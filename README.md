# RAG Local

This project is a local-first implementation for Retrieval-Augmented Generation (RAG) pipelines. 
It allows you to ingest documents from various sources, store them in a local ChromaDB vector database, and query them using language models.

## Features

- **Local-First**: All data (documents, vector database, history) is stored locally. No cloud services required.
- **Multiple Data Sources**:
  - Ingest pages and sub-pages from **Notion**.
  - Ingest local **Markdown files**.
- **Persistent Vector Store**: Uses ChromaDB to store document embeddings locally.
- **Efficient Indexing**: Only re-indexes documents that have changed, saving time and computational resources.
- **Rich CLI**: Interactive command-line interface with progress bars and status updates, powered by `rich`.
- **Configurable**: Easily configure paths, tokens, and other settings via a `.env` file or command-line arguments.

## How It Works

The process is divided into two main stages:

1.  **Ingestion**:
    - **Discovery**: Scripts scan the source (either Notion or a local directory) to find all relevant documents.
    - **Extraction & Enrichment**: The content of each document is extracted. For Notion pages, metadata like title, URL, and last edit time are preserved. For local files, the file path is used as metadata.
    - **Chunking**: Documents are split into smaller text chunks (nodes) to facilitate better embedding and retrieval.
    - **Embedding & Storage**: Each text chunk is converted into a vector embedding using a Hugging Face model (`BAAI/bge-large-en`) and stored in a local ChromaDB collection. An indexing history is maintained to keep track of changes.

2.  **Querying**:
    - The `scripts/query_chroma.py` script loads the existing ChromaDB database and the same embedding model.
    - It takes a user query, embeds it, and performs a similarity search in ChromaDB to find the most relevant text chunks.
    - These chunks are then passed to a language model (via `llama-index`) as context to generate a well-informed answer.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd RAG_Local
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables**:
    - Create a `.env` file by copying the example:
      ```bash
      cp env.example .env
      ```
    - Edit the `.env` file with your configuration:
      - `CHROMA_PERSIST_DIR`: Path to store the ChromaDB database (e.g., `./chroma_storage`).
      - `SOURCE_DIR`: Path to the directory containing your local markdown files (e.g., `./documents`).
      - `CHROMA_HISTORY_PATH`: Path to the JSON file for storing indexing history (e.g., `./data/indexed_files.json`).
      - `NOTION_INTEGRATION_TOKEN` (Optional): Your Notion integration token if you want to use the Notion ingest script.
      - `NOTION_PAGE_ID` (Optional): The root Notion page ID to start indexing from.

## Usage

### Ingesting Local Markdown Files

This is the recommended approach for using local files as your knowledge base.

- **Command**:
  ```bash
  python3 scripts/local_to_chroma.py
  ```

- **Description**:
  This script recursively finds all `.md` files in the `SOURCE_DIR`, checks them against the indexing history, and embeds any new or modified files into ChromaDB.

- **Arguments**:
  - `--source-dir`: The directory to scan for markdown files. Defaults to `./documents`.
  - `--persist-dir`: The directory where ChromaDB is stored. Defaults to `./chroma_storage`.
  - `--history-path`: Path to the indexing history file. Defaults to `./data/indexed_files.json`.
  - `--collection-name`: The name of the ChromaDB collection to use. Defaults to `local_files_collection`.
  - `--force-reindex`: Force the script to re-index all documents, regardless of modification time.
  - `--reset-chroma`: Deletes the existing ChromaDB database and history before running. Useful for starting fresh.

### Ingesting from Notion (Legacy)

- **Command**:
  ```bash
  python3 scripts/notion_to_chroma.py
  ```
- **Arguments**:
  - `--notion-token`: Your Notion integration token.
  - `--notion-page-id`: The root Notion page ID.
  - `--reset-chroma`: Deletes the database and history before running.

### Querying Your Documents

Once your documents are indexed, you can ask questions using the query script.

- **Command**:
  ```bash
  python3 scripts/query_chroma.py "Your question here"
  ```
- **Arguments**:
  - `--collection-name`: Specify the collection you want to query (`local_files_collection` for local files, `notion_collection` for Notion).

This will use the indexed documents as context to answer your question.