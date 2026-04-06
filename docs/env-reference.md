# Env Reference

This document explains the `.env` file used by the workspace-local RAG app.

The app loads `.env` from the project root by default.

## How To Use It

1. Copy `env.example` to `.env`
2. Change only the values you need
3. Run the app from the workspace root

```bash
cp env.example .env
```

## Precedence

Configuration is resolved in this order:

1. CLI flags
2. shell environment variables
3. `.env`
4. built-in defaults

## Recommended Starting Profiles

These are practical starting points for this project.

### Precision Q&A

Use this when you want tighter retrieval and less noise.

```env
RAG_TOP_K=5
RAG_CONTEXT_MAX_CHARS=12000
RAG_CHUNK_SIZE=1200
RAG_CHUNK_OVERLAP=200
```

### Balanced Default

Use this when you want broader retrieval without overloading the prompt.

```env
RAG_TOP_K=8
RAG_CONTEXT_MAX_CHARS=18000
RAG_CHUNK_SIZE=1200
RAG_CHUNK_OVERLAP=200
```

### Broad Summary Mode

Use this when you ask for high-level summaries of long files.

```env
RAG_TOP_K=10
RAG_CONTEXT_MAX_CHARS=24000
RAG_CHUNK_SIZE=1400
RAG_CHUNK_OVERLAP=250
```

## Important Retrieval Note

- `RAG_TOP_K` is how many chunks are retrieved from Chroma
- `RAG_CONTEXT_MAX_CHARS` is the final context cap sent to the LLM
- the app currently limits context by characters, not tokens

That means increasing `RAG_TOP_K` alone does not guarantee that all retrieved chunks will fit into the final prompt.

Practical example:

```env
RAG_TOP_K=20
RAG_CONTEXT_MAX_CHARS=20000
```

What this usually means in practice:

- the retriever will try to fetch up to 20 chunks
- the final prompt will still be trimmed to about 20,000 characters of retrieved context
- not all 20 chunks will necessarily fit into the final LLM context block

Why this matters:

- MiniMax M2.7 has a very large context window, but the app still trims retrieved context before sending it
- pushing `RAG_TOP_K` too high can increase retrieval noise if lower-quality chunks get included

Recommendation:

- use `RAG_TOP_K=8` for a strong default
- use `RAG_TOP_K=10` to `12` for broad summaries
- use `RAG_TOP_K=20` only for experimentation or very broad summary-style questions

## Variable Reference

### Workspace Paths

#### `RAG_SOURCE_DIR`

Default:

```env
RAG_SOURCE_DIR=./knowledge_base
```

What it does:
Directory where source `.md` and `.txt` files are read from.

When to change it:
Change it if your documents live in another folder inside the workspace.

#### `RAG_STORAGE_DIR`

Default:

```env
RAG_STORAGE_DIR=./.rag
```

What it does:
Root folder for workspace-local RAG data.

When to change it:
Usually leave it alone.

#### `RAG_CHROMA_DIR`

Default:

```env
RAG_CHROMA_DIR=./.rag/chroma
```

What it does:
Persistent Chroma vector store directory.

When to change it:
Only if you want Chroma data in another workspace-local folder.

#### `RAG_MODEL_CACHE_DIR`

Default:

```env
RAG_MODEL_CACHE_DIR=./.rag/cache
```

What it does:
Stores downloaded embedding model files.

When to change it:
Change it if you want a different cache location inside the workspace.

#### `RAG_STATE_DIR`

Default:

```env
RAG_STATE_DIR=./.rag/state
```

What it does:
Stores the manifest and ingestion state files.

When to change it:
Usually leave it alone.

### Retrieval And Chunking

#### `RAG_COLLECTION_NAME`

Default:

```env
RAG_COLLECTION_NAME=workspace_rag
```

What it does:
Name of the Chroma collection.

When to change it:
Change it if you want multiple separate indexes in the same workspace.

#### `RAG_EMBED_MODEL`

Default:

```env
RAG_EMBED_MODEL=BAAI/bge-base-en-v1.5
```

What it does:
Local embedding model used for documents and queries.

When to change it:
Change it if you want a different local embedding model.

#### `RAG_TOP_K`

Default:

```env
RAG_TOP_K=5
```

What it does:
Maximum number of chunks retrieved for each question before final context trimming.

When to change it:
- raise it for broad summaries and exploratory questions
- lower it for precise factual questions

Recommended range:
- `5` for precision
- `8` for balanced usage
- `10` for long-document summaries
- `12` only if you also raise the context cap and confirm quality stays good

#### `RAG_CHUNK_SIZE`

Default:

```env
RAG_CHUNK_SIZE=1200
```

What it does:
Target chunk size in characters.

When to change it:
- raise it if your chunks feel too fragmented
- lower it if each chunk covers too many unrelated ideas

Recommended range:
- `1000` to `1600` for this project

#### `RAG_CHUNK_OVERLAP`

Default:

```env
RAG_CHUNK_OVERLAP=200
```

What it does:
Character overlap between consecutive chunks.

When to change it:
- raise it if important transitions are getting split awkwardly
- lower it if you want less redundancy

Recommended range:
- `150` to `300`

