from __future__ import annotations

import re
import time
from collections.abc import Callable

from openai import OpenAI

from .config import AppConfig
from .models import AnswerPayload, RetrievedChunk
from .retrieval import build_context


class LLMConfigurationError(RuntimeError):
    """Raised when the configured LLM provider cannot run."""


THINK_BLOCK_RE = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


def _build_messages(
    config: AppConfig,
    question: str,
    retrieved_chunks: list[RetrievedChunk],
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    context = build_context(retrieved_chunks, config.context_max_chars)
    system_message = (
        f"{config.system_prompt}\n\n"
        "Retrieved workspace context follows. Use it whenever you make claims about the workspace.\n"
        "If the context is not enough, say so clearly.\n\n"
        f"{context}"
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system_message}]
    history = history or []
    max_messages = max(config.max_history_turns, 0) * 2
    for message in history[-max_messages:]:
        role = message.get("role")
        content = message.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    return messages


def _sanitize_answer(text: str) -> str:
    sanitized = THINK_BLOCK_RE.sub("", text or "")
    return sanitized.strip()


def _echo_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "Echo provider is active. No retrieved chunks were available."
    lines = [
        "Echo provider is active. Retrieved context summary:",
        f"Question: {question}",
    ]
    for index, chunk in enumerate(chunks, start=1):
        preview = " ".join(chunk.content.split())[:220]
        lines.append(f"{index}. {chunk.path} ({chunk.score:.3f}) -> {preview}")
    return "\n".join(lines)


def answer_question(
    config: AppConfig,
    question: str,
    retrieved_chunks: list[RetrievedChunk],
    *,
    history: list[dict[str, str]] | None = None,
    stream: bool = False,
    on_token: Callable[[str], None] | None = None,
) -> AnswerPayload:
    started = time.perf_counter()
    sources = [chunk.to_source_dict() for chunk in retrieved_chunks]
    retrieved_texts = [chunk.content for chunk in retrieved_chunks]

    if config.llm_provider == "echo":
        answer = _echo_answer(question, retrieved_chunks)
        if stream and on_token is not None:
            on_token(answer)
        timing_ms = int((time.perf_counter() - started) * 1000)
        return AnswerPayload(
            question=question,
            answer=answer,
            sources=sources,
            retrieved_chunks=retrieved_texts,
            model="echo",
            collection=config.collection_name,
            timing_ms=timing_ms,
        )

    if config.llm_provider != "minimax":
        raise LLMConfigurationError(
            f"Unsupported provider '{config.llm_provider}'. Use 'minimax' or 'echo'."
        )

    if not config.minimax_api_key:
        raise LLMConfigurationError("MINIMAX_API_KEY is not configured.")

    client = OpenAI(api_key=config.minimax_api_key, base_url=config.llm_base_url)
    messages = _build_messages(config, question, retrieved_chunks, history=history)

    if stream:
        answer_parts: list[str] = []
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=messages,
            temperature=config.temperature,
            stream=True,
            timeout=config.llm_timeout_seconds,
        )
        for event in response:
            choice = event.choices[0] if event.choices else None
            delta = choice.delta.content if choice and choice.delta else None
            if not delta:
                continue
            answer_parts.append(delta)
            if on_token is not None:
                on_token(delta)
        answer = "".join(answer_parts).strip()
    else:
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=messages,
            temperature=config.temperature,
            stream=False,
            timeout=config.llm_timeout_seconds,
        )
        answer = response.choices[0].message.content or ""

    answer = _sanitize_answer(answer)

    timing_ms = int((time.perf_counter() - started) * 1000)
    return AnswerPayload(
        question=question,
        answer=answer.strip(),
        sources=sources,
        retrieved_chunks=retrieved_texts,
        model=config.llm_model,
        collection=config.collection_name,
        timing_ms=timing_ms,
    )
