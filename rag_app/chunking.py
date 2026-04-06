from __future__ import annotations

from .models import ChunkDraft


def _best_boundary(text: str, start: int, target_end: int, floor: int) -> int:
    segment = text[start:target_end]
    boundaries = ["\n## ", "\n# ", "\n\n", "\n", ". ", " "]
    for boundary in boundaries:
        index = segment.rfind(boundary)
        if index == -1:
            continue
        candidate = start + index + len(boundary.strip())
        if candidate >= floor:
            return candidate
    return target_end


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[ChunkDraft]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    chunks: list[ChunkDraft] = []
    cursor = 0
    text_length = len(normalized)
    minimum_fraction = 0.6

    while cursor < text_length:
        tentative_end = min(text_length, cursor + chunk_size)
        floor = cursor + int(chunk_size * minimum_fraction)
        floor = min(floor, tentative_end)
        end = _best_boundary(normalized, cursor, tentative_end, floor)
        if end <= cursor:
            end = tentative_end

        chunk_text = normalized[cursor:end].strip()
        if chunk_text:
            chunks.append(
                ChunkDraft(
                    index=len(chunks),
                    text=chunk_text,
                    start_char=cursor,
                    end_char=end,
                )
            )

        if end >= text_length:
            break

        cursor = max(end - chunk_overlap, cursor + 1)
        while cursor < text_length and normalized[cursor].isspace():
            cursor += 1

    return chunks
