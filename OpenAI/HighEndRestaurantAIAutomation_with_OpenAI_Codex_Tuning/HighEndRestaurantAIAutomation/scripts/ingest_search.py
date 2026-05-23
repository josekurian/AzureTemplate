"""Create or update AI Search documents from sample restaurant files.

Codex TODO:
- Create index from infra/bicep/search-index.json if missing.
- Generate embeddings using Azure OpenAI.
- Upload documents to Azure AI Search.
"""
from pathlib import Path
import json

for path in Path('data').rglob('*'):
    if path.is_file():
        print(f"Would ingest: {path}")
