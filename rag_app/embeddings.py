from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer

from .config import AppConfig


_MODEL_CACHE: dict[tuple[str, str, str | None], SentenceTransformer] = {}
_WARMED_MODELS: set[tuple[str, str, str | None]] = set()

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


@contextlib.contextmanager
def _silence_process_output() -> None:
    try:
        stdout_fd = sys.stdout.fileno()
        stderr_fd = sys.stderr.fileno()
    except (AttributeError, OSError, ValueError):
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                yield
        return

    saved_stdout = os.dup(stdout_fd)
    saved_stderr = os.dup(stderr_fd)
    try:
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(devnull.fileno(), stdout_fd)
            os.dup2(devnull.fileno(), stderr_fd)
            yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_stdout, stdout_fd)
        os.dup2(saved_stderr, stderr_fd)
        os.close(saved_stdout)
        os.close(saved_stderr)


def _default_query_prefix(model_name: str) -> str | None:
    lowered = model_name.lower()
    if "bge" in lowered:
        return "Represent this sentence for searching relevant passages: "
    if "e5" in lowered:
        return "query: "
    return None


def _cached_snapshot_path(model_name: str, cache_dir: Path) -> str | None:
    model_dir = cache_dir / f"models--{model_name.replace('/', '--')}" / "snapshots"
    if not model_dir.exists():
        return None
    snapshots = sorted(path for path in model_dir.iterdir() if path.is_dir())
    if not snapshots:
        return None
    return str(snapshots[-1])


def _warm_embedding_model(cache_key: tuple[str, str, str | None], model: SentenceTransformer) -> None:
    if cache_key in _WARMED_MODELS:
        return
    with _silence_process_output():
        model.encode(
            ["warmup"],
            batch_size=1,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
    _WARMED_MODELS.add(cache_key)


def get_embedding_model(config: AppConfig) -> SentenceTransformer:
    cache_key = (config.embed_model, str(config.model_cache_dir), config.embed_device)
    model = _MODEL_CACHE.get(cache_key)
    if model is None:
        cached_snapshot = _cached_snapshot_path(config.embed_model, config.model_cache_dir)
        model_source = cached_snapshot or config.embed_model
        with _silence_process_output():
            model = SentenceTransformer(
                model_source,
                cache_folder=str(config.model_cache_dir),
                device=config.embed_device,
                local_files_only=bool(cached_snapshot),
            )
        _MODEL_CACHE[cache_key] = model
    _warm_embedding_model(cache_key, model)
    return model


def embed_texts(config: AppConfig, texts: list[str], show_progress: bool = False) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model(config)
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return embeddings.tolist()


def prepare_query_text(config: AppConfig, question: str) -> str:
    prefix = config.embed_query_prefix
    if prefix is None:
        prefix = _default_query_prefix(config.embed_model)
    return f"{prefix}{question}" if prefix else question


def embed_query(config: AppConfig, question: str) -> list[float]:
    prepared = prepare_query_text(config, question)
    return embed_texts(config, [prepared], show_progress=False)[0]
