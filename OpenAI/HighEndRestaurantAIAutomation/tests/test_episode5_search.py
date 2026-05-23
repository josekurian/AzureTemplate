from fastapi.testclient import TestClient

from app.main import app
from app.services.search_client import RestaurantSearchClient


async def test_search_client_returns_citations_and_diagnostics():
    result = await RestaurantSearchClient().search_knowledge(
        "What is the private dining minimum spend?",
        query_type="hybrid",
        top_k=3,
        document_type="policy",
    )
    assert result["citations"]
    assert result["diagnostics"]["query_type"] == "hybrid"
    assert result["diagnostics"]["used_vector_search"] is True


async def test_search_client_applies_allergen_filter():
    result = await RestaurantSearchClient().search_knowledge(
        "vegetarian tasting menu",
        allergen_tag="vegetarian",
        document_type="menu",
    )
    assert result["results"]
    assert all("vegetarian" in item["allergen_tags"] for item in result["results"])


def test_search_query_endpoint():
    client = TestClient(app)
    response = client.post(
        "/search/query",
        json={
            "query": "What is your dress code?",
            "query_type": "semantic",
            "top_k": 2,
            "document_type": "policy",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"]
    assert body["diagnostics"]["used_semantic_ranker"] is True


def test_search_ingest_status_endpoint():
    client = TestClient(app)
    response = client.get("/search/ingest-status")
    assert response.status_code == 200
    assert response.json()["document_count"] >= 1
