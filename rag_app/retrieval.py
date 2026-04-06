from __future__ import annotations

from .config import AppConfig
from .embeddings import embed_query
from .models import RetrievedChunk
from .storage import get_collection


class EmptyIndexError(RuntimeError):
    """Raised when a query is attempted against an empty collection."""


def retrieve_chunks(config: AppConfig, question: str, top_k: int | None = None) -> list[RetrievedChunk]:
    collection = get_collection(config)
    if collection.count() == 0:
        raise EmptyIndexError(
            f"Collection '{config.collection_name}' is empty. Run 'python -m rag_app ingest' first."
        )

    query_vector = embed_query(config, question)
    result = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k or config.top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    retrieved: list[RetrievedChunk] = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        metadata = dict(metadata or {})
        score = 1.0 - float(distance) if distance is not None else 0.0
        retrieved.append(
            RetrievedChunk(
                doc_id=str(metadata.get("doc_id", "")),
                path=str(metadata.get("path", "")),
                title=str(metadata.get("title", "")),
                score=score,
                chunk_id=str(metadata.get("chunk_id", "")),
                content=document or "",
                metadata=metadata,
            )
        )
    return retrieved


def build_context(chunks: list[RetrievedChunk], max_chars: int) -> str:
    if not chunks:
        return "No retrieved context."

    blocks: list[str] = []
    current_size = 0
    for index, chunk in enumerate(chunks, start=1):
        block = (
            f"[Source {index}]\n"
            f"Path: {chunk.path}\n"
            f"Title: {chunk.title}\n"
            f"Score: {chunk.score:.4f}\n"
            f"Content:\n{chunk.content.strip()}\n"
        )
        if current_size + len(block) > max_chars and blocks:
            break
        blocks.append(block)
        current_size += len(block)
    return "\n".join(blocks)
