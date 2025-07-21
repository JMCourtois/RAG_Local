#!/usr/bin/env python3
"""
scripts/inspect_chunks.py - Interactively select a Notion page and inspect its stored chunks in ChromaDB.
"""
import os
from dotenv import load_dotenv
import chromadb
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.markdown import Markdown
import questionary

# --- Configuration ---
load_dotenv()
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_storage")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "notion_collection")

# --- Main Application ---
def main():
    """
    Main function to run the interactive page chunk inspector.
    """
    console = Console()
    console.print(Rule("[bold #5E81AC]📄 Notion Chunk Inspector[/bold #5E81AC]", style="#434C5E"))

    # 1. Connect to ChromaDB
    if not os.path.exists(CHROMA_PERSIST_DIR):
        console.print(f"[bold red]❌ Error:[/bold red] ChromaDB directory not found at '[cyan]{CHROMA_PERSIST_DIR}[/cyan]'.")
        console.print("Please run the ingestion script first.")
        return

    try:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    except Exception as e:
        console.print(f"[bold red]❌ Error connecting to ChromaDB:[/bold red] {e}")
        return

    # 2. Fetch all documents to build the page list
    try:
        with console.status("[bold #5E81AC]Fetching pages from database...[/]"):
            results = collection.get(include=["metadatas"])
        
        all_metadatas = results.get("metadatas")
        if not all_metadatas:
            console.print("[bold yellow]⚠️ Warning:[/bold yellow] The database is empty. No pages to inspect.")
            return

    except Exception as e:
        console.print(f"[bold red]❌ Error fetching data from ChromaDB:[/bold red] {e}")
        return
    
    # 3. Create a unique list of pages with titles
    pages = {}
    for meta in all_metadatas:
        if isinstance(meta, dict):
            page_id = meta.get("page_id")
            if page_id:
                title = meta.get("title", f"Untitled Page ({page_id[:8]}...)")
                pages[page_id] = title

    if not pages:
        console.print("[bold yellow]⚠️ No pages with valid 'page_id' metadata found in the database.[/bold yellow]")
        return
        
    # 4. Create choices for questionary and sort them
    choices = [
        questionary.Choice(
            title=f"{title} [ID: ...{page_id[-3:]}]",
            value=page_id
        ) for page_id, title in pages.items()
    ]
    # Sort choices alphabetically by title
    choices.sort(key=lambda x: x.title)

    # 5. Present the interactive selector
    try:
        selected_page_id = questionary.select(
            "Select a page to inspect its chunks:",
            choices=choices,
            use_indicator=True,
            style=questionary.Style([
                ('qmark', 'fg:#5E81AC bold'),
                ('question', 'bold white'),
                ('pointer', 'fg:#5E81AC bold'),
                ('highlighted', 'fg:white bg:#3B4252'), # Subtle background
                ('selected', 'fg:white'), # Cleaner look, no bold
                ('answer', 'fg:#88C0D0 bold'),
            ])
        ).ask()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Operation cancelled by user.[/bold yellow]")
        return

    if not selected_page_id:
        console.print("[bold yellow]👋 No page selected. Exiting.[/bold yellow]")
        return

    # 6. Fetch and display chunks for the selected page
    console.print(f"\n[bold]🔍 Fetching chunks for page ID: [cyan]{selected_page_id}[/cyan]...[/bold]")
    
    try:
        page_chunks_result = collection.get(
            where={"page_id": selected_page_id},
            include=["metadatas", "documents"]
        )
    except Exception as e:
        console.print(f"[bold red]❌ Error fetching chunks for page {selected_page_id}:[/bold red] {e}")
        return

    documents = page_chunks_result.get('documents')
    chunk_metadatas = page_chunks_result.get('metadatas')

    if not documents or not chunk_metadatas:
        console.print(f"[bold yellow]🤷 No chunks found for page ID: [cyan]{selected_page_id}[/cyan][/bold yellow]")
        return

    page_title = pages.get(selected_page_id, "Unknown Title")
    console.print(f"[bold green]✅ Found {len(documents)} chunk(s) for page '[bold white]{page_title}[/bold white]'[/bold green]")
    console.print(Rule(style="#434C5E"))

    for i, (doc, meta) in enumerate(zip(documents, chunk_metadatas)):
        panel_title = Text(f"Chunk {i + 1}/{len(documents)}", style="bold white")
        
        meta_info = Text()
        meta_info.append("Metadata:\n", style="bold underline grey50")
        if isinstance(meta, dict):
            for key, value in meta.items():
                meta_info.append(f"  • {key}: ", style="grey50")
                meta_info.append(str(value) + "\n", style="grey50")

        content_md = Markdown(doc or "*No content*", style="white")
        
        panel_content = Group(meta_info, content_md)
        
        console.print(
            Panel(
                panel_content,
                title=panel_title,
                border_style="#5E81AC",
                expand=False,
                padding=(1, 2)
            )
        )

if __name__ == "__main__":
    main() 