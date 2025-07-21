#!/usr/bin/env python3
"""
scripts/notion_to_chroma.py - Ingest Notion pages (and sub-pages) into ChromaDB for RAG pipelines.
Configurable via .env variables and/or command-line arguments.
"""
import os
import json
import argparse
import shutil
import time

from dotenv import load_dotenv
from notion_client import Client as NotionClient
import chromadb

# --- Rich UI Imports ---
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table

# --- LlamaIndex Imports ---
from llama_index.core import VectorStoreIndex, Settings, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from chromadb import PersistentClient
from chromadb.config import Settings as ChromaSettings, DEFAULT_TENANT, DEFAULT_DATABASE

# Load environment variables
load_dotenv()
DEFAULT_NOTION_TOKEN = os.getenv("NOTION_INTEGRATION_TOKEN")
DEFAULT_NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
DEFAULT_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
DEFAULT_HISTORY_PATH = os.getenv("CHROMA_HISTORY_PATH", "./data/indexed_pages.json")

# Command-line arguments
parser = argparse.ArgumentParser(description="Ingest Notion into ChromaDB for RAG.")
parser.add_argument("--notion-token", default=DEFAULT_NOTION_TOKEN, help="Notion integration token.")
parser.add_argument("--notion-page-id", default=DEFAULT_NOTION_PAGE_ID, help="Root Notion page ID.")
parser.add_argument("--persist-dir", default=DEFAULT_PERSIST_DIR, help="ChromaDB persistence directory.")
parser.add_argument("--history-path", default=DEFAULT_HISTORY_PATH, help="Indexing history JSON path.")
parser.add_argument("--force-reindex", action="store_true", help="Force reindexing even if no changes detected.")
parser.add_argument("--reset-chroma", action="store_true", help="Delete existing ChromaDB database and history before running.")
parser.add_argument("--sync", action="store_true", help="Force a sync and print debug info about deleted pages.")
args = parser.parse_args()

NOTION_TOKEN = args.notion_token
NOTION_PAGE_ID = args.notion_page_id
PERSIST_DIR = args.persist_dir
HISTORY_PATH = args.history_path
FORCE_REINDEX = args.force_reindex

if NOTION_TOKEN is None:
    raise ValueError("❌ Missing NOTION_INTEGRATION_TOKEN in .env or --notion-token argument")
if NOTION_PAGE_ID is None:
    raise ValueError("❌ Missing NOTION_PAGE_ID in .env or --notion-page-id argument")

notion = NotionClient(auth=NOTION_TOKEN)
console = Console() # Rich console for better UI

def load_history(history_path):
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_history(history, history_path):
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def should_reindex(doc, history):
    page_id = doc.metadata.get("page_id")
    last_edit = doc.metadata.get("last_edited_time")
    if page_id is None or last_edit is None:
        return True
    return (page_id not in history) or (history[page_id] != last_edit)

def _get_text_from_rich_text_array(rich_text: list) -> str:
    """Helper to extract and join plain text from a rich_text array."""
    return "".join(text.get("plain_text", "") for text in rich_text)

def _get_block_text(block) -> str:
    """
    Extracts and formats plain text from a Notion block based on its type,
    adding markdown-like formatting for structure.
    """
    block_type = block.get("type")
    if not block_type:
        return ""
    
    content = block.get(block_type, {})
    text_content = ""

    # Generic text extraction for common block types
    if "rich_text" in content:
        text_content = _get_text_from_rich_text_array(content["rich_text"])

    # Type-specific formatting
    if block_type == "heading_1":
        return f"# {text_content}"
    if block_type == "heading_2":
        return f"## {text_content}"
    if block_type == "heading_3":
        return f"### {text_content}"
    if block_type == "bulleted_list_item":
        return f"- {text_content}"
    if block_type == "numbered_list_item":
        # Using a generic "1." as true sequential numbering is complex here.
        return f"1. {text_content}"
    if block_type == "quote":
        return f"> {text_content}"
    if block_type == "to_do":
        checked = content.get("checked", False)
        prefix = "[x] " if checked else "[ ] "
        return f"{prefix}{text_content}"
    if block_type == "callout":
        emoji = content.get("icon", {}).get("emoji", "")
        return f"{emoji} {text_content}".strip()
    if block_type == "paragraph":
        return text_content
    
    # Fallback for any other block that has rich_text but isn't explicitly handled
    if text_content:
        return text_content
    
    return "" # Return empty for unhandled block types like 'image', 'divider', etc.

