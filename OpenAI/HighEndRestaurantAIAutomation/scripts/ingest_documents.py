import asyncio
import json
from pathlib import Path
from typing import Any

from azure.search.documents import SearchClient

from app.core.auth import get_credential
from app.core.config import settings
from app.services.openai_client import AzureOpenAIClient

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def discover_documents() -> list[Path]:
    return [path for path in DATA_DIR.rglob("*") if path.is_file()]


def chunk_text(text: str, *, max_chars: int = 900, overlap: int = 150) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + max_chars)
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def extract_text(path: Path) -> str:
    if path.suffix == ".json":
        payload = json.loads(path.read_text())
        return json.dumps(payload, indent=2)
    return path.read_text()


def metadata_for(path: Path, chunk_index: int, content: str) -> dict[str, Any]:
    lowered = content.lower()
    document_type = "faq" if "faq" in path.name else "policy" if "policy" in path.name else "menu"
    if "contract" in lowered or "private dining" in lowered:
        document_type = "contract"
    menu_section = None
    if "tasting" in lowered:
        menu_section = "tasting"
    elif "pairing" in lowered or "wine" in lowered:
        menu_section = "pairings"
    allergen_tags = []
    for tag in ("shellfish", "dairy", "nut", "gluten", "vegan", "vegetarian"):
        if tag in lowered:
            allergen_tags.append(tag)
    return {
        "id": f"{path.stem}-{chunk_index}",
        "chunk_id": f"{path.stem}-{chunk_index}",
        "title": path.stem.replace("_", " ").title(),
        "source": str(path.relative_to(DATA_DIR.parent)),
        "document_type": document_type,
        "menu_section": menu_section,
        "page_number": chunk_index + 1,
        "allergen_tags": allergen_tags,
        "content": content,
        "metadata_json": json.dumps(
            {
                "relative_path": str(path.relative_to(ROOT)),
                "extension": path.suffix,
            }
        ),
    }


async def build_documents() -> list[dict[str, Any]]:
    embedding_client = AzureOpenAIClient()
    documents = []
    for path in discover_documents():
        chunks = chunk_text(extract_text(path))
        for index, chunk in enumerate(chunks):
            record = metadata_for(path, index, chunk)
            record["content_vector"] = await embedding_client.embed(chunk)
            documents.append(record)
    return documents


async def upload_documents(documents: list[dict[str, Any]]) -> None:
    client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index,
        credential=get_credential(),
    )
    client.upload_documents(documents=documents)


async def main() -> None:
    documents = await build_documents()
    print(f"Prepared {len(documents)} chunks for search ingestion")
    if settings.mock_mode or not settings.azure_search_endpoint:
        print("Mock mode is enabled or no search endpoint is configured. Skipping upload.")
        return
    await upload_documents(documents)
    print(f"Uploaded chunks to {settings.azure_search_index}")


if __name__ == "__main__":
    asyncio.run(main())
