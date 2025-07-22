#!/usr/bin/env python3
"""
scripts/inspect_chroma.py - A utility to inspect the contents of the ChromaDB collection.

This script prints a summary of documents grouped by their source file
in a clean, readable table format.
"""

import os
import chromadb
from dotenv import load_dotenv
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Load environment variables
load_dotenv()
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_storage")
console = Console()

def inspect_database():
    """Connects to ChromaDB and prints a summary of its contents in a table."""
    
    if not os.path.exists(CHROMA_PERSIST_DIR):
        console.print(Panel(f"❌ [bold red]Database directory not found[/bold red]\n[dim]{CHROMA_PERSIST_DIR}[/dim]", 
                            title="Error", expand=False, border_style="red"))
        return

    console.print(Panel(f"🔬 Inspecting ChromaDB at [cyan]{CHROMA_PERSIST_DIR}[/cyan]", 
                        title="[bold green]ChromaDB Inspector[/bold green]", expand=False))
    
    try:
        # 1. Connect to the client
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        collection = client.get_collection("local_files_collection")

        # 2. Get all documents
        all_docs = collection.get(include=["metadatas"])
        
        total_docs = len(all_docs.get('ids', []))
        
        if total_docs == 0:
            console.print("\n[bold green]✅ The database is empty.[/bold green]")
            return

        # 3. Group chunks by document_id and aggregate metadata
        docs_summary = defaultdict(lambda: {'count': 0, 'title': 'N/A'})
        all_metadatas = all_docs.get('metadatas', []) or []
        
        for meta in all_metadatas:
            doc_id = str(meta.get('document_id', 'Unknown_ID'))
            docs_summary[doc_id]['count'] += 1
            
            if meta.get('title'):
                docs_summary[doc_id]['title'] = str(meta.get('title'))

        # 4. Create and display the table
        table = Table(title=f"📊 Summary: {total_docs} Chunks Across {len(docs_summary)} Documents",
                      show_header=True, header_style="bold magenta")
        table.add_column("Document ID (Path)", style="dim", no_wrap=True)
        table.add_column("Title", style="cyan", no_wrap=False)
        table.add_column("Chunk Count", justify="right", style="green")

        # Sort documents by title for consistent order
        sorted_docs = sorted(docs_summary.items(), key=lambda item: item[1]['title'])

        for doc_id, data in sorted_docs:
            table.add_row(doc_id, str(data['title']), str(data['count']))
        
        console.print(table)
        console.print("\n[bold green]✅ Inspection complete.[/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]❌ An error occurred during inspection:[/bold red] {e}")


if __name__ == "__main__":
    inspect_database() 