def _recursively_fetch_block_text(block_id: str, indent_level: int = 0) -> list[str]:
    """Recursively fetches and formats text from a block and its children."""
    all_text = []
    next_cursor = None

    while True:
        try:
            response = notion.blocks.children.list(
                block_id=block_id, start_cursor=next_cursor, page_size=100
            )
            blocks = response.get("results", []) # type: ignore

            for block in blocks:
                # CRITICAL FIX: If the block is a link to a child page, skip it.
                # It will be processed independently by the main loop.
                if block.get("type") == "child_page":
                    continue
                
                # Get text from the current block, if any
                block_text = _get_block_text(block)
                if block_text:
                    all_text.append("  " * indent_level + block_text)

                # If the block has children, recurse, passing the block's ID
                if block.get("has_children"):
                    all_text.extend(_recursively_fetch_block_text(block["id"], indent_level + 1)) # type: ignore

            next_cursor = response.get("next_cursor") # type: ignore
            if not next_cursor:
                break
        except Exception as e:
            # Handle cases where a block is inaccessible (e.g., permissions)
            console.print(f"  [yellow]⚠️ Could not access children of block {block_id}: {e}[/yellow]")
            break
    
    return all_text

def _get_all_blocks_text(page_id: str, progress, task_id, page_title: str) -> str:
    """Paginates through all blocks of a page and concatenates their text, updating progress."""
    progress.update(task_id, description=f"Reading '{page_title}' (recursively)")
    
    all_text_list = _recursively_fetch_block_text(page_id)
            
    return "\n".join(filter(None, all_text_list))

def _discover_child_pages_recursive(block_id: str, discovered_pages: set):
    """
    Recursively finds all child page IDs, providing real-time feedback with titles.
    """
    try:
        next_cursor = None
        while True:
            response = notion.blocks.children.list(block_id=block_id, start_cursor=next_cursor, page_size=100)
            blocks = response.get("results", []) # type: ignore
            for block in blocks:
                if block.get("type") == "child_page":
                    child_page_id = block.get("id")
                    if child_page_id not in discovered_pages:
                        discovered_pages.add(child_page_id)
                        try:
                            # Retrieve page details for real-time feedback
                            page_info = notion.pages.retrieve(page_id=child_page_id)
                            title_list = page_info.get("properties", {}).get("title", {}).get("title", []) # type: ignore
                            title = title_list[0].get("plain_text") if title_list else "Untitled"
                            console.print(f"  [dim] -> Discovered page:[/dim] [cyan]{title}[/cyan]")
                        except Exception:
                            console.print(f"  [dim] -> Discovered page ID:[/dim] [cyan]{child_page_id}[/cyan]")
                        
                        # Recurse into the newly found child page
                        _discover_child_pages_recursive(child_page_id, discovered_pages)
            
            next_cursor = response.get("next_cursor") # type: ignore
            if not next_cursor:
                break
    except Exception as e:
        console.print(f"  [red]⚠️ Error exploring children of block {block_id}: {e}[/red]")

