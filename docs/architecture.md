# Architecture

The app is split into a small set of focused modules.

## Modules

- `config`
  - env vars, path resolution, workspace defaults
- `loaders`
  - file discovery and document loading
- `chunking`
  - deterministic text chunking
- `embeddings`
  - local embedding model loading and query embedding preparation
- `storage`
  - Chroma access and manifest persistence
- `indexing`
  - incremental ingest, upsert, delete
- `retrieval`
  - top-k retrieval and context construction
- `llm`
  - MiniMax adapter and optional echo provider
- `cli`
  - human commands and JSON automation commands
- `legacy`
  - compatibility wrappers for the old scripts

## Data Flow

```text
source files
-> loaders
-> chunking
-> embeddings
-> chroma upsert
-> retrieval
-> context assembly
-> MiniMax answer generation
-> human output or JSON output
```

## Why This Shape

The project used to be a few scripts with duplicated assumptions. The refactor moves the real logic into shared modules so that:

- interactive terminal usage and agent usage share the same logic
- collection names and models are no longer hardcoded in different places
- repeated ingest is safe
