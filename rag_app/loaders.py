from __future__ import annotations

import hashlib
from pathlib import Path

from .config import AppConfig
from .models import SourceDocument


SUPPORTED_SUFFIXES = {".md", ".txt"}


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_title(path: Path, text: str) -> str:
    if path.suffix.lower() == ".md":
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or path.stem
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return path.stem


def _workspace_relative_path(config: AppConfig, path: Path) -> Path:
    try:
        return path.resolve().relative_to(config.workspace_root)
    except ValueError:
        return path.resolve().relative_to(config.source_dir)


def discover_source_files(config: AppConfig) -> list[Path]:
    if not config.source_dir.exists():
        return []
    paths: list[Path] = []
    for path in sorted(config.source_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if any(part.startswith(".") for part in path.relative_to(config.source_dir).parts):
            continue
        paths.append(path)
    return paths


def load_document(config: AppConfig, path: Path) -> SourceDocument:
    raw_bytes = path.read_bytes()
    text = raw_bytes.decode("utf-8")
    relative_path = _workspace_relative_path(config, path)
    return SourceDocument(
        doc_id=relative_path.as_posix(),
        relative_path=relative_path,
        absolute_path=path.resolve(),
        title=_extract_title(path, text),
        text=text,
        file_hash=_hash_bytes(raw_bytes),
        modified_at=path.stat().st_mtime,
    )


def load_documents(config: AppConfig) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for path in discover_source_files(config):
        documents.append(load_document(config, path))
    return documents
