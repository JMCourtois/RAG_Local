#!/usr/bin/env python3
"""
scripts/inspect_chunks.py - Interactively select a document and inspect its stored chunks in ChromaDB.
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
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "local_files_collection")

# --- Main Application ---
def main():
    """
    Main function to run the interactive document chunk inspector.
    """
    console = Console()
    console.print(Rule("[bold #5E81AC]📄 Document Chunk Inspector[/bold #5E81AC]", style="#434C5E"))

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

    # 2. Fetch all documents to build the document list
    try:
        with console.status("[bold #5E81AC]Fetching documents from database...[/]"):
            results = collection.get(include=["metadatas"])
        
        all_metadatas = results.get("metadatas")
        if not all_metadatas:
            console.print("[bold yellow]⚠️ Warning:[/bold yellow] The database is empty. No documents to inspect.")
            return

    except Exception as e:
        console.print(f"[bold red]❌ Error fetching data from ChromaDB:[/bold red] {e}")
        return
    
    # 3. Create a unique list of documents with titles
    documents = {}
    for meta in all_metadatas:
        if isinstance(meta, dict):
            doc_id = meta.get("document_id")
            if doc_id:
                title = meta.get("title", f"Untitled Document ({doc_id})")
                documents[doc_id] = title

    if not documents:
        console.print("[bold yellow]⚠️ No documents with valid 'document_id' metadata found.[/bold yellow]")
        return
        
    # 4. Create choices for questionary and sort them
    choices = [
        questionary.Choice(
            title=f"{title} [ID: {doc_id}]",
            value=doc_id
        ) for doc_id, title in documents.items()
    ]
    choices.sort(key=lambda x: x.title)

    # 5. Present the interactive selector
    try:
        selected_doc_id = questionary.select(
            "Select a document to inspect its chunks:",
            choices=choices,
            use_indicator=True,
            style=questionary.Style([
                ('qmark', 'fg:#5E81AC bold'),
                ('question', 'bold white'),
                ('pointer', 'fg:#5E81AC bold'),
                ('highlighted', 'fg:white bg:#3B4252'),
                ('selected', 'fg:white'),
                ('answer', 'fg:#88C0D0 bold'),
            ])
        ).ask()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Operation cancelled by user.[/bold yellow]")
        return

    if not selected_doc_id:
        console.print("[bold yellow]👋 No document selected. Exiting.[/bold yellow]")
        return

    # 6. Fetch and display chunks for the selected document
    console.print(f"\n[bold]🔍 Fetching chunks for document ID: [cyan]{selected_doc_id}[/cyan]...[/bold]")
    
    try:
        doc_chunks_result = collection.get(
            where={"document_id": selected_doc_id},
            include=["metadatas", "documents"]
        )
    except Exception as e:
        console.print(f"[bold red]❌ Error fetching chunks for document {selected_doc_id}:[/bold red] {e}")
        return

    docs = doc_chunks_result.get('documents')
    chunk_metadatas = doc_chunks_result.get('metadatas')

    if not docs or not chunk_metadatas:
        console.print(f"[bold yellow]🤷 No chunks found for document ID: [cyan]{selected_doc_id}[/cyan][/bold yellow]")
        return

    doc_title = documents.get(selected_doc_id, "Unknown Title")
    console.print(f"[bold green]✅ Found {len(docs)} chunk(s) for document '[bold white]{doc_title}[/bold white]'[/bold green]")
    console.print(Rule(style="#434C5E"))

    for i, (doc, meta) in enumerate(zip(docs, chunk_metadatas)):
        panel_title = Text(f"Chunk {i + 1}/{len(docs)}", style="bold white")
        
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