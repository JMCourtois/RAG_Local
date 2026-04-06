#!/usr/bin/env python3
"""Legacy query wrapper. Prefer `python -m rag_app query`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_app.legacy import query_chroma_main


if __name__ == "__main__":
    raise SystemExit(query_chroma_main())
