# 🚀 Local RAG Project

This project provides a complete, locally-run Retrieval-Augmented Generation (RAG) pipeline. It allows you to ingest local markdown documents, store them in a ChromaDB vector database, and interact with them through a conversational AI powered by the DeepSeek API.

The entire process runs on your machine, ensuring data privacy and full control over your documents.

## ✨ Purpose

The main goal of this project is to offer a powerful RAG solution without relying on external services for data storage or processing. It's designed for developers, researchers, and enthusiasts who want to:

*   **Chat with their documents**: Ask questions about a local knowledge base (e.g., project notes, research papers, personal documents).
*   **Ensure data privacy**: Keep all documents and embeddings stored locally.
*   **Have a flexible foundation**: Easily extend and customize the RAG pipeline for different models or data sources.

## 🌟 Features

*   **📁 Local Document Ingestion**: Recursively finds and processes `.md` files from a specified directory.
*   **🧠 Vector Embeddings**: Uses `BAAI/bge-large-en` to generate high-quality embeddings for your documents.
*   **💾 Persistent Local Storage**: Stores all vector embeddings in a local ChromaDB database.
*   **💬 Interactive Chat**: Provides a command-line interface to chat with your knowledge base, powered by the DeepSeek API.
*   **🔍 Source Verification**: Allows you to see the source documents that the AI used to generate its response.
*   **🛠️ Database Inspection Tools**: Includes scripts to inspect the contents of your ChromaDB, showing which documents are indexed and how many chunks each one has.

## ⚙️ Setup and Installation

Follow these steps to get the project up and running on your local machine.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd RAG_Local
```

### 2. Create and Activate a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

```bash
# Create the virtual environment
python3 -m venv venv

# Activate it (on macOS/Linux)
source venv/bin/activate

# On Windows, use:
# venv\Scripts\activate
```

### 3. Install Dependencies

Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

The project uses an `.env` file to manage API keys and other configuration settings.

First, create a copy of the example file:

```bash
cp env.example .env
```

Next, open the `.env` file and add your **DeepSeek API Key**.

```env
# .env

# --- API Keys ---
# Get your key from: https://platform.deepseek.com/
DEEPSEEK_API_KEY="your_deepseek_api_key_here"

# --- System Configuration ---
# The prompt for the chat model
SYSTEM_PROMPT="You are a helpful AI assistant. Answer the user's questions based on the provided context."

# --- Local Storage Paths ---
# Directory where ChromaDB will store its data
CHROMA_PERSIST_DIR="./chroma_storage"
# Directory where your source markdown files are located
SOURCE_DIR="./documents"

# --- ChromaDB Configuration ---
# Name of the collection within ChromaDB
CHROMA_COLLECTION_NAME="local_files_collection"

# --- Embedding Model ---
# The HuggingFace model used for generating embeddings
EMBED_MODEL="BAAI/bge-large-en"
```

## 🚀 Usage

Using the project involves two main steps: ingesting your documents and then querying them.

### Step 1: Ingest Your Documents

First, place all your markdown (`.md`) files inside the `documents/` directory. The script can handle nested folders.

Once your files are in place, run the ingestion script. This will read your files, split them into chunks, generate embeddings, and store them in your local ChromaDB.

```bash
python scripts/local_to_chroma.py
```

If you ever want to start from scratch, you can use the `--reset-chroma` flag to delete the existing database before indexing.

```bash
python scripts/local_to_chroma.py --reset-chroma
```

### Step 2: Chat with Your Documents

After ingesting your documents, you can start asking questions. Run the query script to start an interactive chat session.

```bash
python scripts/query_chroma.py
```

The script will load the index from ChromaDB and connect to the DeepSeek API. You can then ask questions in the terminal.

To see which parts of your documents the AI is using for its answers, use the `--sources` flag.

```bash
python scripts/query_chroma.py --sources
```

### Utility Scripts

This project includes helpful scripts for inspecting your database.

#### Inspect ChromaDB Summary

To get a high-level summary of what's in your database (which documents are indexed and how many chunks they have), run:

```bash
python scripts/inspect_chroma.py
```

#### Inspect Document Chunks

To see the actual text content of the chunks for a specific document, use this interactive script:

```bash
python scripts/inspect_chunks.py
```

It will present you with a list of indexed documents, and you can select one to see its chunks in detail.