#!/usr/bin/env python3
"""
scripts/local_to_chroma.py - Ingest local markdown files into ChromaDB for RAG pipelines.
"""
import os
import argparse
import time
import shutil
from dotenv import load_dotenv

# --- LlamaIndex Imports ---
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    Document,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from chromadb import PersistentClient
from chromadb.config import Settings as ChromaSettings

# Rich UI Imports
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table

# --- Configuration ---
load_dotenv()
DEFAULT_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_storage")
DEFAULT_SOURCE_DIR = os.getenv("SOURCE_DIR", "./documents")
# Using a different collection name to avoid conflicts with the Notion one
DEFAULT_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "local_files_collection")

console = Console()

def main():
    start_time = time.monotonic()
    console.print(Panel("[bold green]🚀 Local Files to ChromaDB Indexer 🚀[/bold green]", expand=False))

    parser = argparse.ArgumentParser(description="Ingest local files into ChromaDB.")
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR, help="Source directory with markdown files.")
    parser.add_argument("--persist-dir", default=DEFAULT_PERSIST_DIR, help="ChromaDB persistence directory.")
    parser.add_argument("--collection-name", default=DEFAULT_COLLECTION_NAME, help="ChromaDB collection name.")
    parser.add_argument("--force-reindex", action="store_true", help="Force reindexing all files (not yet implemented).")
    parser.add_argument("--reset-chroma", action="store_true", help="Delete existing ChromaDB database before running.")
    args = parser.parse_args()

    if args.reset_chroma:
        console.print(f"🔥 [bold yellow]--reset-chroma flag detected. Deleting ChromaDB directory: {args.persist_dir}[/bold yellow]")
        if os.path.exists(args.persist_dir):
            try:
                shutil.rmtree(args.persist_dir)
                console.print(f"✅ Deleted ChromaDB directory: {args.persist_dir}")
            except OSError as e:
                console.print(f"❌ Error deleting directory {args.persist_dir}: {e}")
        else:
            console.print(f"🤷 Directory {args.persist_dir} not found, nothing to delete.")
        console.print("✅ Reset complete. Proceeding with fresh indexing...")

    console.print(f"📂 Source directory: {args.source_dir}")
    console.print(f"💾 ChromaDB dir: {args.persist_dir}")
    console.print(f"🏷️  Collection name: {args.collection_name}")

    # --- 1. Load Documents ---
    console.print("\n📖 [bold]Loading documents from source directory...[/bold]")
    
    try:
        files_to_process = []
        console.print("🔍 Discovering markdown files...")
        for root, _, files in os.walk(args.source_dir):
            for file in files:
                if file.endswith(".md"):
                    files_to_process.append(os.path.join(root, file))
        
        console.print(f"✅ Found {len(files_to_process)} markdown files to process.")

        if not files_to_process:
            console.print("[yellow]⚠️ No markdown files found in the source directory. Exiting.[/yellow]")
            return

        docs = []
        with Progress(
            SpinnerColumn(), BarColumn(), "[progress.percentage]{task.percentage:>3.0f}%",
            TextColumn("[cyan]{task.description}[/cyan]"), transient=True
        ) as progress:
            task = progress.add_task("[green]Loading documents...", total=len(files_to_process))
            for file_path in files_to_process:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    
                    doc = Document(text=text, id_=file_path)
                    file_name = os.path.basename(file_path)
                    doc.metadata['file_path'] = file_path
                    doc.metadata['file_name'] = file_name
                    docs.append(doc)
                except Exception as e:
                    console.print(f"⚠️ [yellow]Skipping file {file_path} due to error: {e}[/yellow]")
                progress.update(task, advance=1)

        console.print(f"✅ Loaded {len(docs)} documents:")
        
        # Add metadata and print discovered files for better feedback
        for doc in docs:
            file_path = doc.id_
            file_name = doc.metadata.get('file_name', 'Unknown file')
            
            # Create a title from the filename without the extension
            title = os.path.splitext(file_name)[0]

            # Enhance metadata for the inspector script
            doc.metadata['title'] = title
            doc.metadata['document_id'] = file_path # Use path as a unique ID for grouping

            file_name_display = doc.metadata.get('file_name', 'Unknown file')
            console.print(f"  [dim]-> Discovered file:[/dim] [cyan]{file_name_display}[/cyan]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to load documents: {e}[/red]")
        return

    # --- 2. Configure LlamaIndex Settings ---
    console.print("\n⚙️ [bold]Configuring LlamaIndex Settings...[/bold]")
    
    chunk_size = 1024
    chunk_overlap = 200

    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-large-en")
    Settings.node_parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    console.print(f"  [dim]‣ Chunk Size:[/dim] [cyan]{chunk_size} tokens[/cyan]")
    console.print(f"  [dim]‣ Chunk Overlap:[/dim] [cyan]{chunk_overlap} tokens[/cyan]")
    console.print(f"  [dim]‣ Embedding Model:[/dim] [cyan]BAAI/bge-large-en[/cyan]")

    # --- 3. Setup ChromaDB Vector Store ---
    console.print(f"\n💾 Initializing ChromaDB at {args.persist_dir}...")
    db = PersistentClient(path=args.persist_dir, settings=ChromaSettings())
    chroma_collection = db.get_or_create_collection(args.collection_name)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # --- 4. Create Index and Parse Nodes ---
    console.print("\n📚 Parsing documents into text nodes (chunks)...")
    
    with Progress(
        SpinnerColumn(), BarColumn(), "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("[cyan]{task.description}[/cyan]"), transient=True
    ) as progress:
        task = progress.add_task("[green]Parsing documents...", total=len(docs))
        nodes = []
        for doc in docs:
            nodes.extend(Settings.node_parser.get_nodes_from_documents([doc]))
            progress.update(task, advance=1)
    
    console.print(f"  [dim]‣ Generated {len(nodes)} text nodes.[/dim]")

    # --- 5. Generate Embeddings & Insert into ChromaDB ---
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

    console.print("\n🔬 [bold]Generating embeddings for text nodes...[/bold]")
    console.print("[dim]This may take a while depending on the number of nodes and your hardware.[/dim]")
    embed_model = Settings.embed_model
    node_texts = [node.get_content() for node in nodes]
    
    embeddings = embed_model.get_text_embedding_batch(node_texts, show_progress=True)

    for node, embedding in zip(nodes, embeddings):
        node.embedding = embedding
    
    console.print("✅ Embeddings generated.")
    
    console.print("\n💾 [bold]Inserting nodes into ChromaDB...[/bold]")
    with Progress(
        SpinnerColumn(), BarColumn(), "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("[cyan]{task.description}[/cyan] [bold]({task.completed} of {task.total})[/bold]"),
    ) as progress:
        task = progress.add_task("[green]Indexing nodes...", total=len(nodes))
        batch_size = 128
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            index.insert_nodes(batch)
            progress.update(task, advance=len(batch))
    
    # --- 6. Final Summary ---
    console.print("\n✅ Indexing finished. Re-loading collection to get latest count...")

    # Re-initialize the client to get the latest state after indexing
    final_db = PersistentClient(path=args.persist_dir, settings=ChromaSettings())
    final_collection = final_db.get_or_create_collection(args.collection_name)
    final_count = final_collection.count()

    end_time = time.monotonic()
    total_time = end_time - start_time
    
    summary_table = Table(title="Indexing Complete! 🎉", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="dim", width=25)
    summary_table.add_column("Value", style="bold")
    
    summary_table.add_row("Documents Processed", str(len(docs)))
    summary_table.add_row("Text Nodes Generated", str(len(nodes)))
    summary_table.add_row("Nodes in DB", str(final_count))
    summary_table.add_row("Total Time", f"{total_time:.2f} seconds")
    
    console.print(summary_table)


if __name__ == "__main__":
    main() 