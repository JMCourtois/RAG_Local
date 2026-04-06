from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .config import AppConfig, ensure_workspace_layout, load_config
from .indexing import ingest_workspace
from .llm import LLMConfigurationError, answer_question
from .models import RetrievedChunk
from .retrieval import EmptyIndexError, retrieve_chunks
from .storage import get_collection, get_document_chunks, load_manifest


console = Console()


def _common_path_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", help="Workspace root. Defaults to the current directory.")
    parser.add_argument("--source-dir", help="Override the workspace knowledge base directory.")
    parser.add_argument("--storage-dir", help="Override the root storage directory.")
    parser.add_argument("--chroma-dir", help="Override the Chroma persistence directory.")
    parser.add_argument("--model-cache-dir", help="Override the embedding model cache directory.")
    parser.add_argument("--state-dir", help="Override the state directory.")
    parser.add_argument("--collection-name", help="Override the Chroma collection name.")
    parser.add_argument("--embed-model", help="Override the local embedding model.")


def _query_tuning_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--top-k", type=int, help="Number of chunks to retrieve.")
    parser.add_argument("--model", dest="llm_model", help="Override the configured LLM model.")
    parser.add_argument("--provider", dest="llm_provider", help="Override the LLM provider.")
    parser.add_argument("--base-url", dest="llm_base_url", help="Override the LLM base URL.")


def _build_overrides(args: argparse.Namespace) -> dict[str, Any]:
    keys = [
        "source_dir",
        "storage_dir",
        "chroma_dir",
        "model_cache_dir",
        "state_dir",
        "collection_name",
        "embed_model",
        "top_k",
        "llm_model",
        "llm_provider",
        "llm_base_url",
    ]
    return {key: getattr(args, key) for key in keys if hasattr(args, key) and getattr(args, key) is not None}


def _render_sources(chunks: list[RetrievedChunk], *, debug: bool = False) -> None:
    if not chunks:
        console.print("[bold red]No source chunks were retrieved.[/bold red]")
        return

    console.print(Rule("[bold]Retrieved Sources[/bold]"))
    for index, chunk in enumerate(chunks, start=1):
        header = Text()
        header.append(f"{index}. ", style="bold white")
        header.append(chunk.title or chunk.path, style="bold magenta")
        header.append(f"  score={chunk.score:.3f}", style="cyan")

        if debug:
            body = json.dumps(chunk.metadata | {"content": chunk.content}, indent=2, ensure_ascii=False)
        else:
            preview = chunk.content.strip()
            if len(preview) > 700:
                preview = preview[:700].rstrip() + "..."
            body = f"Path: {chunk.path}\nChunk ID: {chunk.chunk_id}\n\n{preview}"

        console.print(Panel(body, title=header, expand=False, border_style="dim"))


def _print_query_payload(payload: dict[str, Any]) -> None:
    console.print(Panel(payload["answer"] or "[No answer returned]", title="Assistant", border_style="cyan"))
    if payload.get("sources"):
        chunks = [
            RetrievedChunk(
                doc_id=source["doc_id"],
                path=source["path"],
                title=source["title"],
                score=float(source["score"]),
                chunk_id=source["chunk_id"],
                content=source["content"],
                metadata={},
            )
            for source in payload["sources"]
        ]
        _render_sources(chunks)


