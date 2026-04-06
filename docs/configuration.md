# Configuration

Copy `env.example` to `.env` and adjust the values you need.

For a full variable-by-variable explanation, see [env-reference.md](env-reference.md).

## Core Environment Variables

```env
RAG_SOURCE_DIR=./knowledge_base
RAG_SOURCE_EXCLUDE_PATHS=
RAG_STORAGE_DIR=./.rag
RAG_CHROMA_DIR=./.rag/chroma
RAG_MODEL_CACHE_DIR=./.rag/cache
RAG_STATE_DIR=./.rag/state
RAG_COLLECTION_NAME=workspace_rag
RAG_EMBED_MODEL=BAAI/bge-base-en-v1.5
RAG_LLM_PROVIDER=minimax
RAG_LLM_BASE_URL=https://api.minimax.io/v1
RAG_LLM_MODEL=MiniMax-M2.7
RAG_LLM_TIMEOUT_SECONDS=60
MINIMAX_API_KEY=your_minimax_api_key_here
SYSTEM_PROMPT="..."
```

## Source Selection Modes

Default mode:

```env
RAG_SOURCE_DIR=./knowledge_base
```

Parent-root mode:

```env
RAG_SOURCE_DIR=..
```

When `RAG_SOURCE_DIR` points above the current RAG workspace, the loader automatically excludes the current RAG project folder from indexing. This lets the project live inside a larger workspace and index sibling folders instead of indexing itself.

Optional extra exclusions:

```env
RAG_SOURCE_EXCLUDE_PATHS=Archive,tmp/generated
```

These paths are relative to `RAG_SOURCE_DIR`.

## MiniMax Setup

Set:

- `MINIMAX_API_KEY`
- `RAG_LLM_PROVIDER=minimax`
- `RAG_LLM_BASE_URL=https://api.minimax.io/v1`
- `RAG_LLM_MODEL=MiniMax-M2.7`
- `RAG_LLM_TIMEOUT_SECONDS=60`

You can switch models without code changes, for example:

```env
RAG_LLM_MODEL=MiniMax-M2.5
```

## Embedding Configuration

Embeddings stay local in v1.

Defaults:

- `RAG_EMBED_MODEL=BAAI/bge-base-en-v1.5`
- `RAG_CHUNK_SIZE=1200`
- `RAG_CHUNK_OVERLAP=200`

Optional:

- `RAG_EMBED_DEVICE` to pin a device
- `RAG_EMBED_QUERY_PREFIX` if you want a custom query prefix

## Local Testing Provider

For local verification without calling MiniMax, you can temporarily use:

```env
RAG_LLM_PROVIDER=echo
```

That mode returns a deterministic answer built from retrieved chunks and is useful for CLI and JSON smoke tests.
