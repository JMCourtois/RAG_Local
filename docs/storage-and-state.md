# Storage And State

The project keeps all runtime data inside the workspace.

## Chroma

Directory:

```text
.rag/chroma/
```

This stores the persistent vector collection.

## Model Cache

Directory:

```text
.rag/cache/
```

This stores local embedding model files.

## Manifest State

Directory:

```text
.rag/state/
```

Each collection gets its own manifest file. The manifest stores:

- `doc_id`
- workspace-relative path
- title
- file hash
- chunk ids
- chunk count
- timestamps

## Safe Reset

To rebuild the collection cleanly:

```bash
python -m rag_app ingest --reset
```

That removes the collection data and manifest state, then rebuilds from the source files.

## Do Not Edit By Hand

Avoid manual edits to:

- `.rag/chroma/`
- `.rag/state/manifest-*.json`

Use the CLI commands instead.