def _payload_to_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _query_once(
    config: AppConfig,
    question: str,
    *,
    json_mode: bool,
    show_sources: bool,
    sources_debug: bool,
    history: list[dict[str, str]] | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    chunks = retrieve_chunks(config, question, top_k=config.top_k)
    if stream and not json_mode:
        console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")
        payload = answer_question(
            config,
            question,
            chunks,
            history=history,
            stream=True,
            on_token=lambda token: print(token, end="", flush=True),
        )
        print()
    else:
        payload = answer_question(config, question, chunks, history=history, stream=False)

    payload_dict = payload.to_dict()

    if json_mode:
        _payload_to_json(payload_dict)
    else:
        if not stream:
            console.print(
                Panel(
                    payload.answer or "[No answer returned]",
                    title=f"{payload.model}  ({payload.timing_ms} ms)",
                    border_style="cyan",
                )
            )
        else:
            console.print(f"[dim]{payload.model}  ({payload.timing_ms} ms)[/dim]")
        if show_sources or sources_debug:
            _render_sources(chunks, debug=sources_debug)
    return payload_dict


def cmd_ingest(args: argparse.Namespace) -> int:
    config = load_config(args.workspace, overrides=_build_overrides(args))
    ensure_workspace_layout(config)

    if not args.json:
        console.print(Panel("Workspace RAG Ingestion", border_style="green", expand=False))
        console.print(f"Source directory: [cyan]{config.source_dir}[/cyan]")
        console.print(f"Chroma directory: [cyan]{config.chroma_dir}[/cyan]")
        console.print(f"Collection: [cyan]{config.collection_name}[/cyan]")
        console.print(f"Embedding model: [cyan]{config.embed_model}[/cyan]")

    try:
        summary = ingest_workspace(
            config,
            reset=args.reset,
            console=None if args.json else console,
            show_progress=not args.no_progress and not args.json,
        )
    except Exception as exc:
        if args.json:
            _payload_to_json(
                {
                    "status": "error",
                    "collection": config.collection_name,
                    "source_dir": str(config.source_dir),
                    "error": str(exc),
                }
            )
        else:
            console.print(f"[bold red]{exc}[/bold red]")
        return 1
    if args.json:
        _payload_to_json(
            {
                "status": "ok",
                "collection": config.collection_name,
                "source_dir": str(config.source_dir),
                **summary.to_dict(),
            }
        )
        return 0

    table = Table(title="Ingestion Complete", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")
    for key, value in summary.to_dict().items():
        table.add_row(key.replace("_", " ").title(), str(value))
    console.print(table)
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    config = load_config(args.workspace, overrides=_build_overrides(args))
    interactive = args.interactive or not bool(args.question)
    history: list[dict[str, str]] = []

    if interactive:
        console.print(Panel("Workspace RAG Chat", border_style="cyan", expand=False))
        console.print(f"Collection: [cyan]{config.collection_name}[/cyan]")
        console.print(f"Provider: [cyan]{config.llm_provider}[/cyan]")
        console.print("Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to stop.")
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                return 0
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "bye"}:
                return 0
            try:
                payload = _query_once(
                    config,
                    user_input,
                    json_mode=False,
                    show_sources=args.sources,
                    sources_debug=args.sources_debug,
                    history=history,
                    stream=True,
                )
            except (EmptyIndexError, LLMConfigurationError) as exc:
                console.print(f"[bold red]{exc}[/bold red]")
                continue
            except Exception as exc:
                console.print(f"[bold red]{exc}[/bold red]")
                continue
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": payload["answer"]})
        return 0

    if not args.question:
        raise SystemExit("A question is required unless --interactive is used.")

    try:
        _query_once(
            config,
            args.question,
            json_mode=args.json,
            show_sources=args.sources,
            sources_debug=args.sources_debug,
            stream=False,
        )
    except (EmptyIndexError, LLMConfigurationError) as exc:
        if args.json:
            _payload_to_json(
                {
                    "error": str(exc),
                    "question": args.question,
                    "collection": config.collection_name,
                    "model": config.llm_model,
                }
            )
        else:
            console.print(f"[bold red]{exc}[/bold red]")
        return 1
    except Exception as exc:
        if args.json:
            _payload_to_json(
                {
                    "error": str(exc),
                    "question": args.question,
                    "collection": config.collection_name,
                    "model": config.llm_model,
                }
            )
        else:
            console.print(f"[bold red]{exc}[/bold red]")
        return 1
    return 0


def _select_doc_id(config: AppConfig) -> str | None:
    manifest = load_manifest(config)
    documents = sorted(manifest.get("documents", {}).values(), key=lambda item: item.get("path", ""))
    if not documents:
        return None
    choices = [
        questionary.Choice(
            title=f"{document.get('title', document['path'])} [{document['path']}]",
            value=document["doc_id"],
        )
        for document in documents
    ]
    return questionary.select("Select a document to inspect:", choices=choices).ask()


def _print_inspect_summary(config: AppConfig, *, json_mode: bool) -> int:
    manifest = load_manifest(config)
    documents = sorted(manifest.get("documents", {}).values(), key=lambda item: item.get("path", ""))
    collection = get_collection(config)
    payload = {
        "collection": config.collection_name,
        "collection_count": collection.count(),
        "documents": documents,
    }
    if json_mode:
        _payload_to_json(payload)
        return 0

    table = Table(title=f"Collection Summary: {config.collection_name}", show_header=True, header_style="bold magenta")
    table.add_column("Path", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Chunks", justify="right", style="green")
    table.add_column("Hash", style="yellow")
    for document in documents:
        table.add_row(
            str(document.get("path", "")),
            str(document.get("title", "")),
            str(document.get("chunk_count", 0)),
            str(document.get("file_hash", ""))[:12],
        )
    console.print(table)
    console.print(f"Collection count: [bold]{collection.count()}[/bold]")
    return 0


def _print_document_chunks(config: AppConfig, doc_id: str, *, json_mode: bool) -> int:
    chunks = get_document_chunks(config, doc_id)
    if json_mode:
        _payload_to_json({"doc_id": doc_id, "chunks": chunks})
        return 0
    if not chunks:
        console.print(f"[bold yellow]No chunks found for {doc_id}.[/bold yellow]")
        return 0
    console.print(Rule(f"[bold]Chunks for {doc_id}[/bold]"))
    for index, chunk in enumerate(chunks, start=1):
        preview = chunk["content"]
        console.print(
            Panel(
                preview,
                title=f"{index}. {chunk.get('title', doc_id)}",
                subtitle=f"chunk_index={chunk.get('chunk_index', 0)}",
                border_style="dim",
                expand=False,
            )
        )
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    config = load_config(args.workspace, overrides=_build_overrides(args))
    if args.interactive:
        selected = _select_doc_id(config)
        if not selected:
            console.print("[bold yellow]No document selected.[/bold yellow]")
            return 0
        return _print_document_chunks(config, selected, json_mode=args.json)

    if args.doc_id:
        return _print_document_chunks(config, args.doc_id, json_mode=args.json)

    if args.path:
        manifest = load_manifest(config)
        for document in manifest.get("documents", {}).values():
            if document.get("path") == args.path:
                return _print_document_chunks(config, document["doc_id"], json_mode=args.json)
        if args.json:
            _payload_to_json({"error": f"Path not found in manifest: {args.path}"})
        else:
            console.print(f"[bold red]Path not found in manifest: {args.path}[/bold red]")
        return 1

    return _print_inspect_summary(config, json_mode=args.json)


def cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(args.workspace, overrides=_build_overrides(args))
    ensure_workspace_layout(config)
    manifest = load_manifest(config)
    collection = get_collection(config)
    source_files = sorted(path.as_posix() for path in config.source_dir.rglob("*") if path.is_file())
    payload = {
        "config": config.to_public_dict(),
        "checks": {
            "source_dir_exists": config.source_dir.exists(),
            "storage_dir_exists": config.storage_dir.exists(),
            "chroma_dir_exists": config.chroma_dir.exists(),
            "model_cache_dir_exists": config.model_cache_dir.exists(),
            "state_dir_exists": config.state_dir.exists(),
            "manifest_exists": config.manifest_path.exists(),
            "minimax_api_key_configured": bool(config.minimax_api_key),
            "collection_count": collection.count(),
            "manifest_document_count": len(manifest.get("documents", {})),
            "source_file_count": len(source_files),
        },
    }
    if args.json:
        _payload_to_json(payload)
        return 0

    table = Table(title="Workspace RAG Doctor", show_header=True, header_style="bold magenta")
    table.add_column("Check", style="dim")
    table.add_column("Value", style="bold")
    for key, value in payload["checks"].items():
        table.add_row(key.replace("_", " ").title(), str(value))
    console.print(table)
    console.print(f"Workspace root: [cyan]{config.workspace_root}[/cyan]")
    console.print(f"Collection: [cyan]{config.collection_name}[/cyan]")
    console.print(f"Embedding model: [cyan]{config.embed_model}[/cyan]")
    console.print(f"LLM provider/model: [cyan]{config.llm_provider} / {config.llm_model}[/cyan]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workspace-local RAG for Openclaw and terminal use.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Index or update the workspace knowledge base.")
    _common_path_arguments(ingest_parser)
    ingest_parser.add_argument("--reset", action="store_true", help="Delete the existing collection state first.")
    ingest_parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    ingest_parser.add_argument("--no-progress", action="store_true", help="Disable embedding progress output.")
    ingest_parser.set_defaults(func=cmd_ingest)

    query_parser = subparsers.add_parser("query", help="Ask questions against the indexed workspace.")
    _common_path_arguments(query_parser)
    _query_tuning_arguments(query_parser)
    query_parser.add_argument("--interactive", action="store_true", help="Start an interactive chat session.")
    query_parser.add_argument("--question", help="Run a single query and return immediately.")
    query_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    query_parser.add_argument("--sources", action="store_true", help="Show source chunks after the answer.")
    query_parser.add_argument("--sources-debug", action="store_true", help="Show source metadata in debug form.")
    query_parser.set_defaults(func=cmd_query)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect the current collection and stored chunks.")
    _common_path_arguments(inspect_parser)
    inspect_parser.add_argument("--interactive", action="store_true", help="Pick a document interactively.")
    inspect_parser.add_argument("--doc-id", help="Show chunks for a specific document id.")
    inspect_parser.add_argument("--path", help="Show chunks for a specific workspace-relative path.")
    inspect_parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    inspect_parser.set_defaults(func=cmd_inspect)

    doctor_parser = subparsers.add_parser("doctor", help="Validate configuration and local workspace state.")
    _common_path_arguments(doctor_parser)
    _query_tuning_arguments(doctor_parser)
    doctor_parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    doctor_parser.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
