# Openclaw Workspace RAG

This project is now a workspace-local RAG application designed for two modes at once:

- human use from the terminal
- Openclaw agent use through structured JSON commands

It keeps embeddings and Chroma data local in the workspace, uses MiniMax for generation, and supports incremental indexing for `md` and `txt` documents.

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
```

Put your source documents into `./knowledge_base/`, then run:

```bash
python -m rag_app ingest
python -m rag_app query --interactive
python -m rag_app query --question "What does this workspace contain?" --json
python -m rag_app inspect
python -m rag_app doctor
```

## Reset And Rebuild The Index

Normal ingestion is incremental, so running `python -m rag_app ingest` will only add new files, update changed files, and remove deleted files.

If you want to delete the current Chroma collection state and rebuild everything from scratch, use:

```bash
python -m rag_app ingest --reset
```

If you still use the legacy wrapper, the equivalent command is:

```bash
python scripts/local_to_chroma.py --reset-chroma
```

## Inspect Documents And Chunks

To inspect the indexed documents in the collection, run:

```bash
python -m rag_app inspect
```

To pick a document interactively and print all of its stored chunks, use:

```bash
python -m rag_app inspect --interactive
```

To inspect the chunks for one specific file directly, use its workspace-relative path:

```bash
python -m rag_app inspect --path "knowledge_base/your-file.md"
```

If you prefer the old wrapper, this still works too:

```bash
python scripts/inspect_chunks.py
```

## Legacy Script Wrappers

The old entrypoints still exist as thin wrappers:

```bash
python scripts/local_to_chroma.py
python scripts/query_chroma.py
python scripts/inspect_chroma.py
python scripts/inspect_chunks.py
```

## Documentation

Start here:

- [docs/README.md](docs/README.md)
- [docs/openclone-installation.md](docs/openclone-installation.md)

That guide links the full workspace layout, configuration, ingestion flow, querying behavior, Openclaw integration, storage model, architecture notes, and troubleshooting steps.
