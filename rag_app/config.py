from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant for a workspace-local RAG system. "
    "Answer the user's question using the retrieved context whenever possible. "
    "If the retrieved context is insufficient, say that clearly instead of inventing facts."
)


def _coalesce(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return default


def _resolve_path(value: str | Path, workspace_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (workspace_root / path).resolve()


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)


def _normalize_relative_source_path(value: str) -> str:
    normalized = Path(value.strip())
    if not str(normalized) or str(normalized) == ".":
        raise ValueError("Source exclude paths must not be empty.")
    if normalized.is_absolute():
        raise ValueError("RAG_SOURCE_EXCLUDE_PATHS entries must be relative to RAG_SOURCE_DIR.")
    if ".." in normalized.parts:
        raise ValueError("RAG_SOURCE_EXCLUDE_PATHS entries must not contain '..'.")
    return normalized.as_posix()


def _parse_relative_source_paths(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    paths: list[str] = []
    seen: set[str] = set()
    for raw_item in value.split(","):
        raw_item = raw_item.strip()
        if not raw_item:
            continue
        normalized = _normalize_relative_source_path(raw_item)
        if normalized in seen:
            continue
        seen.add(normalized)
        paths.append(normalized)
    return tuple(paths)


def _is_ancestor_path(ancestor: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(ancestor)
        return True
    except ValueError:
        return False


def _combine_exclusion_paths(*groups: tuple[str, ...]) -> tuple[str, ...]:
    combined: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item in seen:
                continue
            seen.add(item)
            combined.append(item)
    return tuple(combined)


@dataclass(frozen=True, slots=True)
class AppConfig:
    workspace_root: Path
    source_dir: Path
    source_exclude_paths: tuple[str, ...]
    effective_source_exclude_paths: tuple[str, ...]
    workspace_root_auto_excluded: bool
    storage_dir: Path
    chroma_dir: Path
    model_cache_dir: Path
    state_dir: Path
    manifest_path: Path
    collection_name: str
    embed_model: str
    embed_device: str | None
    embed_query_prefix: str | None
    llm_provider: str
    llm_base_url: str
    llm_model: str
    minimax_api_key: str | None
    system_prompt: str
    top_k: int
    chunk_size: int
    chunk_overlap: int
    context_max_chars: int
    max_history_turns: int
    temperature: float
    llm_timeout_seconds: float

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "workspace_root": str(self.workspace_root),
            "source_dir": str(self.source_dir),
            "source_exclude_paths": list(self.source_exclude_paths),
            "effective_source_exclude_paths": list(self.effective_source_exclude_paths),
            "workspace_root_auto_excluded": self.workspace_root_auto_excluded,
            "storage_dir": str(self.storage_dir),
            "chroma_dir": str(self.chroma_dir),
            "model_cache_dir": str(self.model_cache_dir),
            "state_dir": str(self.state_dir),
            "manifest_path": str(self.manifest_path),
            "collection_name": self.collection_name,
            "embed_model": self.embed_model,
            "embed_device": self.embed_device,
            "embed_query_prefix": self.embed_query_prefix,
            "llm_provider": self.llm_provider,
            "llm_base_url": self.llm_base_url,
            "llm_model": self.llm_model,
            "minimax_api_key_configured": bool(self.minimax_api_key),
            "system_prompt": self.system_prompt,
            "top_k": self.top_k,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "context_max_chars": self.context_max_chars,
            "max_history_turns": self.max_history_turns,
            "temperature": self.temperature,
            "llm_timeout_seconds": self.llm_timeout_seconds,
        }


def load_config(workspace: str | None = None, overrides: dict[str, Any] | None = None) -> AppConfig:
    load_dotenv()
    overrides = overrides or {}

    workspace_root_value = _coalesce(
        workspace,
        overrides.get("workspace_root"),
        os.getenv("RAG_WORKSPACE_ROOT"),
        os.getcwd(),
    )
    workspace_root = Path(workspace_root_value).resolve()

    storage_dir_value = _coalesce(
        overrides.get("storage_dir"),
        os.getenv("RAG_STORAGE_DIR"),
        ".rag",
    )
    storage_dir = _resolve_path(storage_dir_value, workspace_root)

    source_dir_value = _coalesce(
        overrides.get("source_dir"),
        os.getenv("RAG_SOURCE_DIR"),
        os.getenv("SOURCE_DIR"),
        "./knowledge_base",
    )
    chroma_dir_value = _coalesce(
        overrides.get("chroma_dir"),
        os.getenv("RAG_CHROMA_DIR"),
        os.getenv("CHROMA_PERSIST_DIR"),
        str(storage_dir / "chroma"),
    )
    model_cache_dir_value = _coalesce(
        overrides.get("model_cache_dir"),
        os.getenv("RAG_MODEL_CACHE_DIR"),
        str(storage_dir / "cache"),
    )
    state_dir_value = _coalesce(
        overrides.get("state_dir"),
        os.getenv("RAG_STATE_DIR"),
        str(storage_dir / "state"),
    )

    collection_name = str(
        _coalesce(
            overrides.get("collection_name"),
            os.getenv("RAG_COLLECTION_NAME"),
            os.getenv("CHROMA_COLLECTION_NAME"),
            "workspace_rag",
        )
    )
    source_dir = _resolve_path(source_dir_value, workspace_root)
    source_exclude_paths = _parse_relative_source_paths(
        _coalesce(overrides.get("source_exclude_paths"), os.getenv("RAG_SOURCE_EXCLUDE_PATHS"))
    )
    workspace_root_auto_excluded = source_dir != workspace_root and _is_ancestor_path(source_dir, workspace_root)
    auto_exclude_paths = (
        (workspace_root.relative_to(source_dir).as_posix(),) if workspace_root_auto_excluded else ()
    )
    effective_source_exclude_paths = _combine_exclusion_paths(source_exclude_paths, auto_exclude_paths)
    state_dir = _resolve_path(state_dir_value, workspace_root)
    manifest_path = state_dir / f"manifest-{_safe_filename(collection_name)}.json"

    return AppConfig(
        workspace_root=workspace_root,
        source_dir=source_dir,
        source_exclude_paths=source_exclude_paths,
        effective_source_exclude_paths=effective_source_exclude_paths,
        workspace_root_auto_excluded=workspace_root_auto_excluded,
        storage_dir=storage_dir,
        chroma_dir=_resolve_path(chroma_dir_value, workspace_root),
        model_cache_dir=_resolve_path(model_cache_dir_value, workspace_root),
        state_dir=state_dir,
        manifest_path=manifest_path,
        collection_name=collection_name,
        embed_model=str(
            _coalesce(
                overrides.get("embed_model"),
                os.getenv("RAG_EMBED_MODEL"),
                os.getenv("EMBED_MODEL"),
                "BAAI/bge-base-en-v1.5",
            )
        ),
        embed_device=_coalesce(overrides.get("embed_device"), os.getenv("RAG_EMBED_DEVICE")),
        embed_query_prefix=_coalesce(
            overrides.get("embed_query_prefix"),
            os.getenv("RAG_EMBED_QUERY_PREFIX"),
        ),
        llm_provider=str(
            _coalesce(overrides.get("llm_provider"), os.getenv("RAG_LLM_PROVIDER"), "minimax")
        ).lower(),
        llm_base_url=str(
            _coalesce(
                overrides.get("llm_base_url"),
                os.getenv("RAG_LLM_BASE_URL"),
                "https://api.minimax.io/v1",
            )
        ),
        llm_model=str(
            _coalesce(overrides.get("llm_model"), os.getenv("RAG_LLM_MODEL"), "MiniMax-M2.7")
        ),
        minimax_api_key=_coalesce(overrides.get("minimax_api_key"), os.getenv("MINIMAX_API_KEY")),
        system_prompt=str(
            _coalesce(overrides.get("system_prompt"), os.getenv("SYSTEM_PROMPT"), DEFAULT_SYSTEM_PROMPT)
        ),
        top_k=int(_coalesce(overrides.get("top_k"), os.getenv("RAG_TOP_K"), 5)),
        chunk_size=int(_coalesce(overrides.get("chunk_size"), os.getenv("RAG_CHUNK_SIZE"), 1200)),
        chunk_overlap=int(
            _coalesce(overrides.get("chunk_overlap"), os.getenv("RAG_CHUNK_OVERLAP"), 200)
        ),
        context_max_chars=int(
            _coalesce(
                overrides.get("context_max_chars"),
                os.getenv("RAG_CONTEXT_MAX_CHARS"),
                12000,
            )
        ),
        max_history_turns=int(
            _coalesce(overrides.get("max_history_turns"), os.getenv("RAG_MAX_HISTORY_TURNS"), 6)
        ),
        temperature=float(_coalesce(overrides.get("temperature"), os.getenv("RAG_TEMPERATURE"), 0.1)),
        llm_timeout_seconds=float(
            _coalesce(overrides.get("llm_timeout_seconds"), os.getenv("RAG_LLM_TIMEOUT_SECONDS"), 60)
        ),
    )


def ensure_workspace_layout(config: AppConfig, create_source_dir: bool = True) -> None:
    if create_source_dir:
        config.source_dir.mkdir(parents=True, exist_ok=True)
    config.storage_dir.mkdir(parents=True, exist_ok=True)
    config.chroma_dir.mkdir(parents=True, exist_ok=True)
    config.model_cache_dir.mkdir(parents=True, exist_ok=True)
    config.state_dir.mkdir(parents=True, exist_ok=True)
