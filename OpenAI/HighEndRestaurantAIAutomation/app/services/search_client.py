import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from azure.search.documents import SearchClient

try:
    from azure.search.documents.models import VectorizedQuery
except ImportError:  # pragma: no cover
    VectorizedQuery = None

from app.core.auth import get_credential
from app.core.config import settings
from app.services.openai_client import AzureOpenAIClient

_PUBLISHED_DOCUMENTS: list[dict[str, Any]] = []
_QUERY_LOGS: list[dict[str, Any]] = []


class RestaurantSearchClient:
    def __init__(self) -> None:
        self._sample_menu = self._load_json("sample_menu.json")
        self._private_policy = self._load_text("docs/private_dining_policy.md")
        self._faq_source = self._load_text("nlp/faq_source.md")
        self._embedding_client = AzureOpenAIClient()
        self._mock_documents = self._build_mock_documents()

    def _client(self) -> SearchClient:
        return SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index,
            credential=get_credential(),
        )

    def _data_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "data"

    def _load_json(self, relative_path: str) -> dict:
        path = self._data_dir() / relative_path
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def _load_text(self, relative_path: str) -> str:
        path = self._data_dir() / relative_path
        if not path.exists():
            return ""
        return path.read_text()

    def _base_document(
        self,
        *,
        id: str,
        title: str,
        source: str,
        content: str,
        document_type: str,
        category: str,
        page: int = 1,
        section: str | None = None,
        menu_section: str | None = None,
        allergen_tags: list[str] | None = None,
        access_level: str = "public",
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        return {
            "id": id,
            "title": title,
            "source": source,
            "content": content,
            "document_type": document_type,
            "category": category,
            "language": "en",
            "access_level": access_level,
            "page": page,
            "page_number": page,
            "section": section,
            "chunk_id": id,
            "menu_section": menu_section,
            "allergen_tags": allergen_tags or [],
            "effective_date": None,
            "confidence": confidence,
            "metadata_json": "{}",
        }

    def _build_mock_documents(self) -> list[dict[str, Any]]:
        menus = self._sample_menu.get("menus", [])
        policies = self._sample_menu.get("policies", {})
        docs = [
            self._base_document(
                id="policy-1",
                title="Guest policy overview",
                source="sample_menu.json",
                content=(
                    f"Dress code: {policies.get('dress_code', '')} "
                    f"Cancellation: {policies.get('cancellation', '')} "
                    f"Allergens: {policies.get('allergens', '')}"
                ).strip(),
                document_type="policy",
                category="restaurant_policy",
                section="guest-policy",
                allergen_tags=["general-allergy"],
            ),
            self._base_document(
                id="private-dining-1",
                title="Private dining policy",
                source="private_dining_policy.md",
                content=self._private_policy,
                document_type="policy",
                category="private_dining",
                section="private-dining",
                menu_section="private-dining",
            ),
            self._base_document(
                id="faq-1",
                title="Restaurant FAQ",
                source="faq_source.md",
                content=self._faq_source,
                document_type="faq",
                category="faq",
                section="faq",
                allergen_tags=["general-allergy"],
            ),
        ]

        for index, item in enumerate(menus, start=1):
            tags = []
            serialized = json.dumps(item).lower()
            if "vegetarian" in serialized:
                tags.append("vegetarian")
            if "vegan" in serialized:
                tags.append("vegan")
            docs.append(
                self._base_document(
                    id=f"menu-{index}",
                    title=item.get("name", f"Menu item {index}"),
                    source="sample_menu.json",
                    content=" ".join(f"{key}: {value}" for key, value in item.items()),
                    document_type="menu",
                    category="menu",
                    section=item.get("name", "").lower(),
                    menu_section="tasting" if "tasting" in item.get("name", "").lower() else "pairings",
                    allergen_tags=tags,
                )
            )
        return docs

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token.strip(".,:;!?").lower() for token in text.split() if token.strip(".,:;!?")}

    def _all_documents(self) -> list[dict[str, Any]]:
        return self._mock_documents + deepcopy(_PUBLISHED_DOCUMENTS)

    def _apply_filters(
        self,
        documents: list[dict[str, Any]],
        *,
        document_type: str | None = None,
        category: str | None = None,
        language: str | None = None,
        access_level: str | None = None,
        menu_section: str | None = None,
        allergen_tag: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        filtered = documents
        applied_filters: dict[str, Any] = {}
        for key, value in {
            "document_type": document_type,
            "category": category,
            "language": language,
            "access_level": access_level,
            "menu_section": menu_section,
        }.items():
            if value:
                filtered = [doc for doc in filtered if doc.get(key) == value]
                applied_filters[key] = value
        if allergen_tag:
            filtered = [doc for doc in filtered if allergen_tag in doc.get("allergen_tags", [])]
            applied_filters["allergen_tag"] = allergen_tag
        return filtered, applied_filters

    def _score_document(self, query: str, document: dict[str, Any], query_type: str) -> float:
        query_tokens = self._tokenize(query)
        content_tokens = self._tokenize(document.get("content", ""))
        overlap = len(query_tokens & content_tokens)
        boost = 0.0
        lowered = query.lower()
        if document.get("title", "").lower() in lowered:
            boost += 0.5
        if document.get("section") and str(document["section"]).lower() in lowered:
            boost += 0.2
        if query_type in {"vector", "hybrid"}:
            boost += 0.3
        if query_type in {"semantic", "hybrid"} and any(word in lowered for word in ("policy", "minimum", "dress", "allergy", "deposit", "invoice")):
            boost += 0.2
        return round(overlap + boost, 3)

    @staticmethod
    def _metadata_json(result: dict[str, Any]) -> str:
        metadata_json = result.get("metadata_json", "{}")
        return metadata_json if isinstance(metadata_json, str) else json.dumps(metadata_json)

    def _result_to_citation(self, result: dict[str, Any]) -> dict[str, Any]:
        excerpt = result.get("content", "")[:220].strip()
        return {
            "source": result.get("source", "unknown"),
            "title": result.get("title", "Untitled"),
            "chunk_id": result.get("chunk_id", result.get("id", "unknown")),
            "page": result.get("page") or result.get("page_number"),
            "page_number": result.get("page") or result.get("page_number"),
            "section": result.get("section"),
            "confidence": float(result.get("confidence", 1.0)),
            "excerpt": excerpt,
        }

    def _to_context(self, results: list[dict[str, Any]]) -> str:
        return "\n\n".join(
            f"[{result['title']}] {result['content']}" for result in results if result.get("content")
        )

    @staticmethod
    def _build_facets(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        facets = {}
        for field in ("document_type", "category", "language"):
            counts = Counter(result.get(field, "unknown") for result in results)
            facets[field] = [{"value": key, "count": value} for key, value in counts.items()]
        return facets

    def _log_query(self, *, query: str, result_count: int, query_type: str, correlation_id: str, zero_result_fallback_used: bool) -> None:
        _QUERY_LOGS.append(
            {
                "query": query,
                "result_count": result_count,
                "query_type": query_type,
                "correlation_id": correlation_id,
                "zero_result_fallback_used": zero_result_fallback_used,
            }
        )

    def _mock_search(
        self,
        query: str,
        *,
        query_type: str = "hybrid",
        top_k: int = 5,
        document_type: str | None = None,
        category: str | None = None,
        language: str | None = None,
        access_level: str | None = None,
        menu_section: str | None = None,
        allergen_tag: str | None = None,
        include_facets: bool = True,
        use_zero_result_fallback: bool = True,
    ) -> dict[str, Any]:
        correlation_id = str(uuid4())
        filtered, applied_filters = self._apply_filters(
            self._all_documents(),
            document_type=document_type,
            category=category,
            language=language,
            access_level=access_level,
            menu_section=menu_section,
            allergen_tag=allergen_tag,
        )
        ranked = []
        for document in filtered:
            score = self._score_document(query, document, query_type)
            if score > 0:
                ranked.append(
                    {
                        **document,
                        "score": score,
                        "reranker_score": round(score + 0.17, 3) if query_type in {"semantic", "hybrid"} else None,
                    }
                )
        ranked.sort(key=lambda item: (item["score"], item.get("reranker_score") or 0), reverse=True)
        zero_result_fallback_used = False
        if not ranked and use_zero_result_fallback:
            fallback_document = filtered[0] if filtered else self._all_documents()[0]
            ranked = [
                {
                    **fallback_document,
                    "score": 0.25,
                    "reranker_score": 0.31 if query_type in {"semantic", "hybrid"} else None,
                }
            ]
            zero_result_fallback_used = True
        results = ranked[:top_k]
        citations = [self._result_to_citation(result) for result in results]
        sources = sorted({result["source"] for result in results})
        response = {
            "context": self._to_context(results),
            "sources": sources,
            "citations": citations,
            "results": results,
            "diagnostics": {
                "query_type": query_type,
                "applied_filters": applied_filters,
                "result_count": len(results),
                "used_vector_search": query_type in {"vector", "hybrid"},
                "used_semantic_ranker": query_type in {"semantic", "hybrid"},
                "embedding_dimensions": settings.azure_search_vector_dimensions,
                "zero_result_fallback_used": zero_result_fallback_used,
                "correlation_id": correlation_id,
            },
            "facets": self._build_facets(results) if include_facets else {"document_type": [], "category": [], "language": []},
        }
        self._log_query(
            query=query,
            result_count=len(results),
            query_type=query_type,
            correlation_id=correlation_id,
            zero_result_fallback_used=zero_result_fallback_used,
        )
        return response

    def _build_filter_expression(
        self,
        *,
        document_type: str | None = None,
        category: str | None = None,
        language: str | None = None,
        access_level: str | None = None,
        menu_section: str | None = None,
        allergen_tag: str | None = None,
    ) -> tuple[str | None, dict[str, Any]]:
        clauses: list[str] = []
        applied_filters: dict[str, Any] = {}
        for key, value in {
            "document_type": document_type,
            "category": category,
            "language": language,
            "access_level": access_level,
            "menu_section": menu_section,
        }.items():
            if value:
                clauses.append(f"{key} eq '{value}'")
                applied_filters[key] = value
        if allergen_tag:
            clauses.append(f"allergen_tags/any(tag: tag eq '{allergen_tag}')")
            applied_filters["allergen_tag"] = allergen_tag
        return (" and ".join(clauses) or None), applied_filters

    async def publish_documents(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        for document in documents:
            existing = next((index for index, item in enumerate(_PUBLISHED_DOCUMENTS) if item["id"] == document["id"]), None)
            normalized = {
                **document,
                "page_number": document.get("page") or document.get("page_number"),
                "metadata_json": self._metadata_json(document),
            }
            if existing is None:
                _PUBLISHED_DOCUMENTS.append(normalized)
            else:
                _PUBLISHED_DOCUMENTS[existing] = normalized
        if not settings.mock_mode and settings.azure_search_endpoint:
            client = self._client()
            client.upload_documents(documents=documents)
        return {"status": "published", "document_count": len(documents)}

    async def search_knowledge(
        self,
        query: str,
        *,
        query_type: str = "hybrid",
        top_k: int = 5,
        document_type: str | None = None,
        category: str | None = None,
        language: str | None = None,
        access_level: str | None = None,
        menu_section: str | None = None,
        allergen_tag: str | None = None,
        include_facets: bool = True,
        use_zero_result_fallback: bool = True,
        require_citations: bool = True,
    ) -> dict[str, Any]:
        if settings.mock_mode:
            result = self._mock_search(
                query,
                query_type=query_type,
                top_k=top_k,
                document_type=document_type,
                category=category,
                language=language,
                access_level=access_level,
                menu_section=menu_section,
                allergen_tag=allergen_tag,
                include_facets=include_facets,
                use_zero_result_fallback=use_zero_result_fallback,
            )
            if not require_citations:
                result["citations"] = []
            return result

        correlation_id = str(uuid4())
        client = self._client()
        filter_expression, applied_filters = self._build_filter_expression(
            document_type=document_type,
            category=category,
            language=language,
            access_level=access_level,
            menu_section=menu_section,
            allergen_tag=allergen_tag,
        )
        search_kwargs: dict[str, Any] = {
            "search_text": query if query_type != "vector" else "*",
            "top": top_k,
            "filter": filter_expression,
            "select": [
                "id",
                "title",
                "source",
                "content",
                "document_type",
                "category",
                "language",
                "access_level",
                "page",
                "section",
                "chunk_id",
                "menu_section",
                "allergen_tags",
                "confidence",
                "metadata_json",
            ],
        }
        if query_type in {"semantic", "hybrid"}:
            search_kwargs["query_type"] = "semantic"
            search_kwargs["semantic_configuration_name"] = settings.azure_search_semantic_config
        if query_type in {"vector", "hybrid"} and VectorizedQuery is not None:
            embedding = await self._embedding_client.embed(query)
            search_kwargs["vector_queries"] = [
                VectorizedQuery(vector=embedding, fields="content_vector", k_nearest_neighbors=top_k)
            ]
        results = []
        for result in client.search(**search_kwargs):
            result_dict = dict(result)
            result_dict["score"] = float(result.get("@search.score", 0.0))
            reranker_score = result.get("@search.reranker_score")
            result_dict["reranker_score"] = float(reranker_score) if reranker_score is not None else None
            result_dict["page_number"] = result_dict.get("page")
            results.append(result_dict)
        zero_result_fallback_used = False
        if not results and use_zero_result_fallback:
            zero_result_fallback_used = True
            fallback = self._mock_search(query, query_type="keyword", top_k=1)
            results = fallback["results"]
        citations = [self._result_to_citation(result) for result in results] if require_citations else []
        response = {
            "context": self._to_context(results),
            "sources": sorted({result.get("source", "unknown") for result in results}),
            "citations": citations,
            "results": results,
            "diagnostics": {
                "query_type": query_type,
                "applied_filters": applied_filters,
                "result_count": len(results),
                "used_vector_search": query_type in {"vector", "hybrid"},
                "used_semantic_ranker": query_type in {"semantic", "hybrid"},
                "embedding_dimensions": settings.azure_search_vector_dimensions,
                "zero_result_fallback_used": zero_result_fallback_used,
                "correlation_id": correlation_id,
            },
            "facets": self._build_facets(results) if include_facets else {"document_type": [], "category": [], "language": []},
        }
        self._log_query(
            query=query,
            result_count=len(results),
            query_type=query_type,
            correlation_id=correlation_id,
            zero_result_fallback_used=zero_result_fallback_used,
        )
        return response

    async def get_ingest_status(self) -> dict[str, Any]:
        if settings.mock_mode:
            all_docs = self._all_documents()
            return {
                "status": "ready",
                "index_name": settings.azure_search_index,
                "document_count": len(all_docs),
                "indexed_sources": sorted({doc["source"] for doc in all_docs}),
                "last_sync_hint": "Mock corpus is loaded from local sample content and in-memory ingestion jobs.",
            }

        client = self._client()
        return {
            "status": "ready",
            "index_name": settings.azure_search_index,
            "document_count": client.get_document_count(),
            "indexed_sources": [],
            "last_sync_hint": "Run scripts/ingest_documents.py after updating restaurant documents.",
        }

    async def get_query_logs(self) -> list[dict[str, Any]]:
        return deepcopy(_QUERY_LOGS[-25:])
