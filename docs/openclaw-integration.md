# Openclaw Integration

This project is designed to be called by Openclaw as a workspace-local command-line tool.

## Recommended Invocation

For agent workflows, use:

```bash
python -m rag_app query --question "..." --json
```

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
