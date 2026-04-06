from __future__ import annotations

import argparse

from .cli import main as cli_main


def local_to_chroma_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy wrapper for workspace ingestion.")
    parser.add_argument("--source-dir")
    parser.add_argument("--persist-dir")
    parser.add_argument("--collection-name")
    parser.add_argument("--force-reindex", action="store_true")
    parser.add_argument("--reset-chroma", action="store_true")
    args = parser.parse_args(argv)

    forwarded = ["ingest"]
    if args.source_dir:
        forwarded += ["--source-dir", args.source_dir]
    if args.persist_dir:
        forwarded += ["--chroma-dir", args.persist_dir]
    if args.collection_name:
        forwarded += ["--collection-name", args.collection_name]
    if args.reset_chroma:
        forwarded.append("--reset")
    return cli_main(forwarded)


def query_chroma_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy wrapper for workspace querying.")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--persist-dir", default=None)
    parser.add_argument("--sources-debug", action="store_true")
    parser.add_argument("--sources", action="store_true")
    parser.add_argument("--question", default=None)
    args = parser.parse_args(argv)

    forwarded = ["query"]
    if args.top_k is not None:
        forwarded += ["--top-k", str(args.top_k)]
    if args.model:
        forwarded += ["--model", args.model]
    if args.persist_dir:
        forwarded += ["--chroma-dir", args.persist_dir]
    if args.sources_debug:
        forwarded.append("--sources-debug")
    if args.sources:
        forwarded.append("--sources")
    if args.question:
        forwarded += ["--question", args.question]
    else:
        forwarded.append("--interactive")
    return cli_main(forwarded)


def inspect_chroma_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy wrapper for collection inspection.")
    parser.add_argument("--persist-dir", default=None)
    parser.add_argument("--collection-name", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    forwarded = ["inspect"]
    if args.persist_dir:
        forwarded += ["--chroma-dir", args.persist_dir]
    if args.collection_name:
        forwarded += ["--collection-name", args.collection_name]
    if args.json:
        forwarded.append("--json")
    return cli_main(forwarded)


def inspect_chunks_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy wrapper for chunk inspection.")
    parser.add_argument("--persist-dir", default=None)
    parser.add_argument("--collection-name", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    forwarded = ["inspect", "--interactive"]
    if args.persist_dir:
        forwarded += ["--chroma-dir", args.persist_dir]
    if args.collection_name:
        forwarded += ["--collection-name", args.collection_name]
    if args.json:
        forwarded.append("--json")
    return cli_main(forwarded)