def sync_deleted_pages(chroma_collection, history: dict, notion_page_ids: set):
    """
    Removes documents from ChromaDB and history if their source page no longer exists in Notion.
    This function performs a full audit of the database.
    """
    console.print("🔄 [bold]Syncing deleted pages...[/bold]")
    
    # 1. Get ALL documents from ChromaDB to perform a full audit.
    try:
        all_chroma_docs = chroma_collection.get(include=["metadatas"])
        all_doc_ids = all_chroma_docs.get('ids', [])
        all_metadatas = all_chroma_docs.get('metadatas', [])
    except Exception as e:
        console.print(f"⚠️ Could not get documents from ChromaDB to sync deletes: {e}")
        return

    # 2. Identify document chunks whose page_id is no longer in Notion
    doc_ids_to_delete = []
    chroma_page_ids = set() # For history cleanup
    for i, meta in enumerate(all_metadatas):
        doc_page_id = meta.get('page_id')
        if doc_page_id:
            chroma_page_ids.add(doc_page_id)
            if doc_page_id not in notion_page_ids:
                doc_ids_to_delete.append(all_doc_ids[i])

    # 3. Delete the orphaned chunks from ChromaDB
    if doc_ids_to_delete:
        console.print(f"🗑️ Found {len(doc_ids_to_delete)} orphaned document chunks to delete...")
        try:
            chroma_collection.delete(ids=doc_ids_to_delete)
            console.print("✅ Successfully deleted orphaned chunks from ChromaDB.")
        except Exception as e:
            console.print(f"❌ Error deleting chunks from ChromaDB: {e}")
    else:
        console.print("✅ No orphaned document chunks found in ChromaDB.")

    # 4. Clean up the history file based on what's no longer in Notion
    history_page_ids_to_delete = set(history.keys()) - notion_page_ids
    if history_page_ids_to_delete:
        console.print(f"🗑️ Found {len(history_page_ids_to_delete)} page(s) to remove from history...")
        for page_id in history_page_ids_to_delete:
            del history[page_id]
        console.print("✅ Successfully removed pages from history.")
    else:
        console.print("✅ History file is already up to date.")

