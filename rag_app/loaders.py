from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .config import AppConfig
from .models import SourceDocument


SUPPORTED_SUFFIXES = {".md", ".txt"}
BUILTIN_EXCLUDED_DIR_NAMES = {"venv", ".venv", "node_modules", "__pycache__", "build", "dist"}


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


def _matches_exclusion(relative_path: Path, excluded_paths: tuple[str, ...]) -> bool:
    relative_posix = relative_path.as_posix()
    return any(relative_posix == excluded or relative_posix.startswith(f"{excluded}/") for excluded in excluded_paths)


def _is_hidden_path(relative_path: Path) -> bool:
    return any(part.startswith(".") for part in relative_path.parts)


def _uses_excluded_dir_name(relative_path: Path) -> bool:
    return any(part in BUILTIN_EXCLUDED_DIR_NAMES for part in relative_path.parts)


def _should_skip_directory(relative_dir: Path, config: AppConfig) -> bool:
    if not relative_dir.parts:
        return False
    if _is_hidden_path(relative_dir):
        return True
    if _uses_excluded_dir_name(relative_dir):
        return True
    if _matches_exclusion(relative_dir, config.effective_source_exclude_paths):
        return True
    return False


def _should_include_file(relative_file: Path, config: AppConfig) -> bool:
    if relative_file.suffix.lower() not in SUPPORTED_SUFFIXES:
        return False
    if _is_hidden_path(relative_file):
        return False
    if _uses_excluded_dir_name(relative_file.parent):
        return False
    if _matches_exclusion(relative_file, config.effective_source_exclude_paths):
        return False
    return True


def discover_source_files(config: AppConfig) -> list[Path]:
    if not config.source_dir.exists():
        return []
    paths: list[Path] = []
    for root, dirs, files in os.walk(config.source_dir, topdown=True):
        root_path = Path(root)
        try:
            relative_root = root_path.relative_to(config.source_dir)
        except ValueError:
            relative_root = Path(".")

        dirs[:] = [
            directory
            for directory in sorted(dirs)
            if not _should_skip_directory(
                Path(directory) if str(relative_root) == "." else relative_root / directory,
                config,
            )
        ]

        for filename in sorted(files):
            relative_file = Path(filename) if str(relative_root) == "." else relative_root / filename
            if _should_include_file(relative_file, config):
                paths.append((config.source_dir / relative_file).resolve())
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
