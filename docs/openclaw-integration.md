# Openclaw Integration

This project is designed to be called by Openclaw as a workspace-local command-line tool.

## Recommended Invocation

For agent workflows, use:

```bash
python -m rag_app query --question "..." --json
```

This is a single-call request, not the interactive chat loop.

Use `--interactive` only for humans in the terminal.
Openclaw agents should use `--question` for one-shot calls.

For index refresh, use:

```bash
python -m rag_app ingest --json
```

## JSON Output Contract

`query --json` returns:

```json
{
  "question": "...",
  "answer": "...",
  "sources": [],
  "retrieved_chunks": [],
  "model": "MiniMax-M2.7",
  "collection": "workspace_rag",
  "timing_ms": 1234
}
```

## What The Agent Actually Receives

The current implementation does not return the raw MiniMax SDK response object.

Instead, it returns a normalized JSON payload with:

- `answer`
  - the final answer text
  - sanitized before returning
  - any leading `<think>...</think>` block is removed
- `sources`
  - structured source objects
  - includes metadata plus chunk content
- `retrieved_chunks`
  - the raw retrieved chunk texts as plain strings
- `model`
  - the model name used for generation
- `collection`
  - the Chroma collection used
- `timing_ms`
  - total generation time in milliseconds

This makes the result easier for agents to consume than a raw provider response.

## Output Modes

The project supports two output styles for queries:

- human terminal mode
  - rich panels
  - streaming in interactive chat
- machine mode with `--json`
  - clean JSON to stdout
  - no Rich terminal formatting

The `answer` field is plain text.
If MiniMax returns markdown-style text, it will still just appear as a string inside JSON.

## Source File Formats

The indexed knowledge base currently supports:

- `.md`
- `.txt`

JSON files are not currently part of the document ingestion pipeline.

## Python-Level Building Blocks

The current codebase is mainly designed for command-line invocation by agents.

Internally, the one-shot path is built from:

- retrieval via `retrieve_chunks(...)`
- answer generation via `answer_question(...)`

So yes, the single-call flow exists today.
The main supported public contract for agents is still:

```bash
python -m rag_app query --question "..." --json
```

## Recommended Agent Pattern

One useful Openclaw pattern is:

1. Agent A calls `query --json`
2. Agent A receives:
   - answer
   - retrieved chunks
   - source metadata
3. Agent A passes the answer or raw retrieved chunks into another agent in a larger MiniMax workflow

This keeps retrieval isolated and makes the RAG component reusable across multiple agent workflows.

## Important Rule

When Openclaw needs structured output, it should always use `--json`. Human-friendly terminal mode prints rich formatting that is intentionally not machine-oriented.
