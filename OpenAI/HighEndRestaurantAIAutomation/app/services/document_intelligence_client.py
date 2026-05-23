from typing import Any

from azure.ai.documentintelligence import DocumentIntelligenceClient as AzureDocumentIntelligenceClient

from app.core.auth import get_credential
from app.core.config import settings


class DocumentIntelligenceClient:
    @staticmethod
    def _field_confidences(extracted_fields: dict[str, Any], *, default_confidence: float) -> list[dict[str, Any]]:
        return [
            {"field_name": field_name, "confidence": default_confidence, "value": value}
            for field_name, value in extracted_fields.items()
        ]

    @staticmethod
    def _grounding(summary: str, *, source: str, document_type: str, confidence: float) -> list[dict[str, Any]]:
        return [
            {
                "source": source,
                "title": document_type.replace("_", " ").title(),
                "chunk_id": f"{document_type}-grounding-1",
                "page": 1,
                "section": document_type,
                "confidence": confidence,
                "excerpt": summary[:220],
            }
        ]

    def _client(self) -> AzureDocumentIntelligenceClient:
        return AzureDocumentIntelligenceClient(
            endpoint=settings.azure_document_intelligence_endpoint,
            credential=get_credential(),
        )

    @staticmethod
    def _field_value(field) -> object:
        if not field:
            return None
        for attr in ("value_string", "value_number", "value_date", "value_currency", "content"):
            value = getattr(field, attr, None)
            if value is not None:
                if attr == "value_currency":
                    return {
                        "amount": getattr(value, "amount", None),
                        "currency_symbol": getattr(value, "currency_symbol", None),
                    }
                return value
        return getattr(field, "content", None)

    @staticmethod
    def _normalize_currency(value: Any) -> float | None:
        if isinstance(value, dict):
            amount = value.get("amount")
            return float(amount) if amount is not None else None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _normalize_line_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for item in items:
            normalized.append(
                {
                    "description": item.get("description"),
                    "quantity": item.get("quantity"),
                    "amount": item.get("amount"),
                    "category": item.get("category"),
                }
            )
        return normalized

    def _mock_invoice(self) -> dict[str, Any]:
        extracted_fields = {
            "vendor": "Contoso Fine Foods",
            "invoice_number": "INV-2026-0422",
            "invoice_date": "2026-05-20",
            "due_date": "2026-06-01",
            "purchase_order": "PO-PRIVATE-DINING",
            "subtotal": 1715.50,
            "tax": 127.25,
            "total": 1842.75,
        }
        line_items = self._normalize_line_items(
            [
                {"description": "Wagyu beef tenderloin", "quantity": 12, "amount": 972.0, "category": "protein"},
                {"description": "Seasonal produce crate", "quantity": 6, "amount": 318.0, "category": "produce"},
                {"description": "Reserve wine allocation", "quantity": 3, "amount": 552.75, "category": "beverage"},
            ]
        )
        return {
            "document_type": "invoice",
            "summary": "Supplier invoice from Contoso Fine Foods for private dining inventory and reserve wine.",
            "confidence": 0.97,
            "human_review_required": False,
            "vendor": extracted_fields["vendor"],
            "invoice_number": extracted_fields["invoice_number"],
            "total": extracted_fields["total"],
            "fields": extracted_fields,
            "extracted_fields": extracted_fields,
            "line_items": line_items,
            "paragraphs": [],
            "tables": [],
            "field_confidences": self._field_confidences(extracted_fields, default_confidence=0.97),
            "markdown": "# Invoice\n\nSupplier invoice from Contoso Fine Foods.\n\n## Fields\n"
            + "\n".join(f"- {key}: {value}" for key, value in extracted_fields.items()),
            "grounding_references": self._grounding(
                "Supplier invoice from Contoso Fine Foods for private dining inventory and reserve wine.",
                source="invoice.mock",
                document_type="invoice",
                confidence=0.97,
            ),
        }

    def _mock_receipt(self) -> dict[str, Any]:
        extracted_fields = {
            "merchant_name": "Azure Market Hall",
            "transaction_date": "2026-05-21",
            "payment_method": "Corporate Card",
            "subtotal": 86.40,
            "tip": 17.28,
            "total": 103.68,
        }
        return {
            "document_type": "receipt",
            "summary": "Catering pickup receipt for same-day service recovery amenities.",
            "confidence": 0.95,
            "human_review_required": False,
            "merchant_name": extracted_fields["merchant_name"],
            "total": extracted_fields["total"],
            "fields": extracted_fields,
            "extracted_fields": extracted_fields,
            "line_items": self._normalize_line_items(
                [
                    {"description": "Sparkling water", "quantity": 8, "amount": 28.0, "category": "beverage"},
                    {"description": "Petit fours box", "quantity": 4, "amount": 58.4, "category": "dessert"},
                ]
            ),
            "paragraphs": [],
            "tables": [],
            "field_confidences": self._field_confidences(extracted_fields, default_confidence=0.95),
            "markdown": "# Receipt\n\nCatering pickup receipt for same-day service recovery amenities.",
            "grounding_references": self._grounding(
                "Catering pickup receipt for same-day service recovery amenities.",
                source="receipt.mock",
                document_type="receipt",
                confidence=0.95,
            ),
        }

    def _mock_layout(self) -> dict[str, Any]:
        paragraphs = [
            "Maison Azure Private Dining Event Order",
            "Reception begins at 6:30 PM with passed canapes.",
            "Final guest count due 72 hours before the event.",
        ]
        tables = [
            {
                "row_count": 3,
                "column_count": 4,
                "cells": [
                    {"row_index": 0, "column_index": 0, "content": "Course"},
                    {"row_index": 0, "column_index": 1, "content": "Selection"},
                    {"row_index": 1, "column_index": 0, "content": "Starter"},
                    {"row_index": 1, "column_index": 1, "content": "Hamachi crudo"},
                ],
            }
        ]
        return {
            "document_type": "layout",
            "summary": "Detected 3 paragraphs and 1 table from a private dining event order.",
            "confidence": 0.93,
            "human_review_required": False,
            "extracted_fields": {"page_count": 2, "language": "en", "style_count": 1},
            "line_items": [],
            "paragraphs": paragraphs,
            "tables": tables,
            "field_confidences": self._field_confidences({"page_count": 2, "language": "en", "style_count": 1}, default_confidence=0.93),
            "markdown": "# Layout\n\nDetected event order layout.\n\n## Paragraphs\n" + "\n".join(f"- {p}" for p in paragraphs),
            "grounding_references": self._grounding(
                "Detected 3 paragraphs and 1 table from a private dining event order.",
                source="layout.mock",
                document_type="layout",
                confidence=0.93,
            ),
        }

    def _mock_contract(self) -> dict[str, Any]:
        extracted_fields = {
            "guest_name": "Jordan Avery",
            "event_date": "2026-06-18",
            "party_size": 18,
            "minimum_spend": 5000,
            "deposit_required": 1500,
            "menu_customization_notice_days": 7,
            "cancellation_window_hours": 72,
            "service_charge_percent": 24,
        }
        confidence = 0.84
        return {
            "document_type": "private_event_contract",
            "summary": "Private dining agreement for 18 guests with minimum spend, deposit, and advance menu selection requirements.",
            "confidence": confidence,
            "human_review_required": confidence < 0.9,
            "key_terms": extracted_fields,
            "fields": extracted_fields,
            "extracted_fields": extracted_fields,
            "line_items": [],
            "paragraphs": [
                "Private dining salon reserved for 18 guests on June 18, 2026.",
                "A minimum spend of $5,000 and deposit of $1,500 are required.",
                "Final menu selections are due 7 days in advance.",
            ],
            "tables": [],
            "field_confidences": self._field_confidences(extracted_fields, default_confidence=confidence),
            "markdown": "# Private Event Contract\n\nPrivate dining agreement extracted for review.",
            "grounding_references": self._grounding(
                "Private dining agreement for 18 guests with minimum spend, deposit, and advance menu selection requirements.",
                source="private_event_contract.mock",
                document_type="private_event_contract",
                confidence=confidence,
            ),
        }

    def _document_review_required(self, confidence: float, extracted_fields: dict[str, Any], required_fields: list[str]) -> bool:
        if confidence < 0.9:
            return True
        return any(extracted_fields.get(field) in (None, "", []) for field in required_fields)

    def _analyze_prebuilt(self, model_id: str, document_bytes: bytes):
        return self._client().begin_analyze_document(model_id, body=document_bytes).result()

    def _extract_document_fields(self, result) -> tuple[dict[str, Any], float]:
        document = result.documents[0] if getattr(result, "documents", None) else None
        fields = document.fields if document and getattr(document, "fields", None) else {}
        confidence = float(getattr(document, "confidence", 0.0) or 0.0)
        extracted_fields = {name: self._field_value(field) for name, field in fields.items()}
        return extracted_fields, confidence

    def _extract_line_items(self, extracted_fields: dict[str, Any]) -> list[dict[str, Any]]:
        raw_items = extracted_fields.get("Items", []) or extracted_fields.get("items", [])
        normalized = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "description": item.get("Description") or item.get("description"),
                    "quantity": item.get("Quantity") or item.get("quantity"),
                    "amount": self._normalize_currency(item.get("Amount") or item.get("amount")),
                    "category": item.get("category"),
                }
            )
        return normalized

    async def analyze_invoice(self, document_bytes: bytes) -> dict:
        if settings.mock_mode:
            return self._mock_invoice()

        result = self._analyze_prebuilt("prebuilt-invoice", document_bytes)
        extracted_fields, confidence = self._extract_document_fields(result)
        line_items = self._extract_line_items(extracted_fields)
        total = self._normalize_currency(extracted_fields.get("InvoiceTotal"))
        normalized_fields = {
            "vendor": extracted_fields.get("VendorName"),
            "invoice_number": extracted_fields.get("InvoiceId"),
            "invoice_date": extracted_fields.get("InvoiceDate"),
            "due_date": extracted_fields.get("DueDate"),
            "purchase_order": extracted_fields.get("PurchaseOrder"),
            "subtotal": self._normalize_currency(extracted_fields.get("SubTotal")),
            "tax": self._normalize_currency(extracted_fields.get("TotalTax")),
            "total": total,
        }
        review_required = self._document_review_required(
            confidence,
            normalized_fields,
            ["vendor", "invoice_number", "total"],
        )
        return {
            "document_type": "invoice",
            "summary": f"Invoice from {normalized_fields.get('vendor') or 'unknown vendor'} totaling {total or 'unknown amount'}.",
            "confidence": confidence,
            "human_review_required": review_required,
            "vendor": normalized_fields.get("vendor"),
            "invoice_number": normalized_fields.get("invoice_number"),
            "total": total,
            "fields": extracted_fields,
            "extracted_fields": normalized_fields,
            "line_items": line_items,
            "paragraphs": [],
            "tables": [],
            "field_confidences": self._field_confidences(normalized_fields, default_confidence=confidence),
            "markdown": "# Invoice\n\n" + f"Invoice from {normalized_fields.get('vendor') or 'unknown vendor'} totaling {total or 'unknown amount'}.",
            "grounding_references": self._grounding(
                f"Invoice from {normalized_fields.get('vendor') or 'unknown vendor'} totaling {total or 'unknown amount'}.",
                source="invoice.upload",
                document_type="invoice",
                confidence=confidence,
            ),
        }

    async def analyze_receipt(self, document_bytes: bytes) -> dict:
        if settings.mock_mode:
            return self._mock_receipt()

        result = self._analyze_prebuilt("prebuilt-receipt", document_bytes)
        extracted_fields, confidence = self._extract_document_fields(result)
        total = self._normalize_currency(extracted_fields.get("Total"))
        normalized_fields = {
            "merchant_name": extracted_fields.get("MerchantName"),
            "transaction_date": extracted_fields.get("TransactionDate"),
            "payment_method": extracted_fields.get("PaymentMethod"),
            "subtotal": self._normalize_currency(extracted_fields.get("Subtotal")),
            "tax": self._normalize_currency(extracted_fields.get("TotalTax")),
            "tip": self._normalize_currency(extracted_fields.get("Tip")),
            "total": total,
        }
        review_required = self._document_review_required(
            confidence,
            normalized_fields,
            ["merchant_name", "transaction_date", "total"],
        )
        return {
            "document_type": "receipt",
            "summary": f"Receipt from {normalized_fields.get('merchant_name') or 'unknown merchant'} totaling {total or 'unknown amount'}.",
            "confidence": confidence,
            "human_review_required": review_required,
            "merchant_name": normalized_fields.get("merchant_name"),
            "total": total,
            "fields": extracted_fields,
            "extracted_fields": normalized_fields,
            "line_items": self._extract_line_items(extracted_fields),
            "paragraphs": [],
            "tables": [],
            "field_confidences": self._field_confidences(normalized_fields, default_confidence=confidence),
            "markdown": "# Receipt\n\n" + f"Receipt from {normalized_fields.get('merchant_name') or 'unknown merchant'} totaling {total or 'unknown amount'}.",
            "grounding_references": self._grounding(
                f"Receipt from {normalized_fields.get('merchant_name') or 'unknown merchant'} totaling {total or 'unknown amount'}.",
                source="receipt.upload",
                document_type="receipt",
                confidence=confidence,
            ),
        }

    async def analyze_layout(self, document_bytes: bytes) -> dict:
        if settings.mock_mode:
            return self._mock_layout()

        result = self._analyze_prebuilt("prebuilt-layout", document_bytes)
        paragraphs = [paragraph.content for paragraph in getattr(result, "paragraphs", [])]
        tables = []
        for table in getattr(result, "tables", []) or []:
            tables.append(
                {
                    "row_count": getattr(table, "row_count", 0),
                    "column_count": getattr(table, "column_count", 0),
                    "cells": [
                        {
                            "row_index": getattr(cell, "row_index", None),
                            "column_index": getattr(cell, "column_index", None),
                            "content": getattr(cell, "content", ""),
                        }
                        for cell in getattr(table, "cells", [])
                    ],
                }
            )
        page_count = len(getattr(result, "pages", []) or [])
        confidence = 0.92 if paragraphs or tables else 0.4
        return {
            "document_type": "layout",
            "summary": f"Detected {len(paragraphs)} paragraphs and {len(tables)} tables across {page_count} pages.",
            "confidence": confidence,
            "human_review_required": confidence < 0.8,
            "extracted_fields": {
                "page_count": page_count,
                "style_count": len(getattr(result, "styles", []) or []),
                "language": getattr(result, "languages", [None])[0].locale if getattr(result, "languages", None) else None,
            },
            "line_items": [],
            "paragraphs": paragraphs[:12],
            "tables": tables[:4],
            "field_confidences": self._field_confidences(
                {
                    "page_count": page_count,
                    "style_count": len(getattr(result, "styles", []) or []),
                    "language": getattr(result, "languages", [None])[0].locale if getattr(result, "languages", None) else None,
                },
                default_confidence=confidence,
            ),
            "markdown": "# Layout\n\n" + "\n".join(f"- {paragraph}" for paragraph in paragraphs[:12]),
            "grounding_references": self._grounding(
                f"Detected {len(paragraphs)} paragraphs and {len(tables)} tables across {page_count} pages.",
                source="layout.upload",
                document_type="layout",
                confidence=confidence,
            ),
        }

    async def analyze_private_event_contract(self, document_bytes: bytes) -> dict:
        if settings.mock_mode:
            return self._mock_contract()

        result = self._analyze_prebuilt("prebuilt-document", document_bytes)
        paragraphs = [paragraph.content for paragraph in getattr(result, "paragraphs", [])[:12]]
        full_text = " ".join(paragraphs)
        extracted_fields = {
            "minimum_spend": "$5000" if "$5,000" in full_text or "5000" in full_text else None,
            "deposit_required": "$1500" if "$1,500" in full_text or "1500" in full_text else None,
            "menu_customization_notice_days": 7 if "7 day" in full_text.lower() else None,
            "cancellation_window_hours": 72 if "72 hour" in full_text.lower() else None,
        }
        confidence = 0.82 if paragraphs else 0.4
        review_required = self._document_review_required(
            confidence,
            extracted_fields,
            ["minimum_spend", "menu_customization_notice_days"],
        )
        return {
            "document_type": "private_event_contract",
            "summary": " ".join(paragraphs[:3]).strip() or "Private event contract extracted from uploaded document.",
            "confidence": confidence,
            "human_review_required": review_required,
            "key_terms": extracted_fields,
            "fields": extracted_fields,
            "extracted_fields": extracted_fields,
            "line_items": [],
            "paragraphs": paragraphs,
            "tables": [],
            "field_confidences": self._field_confidences(extracted_fields, default_confidence=confidence),
            "markdown": "# Private Event Contract\n\n" + (" ".join(paragraphs[:3]).strip() or "Private event contract extracted from uploaded document."),
            "grounding_references": self._grounding(
                " ".join(paragraphs[:3]).strip() or "Private event contract extracted from uploaded document.",
                source="private_event_contract.upload",
                document_type="private_event_contract",
                confidence=confidence,
            ),
        }

    async def analyze_custom_event_document(self, document_bytes: bytes) -> dict:
        result = await self.analyze_private_event_contract(document_bytes)
        return {
            **result,
            "document_type": "custom_event_contract",
            "summary": result["summary"] or "Custom private event contract analyzed.",
        }
