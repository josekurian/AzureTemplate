from fastapi.testclient import TestClient

from app.ingestion.chunking import chunk_markdown
from app.main import app


def test_chunking_is_deterministic():
    content = "# Policy\nGuest allergies must be disclosed at booking.\n" * 10
    one = chunk_markdown(content, source_id="policy-doc", metadata={"title": "Policy", "page": 1})
    two = chunk_markdown(content, source_id="policy-doc", metadata={"title": "Policy", "page": 1})
    assert one
    assert [item["chunk_id"] for item in one] == [item["chunk_id"] for item in two]


def test_ingestion_job_routes_to_review_for_low_confidence_contract():
    client = TestClient(app)
    response = client.post(
        "/ingestion/jobs",
        files={"file": ("private_event_contract.pdf", b"fake-pdf", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    assert body["review_id"]


def test_ingestion_job_indexes_menu_and_query_review_endpoints():
    client = TestClient(app)
    create = client.post(
        "/ingestion/jobs",
        files={"file": ("menu.pdf", b"fake-menu", "application/pdf")},
    )
    assert create.status_code == 200
    body = create.json()
    assert body["status"] == "completed"
    assert body["indexed_document_ids"]
    jobs = client.get("/ingestion/jobs")
    assert jobs.status_code == 200
    assert jobs.json()["jobs"]


def test_review_approve_and_correct_endpoints():
    client = TestClient(app)
    create = client.post(
        "/ingestion/jobs",
        files={"file": ("supplier_contract.pdf", b"fake-contract", "application/pdf")},
    ).json()
    review_id = create["review_id"]
    reviews = client.get("/reviews")
    assert reviews.status_code == 200
    assert any(item["review_id"] == review_id for item in reviews.json())
    corrected = client.post(
        f"/reviews/{review_id}/correct",
        json={"actor": "manager@example.com", "notes": "Updated minimum spend", "corrections": {"minimum_spend": 6500}},
    )
    assert corrected.status_code == 200
    assert corrected.json()["status"] == "corrected"
