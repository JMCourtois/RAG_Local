#!/usr/bin/env python3
"""Legacy ingestion wrapper. Prefer `python -m rag_app ingest`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_app.legacy import local_to_chroma_main


if __name__ == "__main__":
    raise SystemExit(local_to_chroma_main())
