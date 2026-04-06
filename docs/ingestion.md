# Ingestion

The ingestion flow is incremental. It does not blindly append duplicate chunks on every run.

## How It Works

For each file in `knowledge_base/`:

1. compute a stable `doc_id` from the workspace-relative path
2. compute a file hash
3. compare the file hash with the saved manifest
4. skip unchanged files
5. delete old chunks and re-index changed files
6. remove chunks for deleted files

## Supported Sources

- `.md`
- `.txt`

## Commands

Initial or incremental ingest:

```bash
python -m rag_app ingest
```

The standard terminal mode prints a step-by-step Rich UI for:

- source discovery
- incremental change planning
- chunk preparation
- embedding generation
- ChromaDB writes

Reset the collection and re-index from scratch:

```bash
python -m rag_app ingest --reset
```

JSON mode for automation:

```bash
python -m rag_app ingest --json
```

Use `--json` when Openclaw or another automation needs clean machine-readable output without the terminal UI.

## What Gets Written

The ingestion command writes only inside:

- `.rag/chroma/`
- `.rag/cache/`
- `.rag/state/`

## Notes

- If the embedding model is not cached yet, the first ingest may download it.
- If a file becomes empty, it stays in the manifest but contributes zero chunks until content is added again.
