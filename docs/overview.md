# Overview

This project is a workspace-local Retrieval-Augmented Generation system for two audiences:

- you in the terminal
- Openclaw agents running commands inside the same workspace

The project indexes `md` and `txt` files from `./knowledge_base/`, stores vectors in a local Chroma collection under `./.rag/`, and uses MiniMax for answer generation.

## Human Mode

Use the human mode when you want to:

- ingest or refresh the knowledge base
- chat interactively from the terminal
- inspect indexed documents and chunks
- run diagnostics

Main commands:

```bash
python -m rag_app ingest
python -m rag_app query --interactive
python -m rag_app inspect
python -m rag_app doctor
```

## Openclaw Mode

Use the agent mode when an Openclaw agent needs:

- a one-shot RAG answer
- retrieved context to hand off to another agent
- a structured JSON payload without terminal formatting

Example:

```bash
python -m rag_app query --question "Summarize the auth flow" --json
```

That command returns JSON with:

- `question`
- `answer`
- `sources`
- `retrieved_chunks`
- `model`
- `collection`
- `timing_ms`
