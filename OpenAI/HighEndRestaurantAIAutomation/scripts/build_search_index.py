import json
from pathlib import Path

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from app.core.auth import get_credential
from app.core.config import settings


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "infra" / "bicep" / "search-index.json"


def build_schema() -> dict:
    return {
        "name": settings.azure_search_index,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True, "sortable": True},
            {"name": "chunk_id", "type": "Edm.String", "filterable": True, "sortable": True},
            {"name": "title", "type": "Edm.String", "searchable": True},
            {"name": "source", "type": "Edm.String", "filterable": True, "sortable": True},
            {"name": "document_type", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "menu_section", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "page_number", "type": "Edm.Int32", "filterable": True, "sortable": True},
            {"name": "allergen_tags", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
            {"name": "content", "type": "Edm.String", "searchable": True},
            {
                "name": "content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "dimensions": settings.azure_search_vector_dimensions,
                "vectorSearchProfile": "restaurant-vector-profile",
            },
            {"name": "metadata_json", "type": "Edm.String", "searchable": False},
        ],
        "semantic": {
            "configurations": [
                {
                    "name": settings.azure_search_semantic_config,
                    "prioritizedFields": {
                        "titleField": {"fieldName": "title"},
                        "prioritizedContentFields": [{"fieldName": "content"}],
                    },
                }
            ]
        },
        "vectorSearch": {
            "algorithms": [{"name": "restaurant-hnsw", "kind": "hnsw"}],
            "profiles": [{"name": "restaurant-vector-profile", "algorithm": "restaurant-hnsw"}],
        },
    }


def write_schema_file(schema: dict) -> None:
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2))


def create_or_update_index(schema: dict) -> None:
    client = SearchIndexClient(endpoint=settings.azure_search_endpoint, credential=get_credential())
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True, sortable=True),
        SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="document_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="menu_section", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SearchField(
            name="allergen_tags",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            facetable=True,
        ),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=settings.azure_search_vector_dimensions,
            vector_search_profile_name="restaurant-vector-profile",
        ),
        SimpleField(name="metadata_json", type=SearchFieldDataType.String),
    ]
    index = SearchIndex(
        name=schema["name"],
        fields=fields,
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name=settings.azure_search_semantic_config,
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="title"),
                        prioritized_content_fields=[SemanticField(field_name="content")],
                    ),
                )
            ]
        ),
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="restaurant-hnsw")],
            profiles=[VectorSearchProfile(name="restaurant-vector-profile", algorithm_configuration_name="restaurant-hnsw")],
        ),
    )
    client.create_or_update_index(index)


if __name__ == "__main__":
    schema = build_schema()
    write_schema_file(schema)
    if settings.azure_search_endpoint and not settings.mock_mode:
        create_or_update_index(schema)
        print(f"Created or updated Azure AI Search index {settings.azure_search_index}")
    else:
        print(f"Wrote schema to {SCHEMA_PATH}")
