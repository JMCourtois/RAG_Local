from __future__ import annotations

import hashlib
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .chunking import split_text
from .config import AppConfig, ensure_workspace_layout
from .embeddings import embed_texts
from .loaders import discover_source_files, load_document, load_documents
from .models import IngestSummary, SourceDocument
from .storage import default_manifest, get_collection, load_manifest, save_manifest


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class PendingDocument:
    document: SourceDocument
    existing_entry: dict[str, Any] | None
    chunk_texts: list[str]
    chunk_ids: list[str]
    metadatas: list[dict[str, Any]]


def reset_workspace_index(config: AppConfig) -> None:
    if config.chroma_dir.exists():
        shutil.rmtree(config.chroma_dir)
    if config.manifest_path.exists():
        config.manifest_path.unlink()
    ensure_workspace_layout(config)


def _manifest_entry(document: SourceDocument, chunk_ids: list[str]) -> dict[str, Any]:
    return {
        "doc_id": document.doc_id,
        "path": document.relative_path.as_posix(),
        "title": document.title,
        "file_hash": document.file_hash,
        "modified_at": document.modified_at,
        "indexed_at": _utc_now(),
        "chunk_ids": chunk_ids,
        "chunk_count": len(chunk_ids),
    }


def _doc_storage_prefix(doc_id: str) -> str:
    return hashlib.sha1(doc_id.encode("utf-8")).hexdigest()[:12]


def _chunk_storage_id(doc_id: str, file_hash: str, chunk_index: int) -> str:
    return f"chunk-{_doc_storage_prefix(doc_id)}-{file_hash[:12]}-{chunk_index:04d}"


def _print_step(console: Console | None, title: str) -> None:
    if console is None:
        return
    console.print(f"\n[bold]{title}[/bold]")


def _action_label(existing_entry: dict[str, Any] | None) -> tuple[str, str]:
    if existing_entry is None:
        return ("NEW", "green")
    return ("UPDATE", "yellow")


