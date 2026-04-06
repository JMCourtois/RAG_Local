# Troubleshooting

## The index is empty

Run:

```bash
python -m rag_app ingest
```

Then verify with:

```bash
python -m rag_app inspect
```

## Repeated ingest used to create duplicates

The new ingestion flow uses file hashes and chunk deletion before upsert. If you still suspect bad state, run:

```bash
python -m rag_app ingest --reset
```

## MiniMax key is missing

Set:

```env
MINIMAX_API_KEY=...
```

Then check:

```bash
python -m rag_app doctor
```

## MiniMax requests feel stuck

The app now uses a configurable provider timeout:

```env
RAG_LLM_TIMEOUT_SECONDS=60
```

If a provider call is too slow in your environment, lower or raise that value and retry.

## Embedding model download problems

The first run may need to download the embedding model. If the environment has restricted network access, pre-cache the model or run the first ingest in an environment with access.

## Wrong paths inside the workspace

Run:

```bash
python -m rag_app doctor
```

That command prints the resolved workspace, source, storage, cache, and state paths.

## Openclaw got decorated terminal output instead of JSON

Use:

```bash
python -m rag_app query --question "..." --json
```

Do not use interactive mode or rich output mode when an agent expects structured stdout.
