from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from .config import AppConfig, ensure_workspace_layout


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_manifest(config: AppConfig) -> dict[str, Any]:
    return {
        "version": 1,
        "collection_name": config.collection_name,
        "embed_model": config.embed_model,
        "updated_at": _utc_now(),
        "documents": {},
    }


def load_manifest(config: AppConfig) -> dict[str, Any]:
    if not config.manifest_path.exists():
        return default_manifest(config)
    data = json.loads(config.manifest_path.read_text(encoding="utf-8"))
    if "documents" not in data or not isinstance(data["documents"], dict):
        return default_manifest(config)
    return data


def save_manifest(config: AppConfig, manifest: dict[str, Any]) -> None:
    ensure_workspace_layout(config)
    manifest["collection_name"] = config.collection_name
    manifest["embed_model"] = config.embed_model
    manifest["updated_at"] = _utc_now()
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=config.state_dir,
        prefix=f"{config.manifest_path.stem}-",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(json.dumps(manifest, indent=2, ensure_ascii=False))
        temp_path = Path(handle.name)
    temp_path.replace(config.manifest_path)


def get_client(config: AppConfig) -> chromadb.PersistentClient:
    ensure_workspace_layout(config)
    return chromadb.PersistentClient(path=str(config.chroma_dir))


def get_collection(config: AppConfig) -> Collection:
    client = get_client(config)
    return client.get_or_create_collection(
        config.collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def get_document_chunks(config: AppConfig, doc_id: str) -> list[dict[str, Any]]:
    collection = get_collection(config)
    result = collection.get(
        where={"doc_id": doc_id},
        include=["metadatas", "documents"],
    )
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    chunks: list[dict[str, Any]] = []
    for document, metadata in zip(documents, metadatas):
        chunk_meta = dict(metadata or {})
        chunk_meta["content"] = document
        chunks.append(chunk_meta)
    chunks.sort(key=lambda chunk: int(chunk.get("chunk_index", 0)))
    return chunks