#### `RAG_CONTEXT_MAX_CHARS`

Default:

```env
RAG_CONTEXT_MAX_CHARS=12000
```

What it does:
Maximum combined context size passed to the LLM, measured in characters.

When to change it:
- raise it for broad summaries
- keep it lower for fast, focused answers

Recommended range:
- `12000` for precision
- `18000` for balanced usage
- `24000` to `30000` for broad summarization

#### `RAG_MAX_HISTORY_TURNS`

Default:

```env
RAG_MAX_HISTORY_TURNS=6
```

What it does:
Maximum recent chat turns kept in interactive mode.

Important clarification:

- this applies to `python -m rag_app query --interactive`
- one turn means one user message plus one assistant reply
- the code keeps up to `RAG_MAX_HISTORY_TURNS * 2` messages from prior chat history

Example:

```env
RAG_MAX_HISTORY_TURNS=6
```

This means:

- the current question is always included
- up to 6 previous user turns and 6 previous assistant responses are kept
- in total, that is up to 12 prior messages from the conversation history

Special cases:

- `RAG_MAX_HISTORY_TURNS=0` means no prior conversation history is included
- this setting does not matter for one-shot queries where you run a single `--question` command and exit

When to change it:
Lower it if you want shorter interactive context, raise it if you want more chat continuity.

#### `RAG_TEMPERATURE`

Default:

```env
RAG_TEMPERATURE=0.1
```

What it does:
Sampling temperature for the LLM response.

When to change it:
- keep low for grounded RAG answers
- raise slightly for more creative or fluid wording

Recommended range:
- `0.0` to `0.2` for RAG

### Optional Embedding Controls

#### `RAG_EMBED_QUERY_PREFIX`

Default:

Not set explicitly by default.

What it does:
Overrides the automatic query prefix used for some embedding families such as BGE or E5.

When to change it:
Usually do not change it unless you know your embedding model needs a specific query prefix.

#### `RAG_EMBED_DEVICE`

Default:

Not set explicitly by default.

What it does:
Lets you pin the embedding model to a specific device.

Examples:

```env
RAG_EMBED_DEVICE=cpu
```

```env
RAG_EMBED_DEVICE=cuda
```

### LLM Provider Settings

#### `RAG_LLM_PROVIDER`

Default:

```env
RAG_LLM_PROVIDER=minimax
```

What it does:
Selects the answer-generation provider.

Supported values:
- `minimax`
- `echo`

When to change it:
Use `echo` for local smoke tests without calling MiniMax.

#### `RAG_LLM_BASE_URL`

Default:

```env
RAG_LLM_BASE_URL=https://api.minimax.io/v1
```

What it does:
OpenAI-compatible MiniMax API base URL.

When to change it:
Only if MiniMax changes the endpoint or you are routing through a compatible proxy.

#### `RAG_LLM_MODEL`

Default:

```env
RAG_LLM_MODEL=MiniMax-M2.7
```

What it does:
MiniMax model name used for final answer generation.

When to change it:
Change it if you want to switch between `MiniMax-M2.7` and `MiniMax-M2.5`.

#### `RAG_LLM_TIMEOUT_SECONDS`

Default:

```env
RAG_LLM_TIMEOUT_SECONDS=60
```

What it does:
Request timeout for LLM calls.

When to change it:
Raise it if responses are timing out. Lower it if you want failures faster.

#### `MINIMAX_API_KEY`

Default:

```env
MINIMAX_API_KEY=your_minimax_api_key_here
```

What it does:
Authentication key for MiniMax API requests.

When to change it:
Always. This is required for real MiniMax generation.

### System Prompt

#### `SYSTEM_PROMPT`

Default:

```env
SYSTEM_PROMPT="You are a helpful assistant for a workspace-local RAG system. Use the retrieved context whenever possible and say clearly when the context is insufficient."
```

What it does:
System instruction sent to the LLM.

When to change it:
Change it if you want the answer style or constraints to be different.

## Advanced And Compatibility Variables

These are supported by the app but are not part of the main `env.example`.

### `RAG_WORKSPACE_ROOT`

Advanced override for the workspace root.

### Legacy Aliases

These still work for compatibility, but prefer the newer `RAG_*` names:

- `SOURCE_DIR`
- `CHROMA_PERSIST_DIR`
- `CHROMA_COLLECTION_NAME`
- `EMBED_MODEL`

## Recommended First Changes

If you want to tune the project without overcomplicating it, the first variables worth changing are:

1. `MINIMAX_API_KEY`
2. `RAG_TOP_K`
3. `RAG_CONTEXT_MAX_CHARS`
4. `RAG_CHUNK_SIZE`
5. `RAG_CHUNK_OVERLAP`
6. `RAG_LLM_MODEL`

## Practical Recommendation For This Project

Based on the current setup and the large markdown file you tested:

- keep `RAG_CHUNK_SIZE=1200` or raise it slightly to `1400`
- keep `RAG_CHUNK_OVERLAP=200`
- use `RAG_TOP_K=8` as the best default next step
- raise `RAG_CONTEXT_MAX_CHARS=18000` together with it

That is the best next tuning step before trying more aggressive settings.
