from fastapi.testclient import TestClient

from app.main import app
from app.services.search_client import RestaurantSearchClient


async def test_v2_search_returns_facets_and_correlation_id():
    result = await RestaurantSearchClient().search_knowledge(
        "private dining minimum spend",
        query_type="hybrid",
        document_type="policy",
        include_facets=True,
    )
    assert result["facets"]["document_type"]
    assert result["diagnostics"]["correlation_id"]


async def test_v2_search_zero_result_fallback():
    result = await RestaurantSearchClient().search_knowledge(
        "zzzz impossible query",
        query_type="semantic",
        use_zero_result_fallback=True,
    )
    assert result["diagnostics"]["zero_result_fallback_used"] is True
    assert result["results"]


def test_search_query_v2_endpoint():
    client = TestClient(app)
    response = client.post(
        "/search/query/v2",
        json={
            "query": "vegetarian tasting menu",
            "query_type": "hybrid",
            "document_type": "menu",
            "allergen_tag": "vegetarian",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["facets"]["document_type"]
    assert body["diagnostics"]["used_vector_search"] is True


def test_search_query_log_endpoint():
    client = TestClient(app)
    client.post("/search/query/v2", json={"query": "dress code", "query_type": "keyword"})
    response = client.get("/search/query-log")
    assert response.status_code == 200
    assert response.json()["queries"]
