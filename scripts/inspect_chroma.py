#!/usr/bin/env python3
"""Legacy inspection wrapper. Prefer `python -m rag_app inspect`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_app.legacy import inspect_chroma_main


if __name__ == "__main__":
    raise SystemExit(inspect_chroma_main())
