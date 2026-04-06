# Querying

The project supports both interactive human chat and one-shot machine-readable queries.

## Interactive Terminal Mode

```bash
python -m rag_app query --interactive
```

Useful flags:

```bash
python -m rag_app query --interactive --sources
python -m rag_app query --interactive --model MiniMax-M2.5
```

## One-Shot Human Query

```bash
python -m rag_app query --question "What does the workspace say about deployment?"
```

## One-Shot JSON Query

```bash
python -m rag_app query --question "Summarize the deployment notes" --json
```

That mode prints only JSON on stdout, which is the mode Openclaw agents should use.

## Source Display

In human mode, use:

- `--sources` for a readable source view
- `--sources-debug` for metadata-heavy source inspection

## Retrieval Behavior

The query command:

1. embeds the user question locally
2. retrieves top-k chunks from Chroma
3. builds a context block from those chunks
4. sends the context plus question to the configured LLM provider
