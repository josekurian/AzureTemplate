import json
from typing import Any


def _to_markdown_from_paragraphs(paragraphs: list[str], summary: str) -> str:
    lines = ["# Extracted Content", "", summary]
    if paragraphs:
        lines.extend(["", "## Paragraphs"])
        lines.extend(f"- {paragraph}" for paragraph in paragraphs)
    return "\n".join(lines).strip()


def normalize_document_intelligence_result(result: dict[str, Any], *, source: str) -> dict[str, Any]:
    confidence = float(result.get("confidence", 0.0))
    extracted_fields = result.get("extracted_fields", {})
    paragraph_text = result.get("paragraphs", [])
    markdown = result.get("markdown") or _to_markdown_from_paragraphs(paragraph_text, result.get("summary", ""))
    return {
        "title": extracted_fields.get("vendor")
        or extracted_fields.get("merchant_name")
        or source,
        "source": source,
        "document_type": result.get("document_type", "document"),
        "category": "operations_documents",
        "language": extracted_fields.get("language", "en"),
        "access_level": "restricted" if result.get("document_type") in {"invoice", "receipt", "private_event_contract", "custom_event_contract"} else "public",
        "page": 1,
        "section": result.get("document_type"),
        "effective_date": extracted_fields.get("invoice_date") or extracted_fields.get("transaction_date") or extracted_fields.get("event_date"),
        "confidence": confidence,
        "grounding": result.get("grounding_references", []),
        "content_markdown": markdown,
        "structured_fields": extracted_fields,
        "allergen_tags": extracted_fields.get("allergen_tags", []),
        "menu_section": extracted_fields.get("menu_section"),
        "metadata_json": json.dumps({"summary": result.get("summary", ""), "field_count": len(extracted_fields)}),
        "human_review_required": result.get("human_review_required", False),
    }


def normalize_content_understanding_result(result: dict[str, Any], *, source: str) -> dict[str, Any]:
    fields = result.get("fields", {})
    confidence = float(result.get("confidence", 0.0))
    markdown = result.get("markdown", "")
    if not markdown:
        markdown = "\n".join(
            [
                "# Analyzer Output",
                "",
                result.get("summary", ""),
                "",
                "## Fields",
                json.dumps(fields, indent=2),
            ]
        )
    document_type = result.get("document_type") or result.get("analyzer_id", "content_understanding")
    return {
        "title": fields.get("menu_title") or source,
        "source": source,
        "document_type": document_type,
        "category": "multimodal_knowledge",
        "language": result.get("language", "en"),
        "access_level": "internal",
        "page": 1,
        "section": result.get("analyzer_id"),
        "effective_date": None,
        "confidence": confidence,
        "grounding": result.get("grounding_references", []),
        "content_markdown": markdown,
        "structured_fields": fields,
        "allergen_tags": fields.get("allergen_tags", []),
        "menu_section": fields.get("menu_section"),
        "metadata_json": json.dumps({"warnings": result.get("warnings", []), "status": result.get("status")}),
        "human_review_required": result.get("human_review_required", False),
    }
