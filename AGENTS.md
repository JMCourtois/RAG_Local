# RAG Local Workspace Guide

This workspace contains a local RAG application for indexing files in `knowledge_base/` and answering questions from the terminal or an OpenClaw-compatible agent workflow.

## Read First

- [docs/openclone-installation.md](docs/openclone-installation.md)
- [docs/overview.md](docs/overview.md)
- [docs/configuration.md](docs/configuration.md)
- [docs/openclaw-integration.md](docs/openclaw-integration.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)

## Important Paths

- `knowledge_base/`
  - source `md` and `txt` files to ingest
- `.rag/chroma/`
  - persistent vector store files
- `.rag/state/`
  - ingestion manifest and state
- `.rag/cache/`
  - local embedding model cache

## Main Commands

```bash
python -m rag_app ingest
python -m rag_app ingest --json
python -m rag_app query --question "What does this workspace contain?" --json
python -m rag_app inspect
python -m rag_app doctor
```

## Agent Rules

- Treat this repository root as the workspace root unless `--workspace` is explicitly provided.
- Use `python -m rag_app query --json` when structured output is needed.
- Use `python -m rag_app ingest --json` for automated refresh workflows.
- Do not edit `.rag/chroma/` directly.
- Do not edit `.rag/state/` directly.
- If `.env` is missing, start from `env.example`.
