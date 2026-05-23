"""
search_client.py — Phase 4: Azure AI Search retrieval layer
============================================================
AI-102 Skills:
  - Vector search (dense retrieval using embeddings)
  - Hybrid search (keyword + vector) with Reciprocal Rank Fusion
  - Semantic ranker (re-ranks top-K results using language model)
  - Index schema management
  - AI-102 Cost Note: Semantic ranker adds per-query charge — only use when precision matters

Restaurant Use Cases:
  - Guest asks: "What wines pair with our wagyu beef?" → hybrid + semantic search
  - Staff query: "What is our allergen policy for tree nuts?" → keyword search on policy docs
  - Sommelier assistant: "Find all wines under £80 from Burgundy" → filtered vector search
"""

import logging
from typing import Optional

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)
from azure.search.documents.models import VectorizedQuery, QueryType, QueryCaptionType, QueryAnswerType
from openai import AzureOpenAI

from src.config import RestaurantAIConfig, get_credential
from src.monitoring.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


RESTAURANT_INDEX_SCHEMA = {
    "index_name": "restaurant-knowledge",
    "embedding_dimensions": 3072,  # text-embedding-3-large produces 3072-dim vectors
}


class RestaurantSearchClient:
    """
    Wraps Azure AI Search for hybrid + semantic retrieval.
    Used as the retrieval layer in the RAG pattern.
    """

    def __init__(self, config: RestaurantAIConfig):
        self.config = config
        credential = get_credential()

        self.search_client = SearchClient(
            endpoint=config.search_endpoint,
            index_name=config.search_index_name,
            credential=credential,
        )
        self.index_client = SearchIndexClient(
            endpoint=config.search_endpoint,
            credential=credential,
        )
        self.openai_client = AzureOpenAI(
            azure_endpoint=config.openai_endpoint,
            azure_ad_token_provider=lambda: credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version=config.openai_api_version,
        )

    # ── Index Management ──────────────────────────────────────────────────────

    def create_or_update_index(self) -> None:
        """
        Create or update the restaurant knowledge index.
        AI-102: Index schema defines searchable, filterable, sortable, and vector fields.
        """
        dims = RESTAURANT_INDEX_SCHEMA["embedding_dimensions"]

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SearchableField(name="content", type=SearchFieldDataType.String,
                           analyzer_name="en.microsoft"),
            SearchableField(name="document_name", type=SearchFieldDataType.String,
                           filterable=True, sortable=True),
            SimpleField(name="document_type", type=SearchFieldDataType.String,
                       filterable=True, facetable=True),
            SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            SimpleField(name="page_count", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="blob_url", type=SearchFieldDataType.String),
            SearchableField(name="metadata_json", type=SearchFieldDataType.String),
            # Vector field for semantic similarity search
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=dims,
                vector_search_profile_name="restaurant-vector-profile",
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="restaurant-hnsw")],
            profiles=[VectorSearchProfile(
                name="restaurant-vector-profile",
                algorithm_configuration_name="restaurant-hnsw",
            )],
        )

        # AI-102: Semantic configuration identifies which fields the ranker uses
        semantic_config = SemanticConfiguration(
            name="restaurant-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")],
                keywords_fields=[SemanticField(field_name="document_type")],
            ),
        )

        index = SearchIndex(
            name=self.config.search_index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=SemanticSearch(configurations=[semantic_config]),
        )

        self.index_client.create_or_update_index(index)
        logger.info(f"Index '{self.config.search_index_name}' created/updated successfully.")

    # ── Search Methods ────────────────────────────────────────────────────────

    def hybrid_semantic_search(
        self,
        query: str,
        top_k: int = 5,
        document_type_filter: Optional[str] = None,
        use_semantic_ranker: bool = True,
    ) -> list[dict]:
        """
        Hybrid search: keyword BM25 + vector similarity, fused via RRF.
        Optionally applies semantic ranker for higher precision.

        AI-102: Hybrid search is the recommended pattern for RAG retrieval.
        Semantic ranker improves precision but adds per-query cost.

        Restaurant example:
          query = "Burgundy Pinot Noir under 80 pounds"
          filter = "document_type eq 'wine_list'"
        """
        with tracer.start_as_current_span("search_retrieval") as span:
            span.set_attribute("query", query[:100])
            span.set_attribute("semantic_ranker", use_semantic_ranker)

            # Generate query embedding for vector component
            query_embedding = self._embed_query(query)

            vector_query = VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=top_k * 2,  # Over-retrieve; RRF will re-rank
                fields="content_vector",
            )

            filter_expr = None
            if document_type_filter:
                filter_expr = f"document_type eq '{document_type_filter}'"

            search_kwargs = {
                "search_text": query,
                "vector_queries": [vector_query],
                "filter": filter_expr,
                "top": top_k,
                "select": ["id", "content", "document_name", "document_type",
                           "chunk_index", "blob_url", "metadata_json"],
            }

            if use_semantic_ranker:
                # AI-102: query_type=SEMANTIC + semantic_configuration_name enables re-ranking
                search_kwargs.update({
                    "query_type": QueryType.SEMANTIC,
                    "semantic_configuration_name": "restaurant-semantic-config",
                    "query_caption": QueryCaptionType.EXTRACTIVE,
                    "query_answer": QueryAnswerType.EXTRACTIVE,
                })

            results = self.search_client.search(**search_kwargs)

            retrieved = []
            for r in results:
                doc = {
                    "id": r["id"],
                    "content": r["content"],
                    "document_name": r["document_name"],
                    "document_type": r["document_type"],
                    "blob_url": r.get("blob_url", ""),
                    "score": r["@search.score"],
                }
                # Semantic captions are extractive highlights from the passage
                if hasattr(r, "@search.captions") and r.get("@search.captions"):
                    doc["caption"] = r["@search.captions"][0].text
                retrieved.append(doc)

            span.set_attribute("results.count", len(retrieved))
            logger.info(f"Retrieved {len(retrieved)} results for query: '{query[:60]}'")
            return retrieved

    def _embed_query(self, text: str) -> list[float]:
        """Generate embedding for the search query using the same model as ingestion."""
        response = self.openai_client.embeddings.create(
            input=text,
            model=self.config.openai_embedding_deployment,
        )
        return response.data[0].embedding
