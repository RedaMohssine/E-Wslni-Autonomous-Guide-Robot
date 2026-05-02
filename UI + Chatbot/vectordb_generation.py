"""Rebuild the Chroma vector DB from every source document under data/.

Discovers files dynamically so adding new PDFs / Markdown / JSON to data/
just works without editing this script.

Run from the project root after deleting the old vector_db/:

  $ cd robot-assistant-chatbot
  $ rm -rf vector_db
  $ python -m src.vectordb_generation
"""
from glob import glob
from pathlib import Path

from src.services.rag import RAGService


DATA_DIR = "data"

# Files we explicitly do NOT want in the vector DB.
EXCLUDED_FILES = {
    "locations.json",          # consumed by NavigationService at runtime
    "emines_docs.json",        # superseded by cleaned_emines_docs.json
}

# Glob patterns we ingest, in priority order.
PATTERNS = ("*.pdf", "*.md", "*.markdown", "*.txt", "*.json")


def _discover_sources() -> list[str]:
    seen: set[str] = set()
    paths: list[str] = []
    for pattern in PATTERNS:
        for path in sorted(glob(f"{DATA_DIR}/{pattern}")):
            name = Path(path).name
            if name in EXCLUDED_FILES or name in seen:
                continue
            seen.add(name)
            paths.append(path)
    return paths


if __name__ == "__main__":
    sources = _discover_sources()
    print("Ingesting:")
    for p in sources:
        print(f"  - {p}")

    RAGService().ingest_files(sources)
