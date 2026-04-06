# OpenClone Workspace Installation

This guide is for the setup where you want this repository to live directly as an OpenClone workspace, or as a dedicated project folder inside your main OpenClone workspace area.

## Recommended Folder Name

Use a simple folder name such as `rag-local`.

That is only a recommendation for readability. The code does not depend on the folder name, so keeping `RAG_Local` also works.

## Recommended Layout

The cleanest setup is to treat this repository root as the workspace root that OpenClone opens.

```text
rag-local/
├── AGENTS.md
├── docs/
├── rag_app/
├── scripts/
├── knowledge_base/
├── .rag/
├── env.example
├── .env
└── requirements.txt
```

If you keep multiple projects under one larger OpenClone directory, place this repo in a folder such as `workspace/rag-local/` and point the agent or terminal commands at that folder.

## Install Steps

1. Put the project in the workspace location you want OpenClone to use.
2. Open a terminal in the project root.
3. Create and activate a virtual environment.
4. Install dependencies.
5. Copy `env.example` to `.env`.
6. Set your `MINIMAX_API_KEY` in `.env`.
7. Add source documents to `knowledge_base/`.
8. Run the first ingestion.

Example:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
mkdir -p knowledge_base
python -m rag_app ingest
```

## First Validation

After ingestion, test the workspace with:

```bash
python -m rag_app query --question "What does this workspace contain?" --json
```

If you want a quick configuration check, run:

```bash
python -m rag_app doctor
```

## OpenClone Workspace Notes

This project is already built to run from the workspace root.

- Documents go in `knowledge_base/`
- Local vector and state data stay in `.rag/`
- The CLI defaults to the current working directory as the workspace root
- If needed, you can still override the workspace with `--workspace`

## File Included For Agent Recognition

The repository now includes a root `AGENTS.md`.

If your OpenClone setup uses the OpenClaw-compatible workspace bootstrap files, that file gives the agent:

- a short description of the project
- direct links to the important docs
- the main commands for ingestion and querying
- guardrails about which directories should not be edited directly

## Suggested Docs To Read Next

- [overview.md](overview.md)
- [configuration.md](configuration.md)
- [querying.md](querying.md)
- [openclaw-integration.md](openclaw-integration.md)
