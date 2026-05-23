import json
from pathlib import Path
from typing import Any

import httpx

from app.core.auth import get_credential
from app.core.config import settings


class ContentUnderstandingClient:
    def __init__(self) -> None:
        self._analyzers = self._load_analyzers()

    def _analyzers_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "analyzers"

    def _load_analyzers(self) -> dict[str, dict[str, Any]]:
        analyzers: dict[str, dict[str, Any]] = {}
        analyzers_dir = self._analyzers_dir()
        if not analyzers_dir.exists():
            return analyzers
        for path in analyzers_dir.glob("*.json"):
            analyzers[path.stem] = json.loads(path.read_text())
        return analyzers

    def list_analyzers(self) -> list[dict[str, Any]]:
        return [
            {
                "analyzer_id": analyzer_id,
                "name": definition.get("name", analyzer_id),
                "input_kinds": definition.get("inputKinds", []),
                "targets": definition.get("targets", []),
                "default_options": definition.get("defaultOptions", {}),
            }
            for analyzer_id, definition in sorted(self._analyzers.items())
        ]

    def _normalize_mock_payload(
        self,
        *,
        analyzer_id: str,
        summary: str,
        fields: dict[str, Any],
        confidence: float,
        filename: str | None,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        analyzer = self._analyzers.get(analyzer_id, {})
        name = analyzer.get("name", analyzer_id)
        source_name = filename or f"{analyzer_id}.sample"
        return {
            "analyzer_id": analyzer_id,
            "document_type": analyzer_id,
            "status": "succeeded",
            "summary": summary,
            "fields": fields,
            "warnings": warnings or [],
            "confidence": confidence,
            "markdown": "\n".join(
                [
                    f"# {name}",
                    "",
                    summary,
                    "",
                    "## Extracted fields",
                    json.dumps(fields, indent=2),
                ]
            ),
            "grounding_references": [
                {
                    "source": source_name,
                    "title": name,
                    "chunk_id": f"{analyzer_id}-grounding-1",
                    "page": 1,
                    "section": analyzer_id,
                    "confidence": confidence,
                    "excerpt": summary[:220],
                }
            ],
            "evidence": [{"source": source_name, "label": name, "confidence": confidence}],
            "human_review_required": confidence < 0.9,
        }

    def _mock_payload(self, analyzer_id: str, filename: str | None = None) -> dict[str, Any]:
        if analyzer_id == "menu_pdf":
            return self._normalize_mock_payload(
                analyzer_id=analyzer_id,
                filename=filename,
                confidence=0.94,
                summary="Detected tasting menu structure, allergens, and premium upsell opportunities from a menu PDF.",
                fields={
                    "menu_title": "Chef's Seasonal Tasting",
                    "course_count": 8,
                    "allergen_tags": ["shellfish", "dairy"],
                    "upsell_candidates": ["Grand Reserve Pairing", "Supplemental caviar course"],
                    "menu_section": "tasting",
                },
            )
        if analyzer_id == "event_contract":
            return self._normalize_mock_payload(
                analyzer_id=analyzer_id,
                filename=filename,
                confidence=0.88,
                summary="Extracted party size, minimum spend, deposit, and approval clauses from a private event contract.",
                fields={
                    "party_size": 18,
                    "minimum_spend": 5000,
                    "deposit_required": 1500,
                    "approval_required": True,
                },
                warnings=["Human review recommended before guest confirmation."],
            )
        if analyzer_id == "chef_video":
            return self._normalize_mock_payload(
                analyzer_id=analyzer_id,
                filename=filename,
                confidence=0.91,
                summary="Chef training clip shows plating consistency with minor garnish placement variance.",
                fields={
                    "service_line": "chef-pass",
                    "quality_score": 0.91,
                    "issues": ["Garnish offset in final plating frame"],
                },
            )
        if analyzer_id == "guest_call_audio":
            return self._normalize_mock_payload(
                analyzer_id=analyzer_id,
                filename=filename,
                confidence=0.93,
                summary="Guest call indicates reservation intent, anniversary occasion, and shellfish allergy.",
                fields={
                    "intent": "reservation",
                    "occasion": "anniversary",
                    "allergy": "shellfish",
                    "handoff_recommended": False,
                },
            )
        return self._normalize_mock_payload(
            analyzer_id=analyzer_id,
            filename=filename,
            confidence=0.9,
            summary="Supplier invoice review detected total amount, invoice number, and payment urgency.",
            fields={"invoice_number": "INV-2026-0422", "total": 1842.75, "rush_payment": False},
        )

    async def analyze_content(
        self,
        *,
        analyzer_id: str,
        content_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        if settings.mock_mode or not settings.azure_content_understanding_endpoint:
            return self._mock_payload(analyzer_id, filename=filename)

        token = get_credential().get_token("https://cognitiveservices.azure.com/.default").token
        endpoint = settings.azure_content_understanding_endpoint.rstrip("/")
        url = (
            f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze"
            f"?api-version={settings.azure_content_understanding_api_version}"
        )
        headers = {"Authorization": f"Bearer {token}", "Content-Type": content_type or "application/octet-stream"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, content=content_bytes)
            response.raise_for_status()
            payload = response.json()

        fields = payload.get("fields", {})
        confidence = float(payload.get("confidence", 0.0))
        summary = payload.get("summary", f"Analyzer {analyzer_id} accepted the document.")
        analyzer = self._analyzers.get(analyzer_id, {})
        title = analyzer.get("name", analyzer_id)
        return {
            "analyzer_id": analyzer_id,
            "document_type": analyzer_id,
            "status": payload.get("status", "submitted"),
            "summary": summary,
            "fields": fields,
            "warnings": payload.get("warnings", []),
            "confidence": confidence,
            "markdown": payload.get("markdown")
            or "\n".join([f"# {title}", "", summary, "", json.dumps(fields, indent=2)]),
            "grounding_references": payload.get("groundingReferences", []),
            "evidence": payload.get("evidence", []),
            "human_review_required": confidence < 0.9,
        }