def ingest_workspace(
    config: AppConfig,
    *,
    reset: bool = False,
    console: Console | None = None,
    show_progress: bool = True,
) -> IngestSummary:
    started = time.perf_counter()
    if reset:
        if console is not None:
            console.print(
                f"[bold yellow]Reset requested.[/bold yellow] Removing collection data from "
                f"[cyan]{config.chroma_dir}[/cyan]."
            )
        reset_workspace_index(config)
        if console is not None:
            console.print("[green]Reset complete.[/green] Starting a fresh ingest.")
    ensure_workspace_layout(config)

    manifest = default_manifest(config) if reset else load_manifest(config)
    collection = get_collection(config)
    if console is None:
        documents = load_documents(config)
    else:
        _print_step(console, "1. Loading source documents")
        source_paths = discover_source_files(config)
        console.print(f"Scanning [cyan]{config.source_dir}[/cyan] for supported files...")
        console.print(f"Found [bold]{len(source_paths)}[/bold] candidate documents.")
        documents = []
        if source_paths:
            with Progress(
                SpinnerColumn(),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("[cyan]{task.description}[/cyan]"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("[green]Loading documents...", total=len(source_paths))
                for path in source_paths:
                    documents.append(load_document(config, path))
                    progress.update(task, advance=1)
            console.print(f"Loaded [bold]{len(documents)}[/bold] documents:")
            for document in documents:
                console.print(
                    "  [dim]->[/dim] "
                    f"[cyan]{document.relative_path.as_posix()}[/cyan] "
                    f"[dim]({len(document.text):,} chars)[/dim]"
                )
        else:
            console.print("[yellow]No .md or .txt files were found.[/yellow]")

    summary = IngestSummary(discovered_documents=len(documents))
    current_doc_ids = {document.doc_id for document in documents}
    indexed_entries: dict[str, Any] = manifest.get("documents", {})

    deleted_doc_ids = sorted(set(indexed_entries) - current_doc_ids)
    if console is not None:
        _print_step(console, "2. Planning incremental changes")
    for doc_id in deleted_doc_ids:
        entry = indexed_entries.pop(doc_id, {})
        chunk_ids = list(entry.get("chunk_ids", []))
        if chunk_ids:
            collection.delete(ids=chunk_ids)
            summary.deleted_chunks += len(chunk_ids)
        summary.deleted_documents += 1
        if console is not None:
            console.print(f"  [red]DELETE[/red] [cyan]{doc_id}[/cyan] [dim]({len(chunk_ids)} old chunks removed)[/dim]")

    pending_documents: list[PendingDocument] = []

    for document in documents:
        existing = indexed_entries.get(document.doc_id)
        if existing and existing.get("file_hash") == document.file_hash:
            summary.skipped_documents += 1
            if console is not None:
                console.print(f"  [blue]SKIP[/blue]   [cyan]{document.relative_path.as_posix()}[/cyan] [dim](unchanged)[/dim]")
            continue

        drafts = split_text(document.text, config.chunk_size, config.chunk_overlap)
        chunk_ids = [_chunk_storage_id(document.doc_id, document.file_hash, draft.index) for draft in drafts]
        chunk_texts = [draft.text for draft in drafts]
        metadatas = [
            {
                "doc_id": document.doc_id,
                "path": document.relative_path.as_posix(),
                "title": document.title,
                "chunk_id": chunk_id,
                "chunk_index": draft.index,
                "file_hash": document.file_hash,
                "start_char": draft.start_char,
                "end_char": draft.end_char,
                "source_ext": document.absolute_path.suffix.lower(),
                "indexed_at": _utc_now(),
            }
            for draft, chunk_id in zip(drafts, chunk_ids)
        ]
        pending_documents.append(
            PendingDocument(
                document=document,
                existing_entry=existing,
                chunk_texts=chunk_texts,
                chunk_ids=chunk_ids,
                metadatas=metadatas,
            )
        )
        action, color = _action_label(existing)
        if console is not None:
            console.print(
                f"  [{color}]{action}[/{color}] "
                f"[cyan]{document.relative_path.as_posix()}[/cyan] "
                f"[dim]({len(chunk_ids)} chunks)[/dim]"
            )
        if existing:
            summary.updated_documents += 1
        else:
            summary.new_documents += 1
        if not chunk_texts:
            summary.empty_documents += 1

    if console is not None:
        plan_table = Table(show_header=True, header_style="bold magenta")
        plan_table.add_column("Metric", style="dim")
        plan_table.add_column("Value", style="bold")
        plan_table.add_row("New documents", str(summary.new_documents))
        plan_table.add_row("Updated documents", str(summary.updated_documents))
        plan_table.add_row("Skipped documents", str(summary.skipped_documents))
        plan_table.add_row("Deleted documents", str(summary.deleted_documents))
        plan_table.add_row(
            "Chunks to generate",
            str(sum(len(pending.chunk_ids) for pending in pending_documents)),
        )
        console.print(plan_table)

    if pending_documents and console is not None:
        _print_step(console, "3. Preparing text chunks")
        with Progress(
            SpinnerColumn(),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("[cyan]{task.description}[/cyan]"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[green]Reviewing chunk plans...", total=len(pending_documents))
            for _pending in pending_documents:
                progress.update(task, advance=1)
        total_chunks = sum(len(pending.chunk_ids) for pending in pending_documents)
        console.print(
            f"Chunk size: [cyan]{config.chunk_size}[/cyan] chars | "
            f"Chunk overlap: [cyan]{config.chunk_overlap}[/cyan] chars"
        )
        console.print(f"Generated [bold]{total_chunks}[/bold] chunks for embedding.")

    for pending in pending_documents:
        old_chunk_ids = list(pending.existing_entry.get("chunk_ids", [])) if pending.existing_entry else []
        if old_chunk_ids:
            collection.delete(ids=old_chunk_ids)
            summary.deleted_chunks += len(old_chunk_ids)

    all_chunk_ids: list[str] = []
    all_chunk_texts: list[str] = []
    all_metadatas: list[dict[str, Any]] = []
    for pending in pending_documents:
        if pending.chunk_texts:
            all_chunk_ids.extend(pending.chunk_ids)
            all_chunk_texts.extend(pending.chunk_texts)
            all_metadatas.extend(pending.metadatas)

    if all_chunk_texts and console is not None:
        _print_step(console, "4. Generating embeddings")
        console.print(
            f"Embedding model: [cyan]{config.embed_model}[/cyan]\n"
            "[dim]This may take a while depending on corpus size and hardware.[/dim]"
        )

    if all_chunk_texts:
        embeddings = embed_texts(config, all_chunk_texts, show_progress=show_progress and console is not None)
        if console is not None:
            console.print("[green]Embeddings generated.[/green]")
            _print_step(console, "5. Writing chunks to ChromaDB")
        batch_size = 128
        if console is not None:
            with Progress(
                SpinnerColumn(),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("[cyan]{task.description}[/cyan] [bold]({task.completed} of {task.total})[/bold]"),
                console=console,
            ) as progress:
                task = progress.add_task("[green]Indexing chunks...", total=len(all_chunk_ids))
                for index in range(0, len(all_chunk_ids), batch_size):
                    batch_slice = slice(index, index + batch_size)
                    collection.upsert(
                        ids=all_chunk_ids[batch_slice],
                        embeddings=embeddings[batch_slice],
                        documents=all_chunk_texts[batch_slice],
                        metadatas=all_metadatas[batch_slice],
                    )
                    progress.update(task, advance=len(all_chunk_ids[batch_slice]))
        else:
            for index in range(0, len(all_chunk_ids), batch_size):
                batch_slice = slice(index, index + batch_size)
                collection.upsert(
                    ids=all_chunk_ids[batch_slice],
                    embeddings=embeddings[batch_slice],
                    documents=all_chunk_texts[batch_slice],
                    metadatas=all_metadatas[batch_slice],
                )
        summary.indexed_chunks = len(all_chunk_ids)

    for pending in pending_documents:
        indexed_entries[pending.document.doc_id] = _manifest_entry(pending.document, pending.chunk_ids)

    manifest["documents"] = indexed_entries
    save_manifest(config, manifest)
    summary.collection_count = get_collection(config).count()
    summary.duration_seconds = time.perf_counter() - started
    return summary
