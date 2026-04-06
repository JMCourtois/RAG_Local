# Workspace Layout

The project is designed to live inside the same workspace that Openclaw can access.

## Expected Layout

```text
workspace-root/
├── AGENTS.md
├── rag_app/
├── scripts/
├── docs/
├── knowledge_base/
└── .rag/
    ├── chroma/
    ├── cache/
    └── state/
```

## What Each Directory Does

- `knowledge_base/`
  - your source documents
  - supported now: `md`, `txt`
- `.rag/chroma/`
  - persistent Chroma collection files
- `.rag/cache/`
  - embedding model cache
- `.rag/state/`
  - manifest and ingestion state
- `docs/`
  - project usage and maintenance documentation
- `AGENTS.md`
  - workspace bootstrap guide for OpenClaw-compatible agents

## What Openclaw Should Touch

Openclaw should:

- run `python -m rag_app ingest`
- run `python -m rag_app query --question ... --json`
- read stdout JSON from query mode

Openclaw should not:

- edit `.rag/chroma/` directly
- edit `.rag/state/` directly
- write custom files into the model cache directory

## Moving The Project

The project is workspace-relative by default. If you copy the whole project into another workspace, it should keep working as long as:

- dependencies are installed
- `.env` is configured
- source files exist under `knowledge_base/`