def main():
    start_time = time.monotonic()
    console.print(Panel("[bold green]🚀 Notion to ChromaDB Indexer 🚀[/bold green]", expand=False))
    
    if args.reset_chroma:
        console.print("🔥 --reset-chroma flag detected. Deleting database and history.")
        if os.path.exists(PERSIST_DIR):
            try:
                shutil.rmtree(PERSIST_DIR)
                console.print(f"✅ Deleted ChromaDB directory: {PERSIST_DIR}")
            except OSError as e:
                console.print(f"❌ Error deleting directory {PERSIST_DIR}: {e}")
        else:
            console.print(f"🤷 Directory {PERSIST_DIR} not found, nothing to delete.")
        
        history_dir = os.path.dirname(HISTORY_PATH)
        if os.path.exists(history_dir):
            try:
                shutil.rmtree(history_dir)
                console.print(f"✅ Deleted history directory: {history_dir}")
            except OSError as e:
                console.print(f"❌ Error deleting directory {history_dir}: {e}")
        else:
            console.print(f"🤷 Directory {history_dir} not found, nothing to delete.")

        console.print("✅ Reset complete. Proceeding with fresh indexing...")

    console.print(f"🔗 Notion page ID: {NOTION_PAGE_ID}")
    console.print(f"💾 ChromaDB dir: {PERSIST_DIR}")
    console.print(f"📝 History: {HISTORY_PATH}")
    if FORCE_REINDEX:
        console.print("🔄 Forced reindexing enabled")

    # --- 1. Discover Pages ---
    with console.status("[bold green]🔍 Discovering pages and subpages...") as status:
        all_page_ids = {NOTION_PAGE_ID}
        _discover_child_pages_recursive(NOTION_PAGE_ID, all_page_ids)
    page_ids_list = list(all_page_ids)
    console.print(f"📄 [bold]Found a total of {len(page_ids_list)} pages.[/bold]")

    history = load_history(HISTORY_PATH)
    
    # Connect to ChromaDB
    chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
    chroma_collection = chroma_client.get_or_create_collection("notion_collection")
    
    # --- 2. Sync Deleted Pages ---
    sync_deleted_pages(chroma_collection, history, all_page_ids)
    
    # --- 3. Read Notion Documents using custom functions for correct attribution ---
    console.print("\n📖 [bold]Reading & Enriching documents from Notion...[/bold]")
    all_docs = []
    
    with Progress(
        SpinnerColumn(),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("[cyan]{task.description}[/cyan] [bold]({task.completed} of {task.total})[/bold]"),
    ) as progress:
        read_task = progress.add_task("[green]Reading Pages...", total=len(page_ids_list))
        
        for page_id in page_ids_list:
            try:
                # Step 1: Retrieve page metadata first
                page_info = notion.pages.retrieve(page_id=page_id)
                page_title = "Untitled"
                props = page_info.get("properties", {}) # type: ignore
                if "title" in props and props["title"].get("title"):
                    title_list = props["title"]["title"]
                    if title_list:
                        page_title = title_list[0].get("plain_text", "Untitled")
                
                # Step 2: Get text content of THIS PAGE ONLY, updating progress within
                page_content = _get_all_blocks_text(page_id, progress, read_task, page_title)

                # Step 3: Create a Document if content exists
                if page_content.strip():
                    doc = Document(
                        text=page_content,
                        metadata={
                            "page_id": page_id,
                            "title": page_title,
                            "url": page_info.get("url"), # type: ignore
                            "last_edited_time": page_info.get("last_edited_time"), # type: ignore
                        }
                    )
                    all_docs.append(doc)
                else:
                    # For empty pages, we still want to update history so we don't re-check them needlessly
                    last_edit = page_info.get("last_edited_time") # type: ignore
                    # Create a temporary doc with just metadata to check against history
                    temp_doc_for_history = Document(metadata={"page_id": page_id, "last_edited_time": last_edit})
                    if last_edit and should_reindex(temp_doc_for_history, history):
                         history[page_id] = last_edit

            except Exception as e:
                console.print(f"\n[red]⚠️ Failed to process page {page_id}: {e}[/red]")
            finally:
                progress.update(read_task, advance=1)

    console.print(f"✅ Loaded and enriched {len(all_docs)} documents successfully.")

    # --- 4. Configure LlamaIndex Settings ---
    console.print("\n⚙️ [bold]Configuring LlamaIndex Settings...[/bold]")
    
    # Using the default values so they are visible and can be easily changed.
    # Standard chunk size, good for general context.
    chunk_size = 1024 
    # Overlap to avoid losing context between chunks.
    chunk_overlap = 200 

    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-large-en")
    Settings.node_parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    console.print(f"  [dim]‣ Chunk Size:[/dim] [cyan]{chunk_size} tokens[/cyan]")
    console.print(f"  [dim]‣ Chunk Overlap:[/dim] [cyan]{chunk_overlap} tokens[/cyan]")
    console.print(f"  [dim]‣ Embedding Model:[/dim] [cyan]BAAI/bge-large-en[/cyan]")

    # 5) Persistent Chroma client
    console.print(f"\n💾 Initializing ChromaDB at {PERSIST_DIR}...")
    chroma_client = PersistentClient(
        path=PERSIST_DIR,
        settings=ChromaSettings(),
        tenant=DEFAULT_TENANT,
        database=DEFAULT_DATABASE,
    )
    chroma_collection = chroma_client.get_or_create_collection("notion_collection")
    
    # Check if the database is empty, which should trigger a re-index.
    is_db_empty = chroma_collection.count() == 0
    if is_db_empty:
        console.print("⚠️ ChromaDB is empty. Forcing a re-index of all documents.")

    # 6) Filter docs to index
    if FORCE_REINDEX or is_db_empty:
        docs_to_index = all_docs
        if FORCE_REINDEX:
            console.print(f"🔄 Reindexing {len(docs_to_index)} documents (forced by flag)")
        else:
            console.print(f"🔄 Reindexing {len(docs_to_index)} documents (database was empty)")
    else:
        docs_to_index = [doc for doc in all_docs if should_reindex(doc, history)]
        console.print(f"🆕 Documents to index based on last edit time: {len(docs_to_index)}")

    # 7) Cleanly update the index by first deleting old chunks
    if not is_db_empty and docs_to_index:
        page_ids_to_update = {doc.metadata['page_id'] for doc in docs_to_index}
        console.print(f"🔄 Preparing to update {len(page_ids_to_update)} page(s) by deleting their old chunks first...")
        # Ensure the list of page IDs are strings for the filter
        delete_filter = {"page_id": {"$in": [str(pid) for pid in page_ids_to_update]}}
        try:
            chroma_collection.delete(where=delete_filter) # type: ignore
            console.print("✅ Successfully deleted old chunks for pages to be updated.")
        except Exception as e:
            console.print(f"❌ Error deleting old chunks during update: {e}")

    # 8) Index or ensure the index
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    console.print("\n📚 Creating/updating index in ChromaDB...")
    if docs_to_index:
        # Step 1: Manually parse documents into nodes to get a countable total for progress bars
        with Progress(
            SpinnerColumn(), BarColumn(), "[progress.percentage]{task.percentage:>3.0f}%",
            TextColumn("[cyan]{task.description}[/cyan]"), transient=True
        ) as progress:
            task = progress.add_task("[green]Parsing documents into nodes...", total=len(docs_to_index))
            nodes = []
            for doc in docs_to_index:
                nodes.extend(Settings.node_parser.get_nodes_from_documents([doc]))
                progress.update(task, advance=1)
        
        console.print(f"  [dim]‣ Generated {len(nodes)} text nodes (chunks).[/dim]")

        # Step 2: Load the index from the vector store. This gives us an object
        # representing the index in ChromaDB, which we can then add nodes to.
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

        # Step 3: Insert nodes in batches with a progress bar for accurate feedback
        with Progress(
            SpinnerColumn(), BarColumn(), "[progress.percentage]{task.percentage:>3.0f}%",
            TextColumn("[cyan]{task.description}[/cyan] [bold]({task.completed} of {task.total})[/bold]"),
        ) as progress:
            task = progress.add_task("[green]Embedding & Indexing...", total=len(nodes))
            batch_size = 32  # Adjustable batch size
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i+batch_size]
                index.insert_nodes(batch)
                progress.update(task, advance=len(batch))

        console.print(f"✅ Indexed {len(docs_to_index)} new/modified documents.")
    else:
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
        )
        console.print("✅ No changes, index is up to date.")

    # 9) Persist changes (ChromaDB with PersistentClient persists automatically)
    console.print("✅ ChromaDB handles persistence automatically.")

    # 10) Update history
    for doc in docs_to_index:
        pid = doc.metadata.get("page_id")
        last_edit = doc.metadata.get("last_edited_time")
        if pid and last_edit:
            history[pid] = last_edit
    if docs_to_index:
        save_history(history, HISTORY_PATH)
        console.print(f"✅ History updated ({len(docs_to_index)} pages indexed).")
    else:
        console.print("📝 No new pages to update in history.")

    # 11) Check documents in ChromaDB
    count = chroma_collection.count()
    console.print(f"📊 Total documents in ChromaDB: {count}")

    # 12) Final Summary Table
    end_time = time.monotonic()
    total_time = end_time - start_time
    
    summary_table = Table(title="Indexing Complete! 🎉", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="dim", width=25)
    summary_table.add_column("Value", style="bold")
    
    summary_table.add_row("Pages Found", str(len(all_page_ids)))
    summary_table.add_row("Docs Indexed/Updated", str(len(docs_to_index)))
    summary_table.add_row("Total Docs in DB", str(chroma_collection.count()))
    summary_table.add_row("Total Time", f"{total_time:.2f} seconds")
    
    console.print(summary_table)

if __name__ == "__main__":
    main()