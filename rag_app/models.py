from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SourceDocument:
    doc_id: str
    relative_path: Path
    absolute_path: Path
    title: str
    text: str
    file_hash: str
    modified_at: float


@dataclass(slots=True)
class ChunkDraft:
    index: int
    text: str
    start_char: int
    end_char: int


@dataclass(slots=True)
class RetrievedChunk:
    doc_id: str
    path: str
    title: str
    score: float
    chunk_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_source_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "path": self.path,
            "title": self.title,
            "score": self.score,
            "chunk_id": self.chunk_id,
            "content": self.content,
        }


@dataclass(slots=True)
class IngestSummary:
    discovered_documents: int = 0
    new_documents: int = 0
    updated_documents: int = 0
    skipped_documents: int = 0
    deleted_documents: int = 0
    empty_documents: int = 0
    indexed_chunks: int = 0
    deleted_chunks: int = 0
    collection_count: int = 0
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovered_documents": self.discovered_documents,
            "new_documents": self.new_documents,
            "updated_documents": self.updated_documents,
            "skipped_documents": self.skipped_documents,
            "deleted_documents": self.deleted_documents,
            "empty_documents": self.empty_documents,
            "indexed_chunks": self.indexed_chunks,
            "deleted_chunks": self.deleted_chunks,
            "collection_count": self.collection_count,
            "duration_seconds": round(self.duration_seconds, 3),
        }


@dataclass(slots=True)
class AnswerPayload:
    question: str
    answer: str
    sources: list[dict[str, Any]]
    retrieved_chunks: list[str]
    model: str
    collection: str
    timing_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "sources": self.sources,
            "retrieved_chunks": self.retrieved_chunks,
            "model": self.model,
            "collection": self.collection,
            "timing_ms": self.timing_ms,
        }
