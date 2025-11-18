#!/usr/bin/env python3
# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""FastAPI web application demonstrating GraphRAG with access control."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Enable INFO level logging to see debug messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from graphrag.config.load_config import load_config
from graphrag.config.models.vector_store_schema_config import VectorStoreSchemaConfig
from graphrag.query.factory import get_local_search_engine_with_access_control
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.vector_stores.base import BaseVectorStore, VectorStoreSearchResult
from graphrag.vector_stores.lancedb import LanceDBVectorStore


class MockVectorStore(BaseVectorStore):
    """Mock vector store that returns empty results."""

    def __init__(self):
        """Initialize without config."""
        # Skip BaseVectorStore.__init__ to avoid needing config
        self.db_connection = None
        self.document_collection = None
        self.query_filter = None
        self.kwargs = {}
        self.index_name = "mock"
        self.id_field = "id"
        self.text_field = "text"
        self.vector_field = "vector"
        self.attributes_field = "attributes"
        self.vector_size = 1536

    def connect(self, **kwargs):
        """No-op connect."""
        pass

    def load_documents(self, documents, overwrite=True):
        """No-op load."""
        pass

    def similarity_search_by_vector(self, query_embedding, k=10, **kwargs):
        """Return empty results."""
        return []

    def similarity_search_by_text(self, text, text_embedder=None, k=10, **kwargs):
        """Return empty results."""
        return []

    def filter_by_id(self, include_ids):
        """No-op filter."""
        return None

    def search_by_id(self, id):
        """No-op search."""
        return None


app = FastAPI(title="GraphRAG Access Control Demo", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to hold loaded data
config = None
text_units = None
entities = None
relationships = None
reports = None
project_root = None
description_embedding_store = None

# Mock user database
USERS = {
    "admin": {
        "id": "admin_123",
        "domains": ["technology", "finance", "engineering", "research"],
        "name": "Admin User",
    },
    "tech_user": {
        "id": "user_tech_456",
        "domains": ["technology", "research"],
        "name": "Tech User",
    },
    "finance_user": {
        "id": "user_finance_789",
        "domains": ["finance"],
        "name": "Finance User",
    },
    "guest": {
        "id": None,
        "domains": [],
        "name": "Guest User",
    },
}

# Custom system prompt with strict instructions
CUSTOM_SYSTEM_PROMPT = """
---Role---

You are a helpful assistant responding to questions based ONLY on the data provided in the tables below.

---Critical Instructions---

1. ONLY use information from the provided data tables. DO NOT use any general knowledge or make assumptions.
2. If the data tables are empty or do not contain relevant information, respond with: "No relevant information found in accessible documents."
3. Answer the question directly without preambles like "Based on the data..." or "According to the information...". Just state the facts.
4. Be concise and factual. Only include information that directly answers the question.
5. Every statement MUST cite its data source using this format:
   "Statement here [Data: <dataset> (record ids)]"

---Target response length and format---

{response_type}

---Data tables---

{context_data}

---Instructions---

Answer the user's question using ONLY the information in the data tables above. If no relevant data exists, say "No relevant information found in accessible documents." Do not add preambles or commentary - just provide the answer with proper citations.
"""


class QueryRequest(BaseModel):
    query: str
    user_role: str = "guest"
    max_results: int = 5


class QueryResponse(BaseModel):
    answer: str
    context_data: dict
    user_info: dict
    access_stats: dict


def load_graphrag_data(root_path: str):
    """Load GraphRAG indexed data and configuration."""
    global config, text_units, entities, relationships, reports, project_root, description_embedding_store

    project_root = root_path
    print(f"Loading GraphRAG data from {root_path}...")

    # Load configuration
    config = load_config(Path(root_path))

    # Load indexed data
    output_dir = Path(root_path) / "output"

    # Find artifacts
    artifacts_dirs = sorted(output_dir.glob("*/artifacts"))
    if not artifacts_dirs:
        artifacts_dir = output_dir
    else:
        artifacts_dir = artifacts_dirs[-1]

    print(f"Loading artifacts from: {artifacts_dir}")

    # Helper function to find parquet files
    def find_parquet(name_options):
        for name in name_options:
            path = artifacts_dir / name
            if path.exists():
                return path
        raise FileNotFoundError(f"Could not find any of {name_options} in {artifacts_dir}")

    text_units_df = pd.read_parquet(
        find_parquet(["text_units.parquet", "create_final_text_units.parquet"])
    )
    text_units = read_indexer_text_units(text_units_df)

    entities_df = pd.read_parquet(
        find_parquet(["entities.parquet", "create_final_entities.parquet"])
    )
    communities_df = pd.read_parquet(
        find_parquet(["communities.parquet", "create_final_communities.parquet"])
    )
    entities = read_indexer_entities(entities_df, communities_df, community_level=2)

    relationships_df = pd.read_parquet(
        find_parquet(["relationships.parquet", "create_final_relationships.parquet"])
    )
    relationships = read_indexer_relationships(relationships_df)

    reports_df = pd.read_parquet(
        find_parquet(["community_reports.parquet", "create_final_community_reports.parquet"])
    )
    reports = read_indexer_reports(
        reports_df, communities_df, community_level=2, config=config
    )

    # Try to load LanceDB vector store for entity descriptions
    lancedb_dir = output_dir / "lancedb"

    if lancedb_dir.exists():
        try:
            import lancedb
            print(f"📦 Loading LanceDB vector store from: {lancedb_dir}")

            # Connect to LanceDB and list available tables
            db = lancedb.connect(str(lancedb_dir))
            table_names = db.table_names()
            print(f"   Available tables: {table_names}")

            # Look for entity description table (try common names and patterns)
            table_name = None

            # First try exact matches
            for name in ["entity_description_embeddings", "description_embedding", "entity_descriptions", "default-entity-description"]:
                if name in table_names:
                    table_name = name
                    break

            # If not found, look for any table containing both "entity" and "description"
            if not table_name:
                for name in table_names:
                    if "entity" in name.lower() and "description" in name.lower():
                        table_name = name
                        print(f"   Found entity description table: {table_name}")
                        break

            # Fallback: use first table (not ideal)
            if not table_name and table_names:
                table_name = table_names[0]
                print(f"   ⚠️  Could not find entity description table, using: {table_name}")

            if table_name:
                # Get the table to check its schema
                table = db.open_table(table_name)
                schema = table.schema

                # Determine vector size from schema
                vector_size = 1536  # default
                if 'vector' in schema.names:
                    vector_field = schema.field('vector')
                    if hasattr(vector_field.type, 'list_size'):
                        vector_size = vector_field.type.list_size

                print(f"   Detected vector size: {vector_size}")

                # Create vector store schema config
                vector_store_config = VectorStoreSchemaConfig(
                    id_field="id",
                    vector_field="vector",
                    text_field="text",
                    attributes_field="attributes",
                    vector_size=vector_size,
                    index_name=table_name,
                )

                description_embedding_store = LanceDBVectorStore(
                    vector_store_schema_config=vector_store_config,
                )
                description_embedding_store.connect(db_uri=str(lancedb_dir))
                print(f"✓ LanceDB vector store loaded: {table_name}")
            else:
                print(f"⚠️  No tables found in LanceDB")
                print(f"⚠️  Using mock vector store (entity similarity disabled)")
                description_embedding_store = MockVectorStore()

        except Exception as e:
            print(f"⚠️  Failed to load LanceDB: {e}")
            print(f"⚠️  Falling back to mock vector store (entity similarity disabled)")
            description_embedding_store = MockVectorStore()
    else:
        print(f"⚠️  LanceDB directory not found at {lancedb_dir}")
        print(f"⚠️  Using mock vector store (entity description similarity disabled)")
        description_embedding_store = MockVectorStore()

    print(f"✓ Loaded {len(text_units)} text units")
    print(f"✓ Loaded {len(entities)} entities")
    print(f"✓ Loaded {len(relationships)} relationships")
    print(f"✓ Loaded {len(reports)} community reports")

    # Debug: Show access control metadata in loaded data
    print(f"\n{'='*60}")
    print(f"🔍 ACCESS CONTROL METADATA CHECK")
    print(f"{'='*60}")

    if text_units:
        print(f"\n📄 Sample Text Units (first 3):")
        for i, tu in enumerate(text_units[:3]):
            attrs = tu.attributes if hasattr(tu, 'attributes') else {}
            print(f"\n  [{i+1}] ID: {tu.id}")
            print(f"      Has attributes: {bool(attrs)}")
            if attrs:
                print(f"      Access type: {attrs.get('access_type', 'MISSING')}")
                print(f"      Owner ID: {attrs.get('owner_id', 'MISSING')}")
                print(f"      Access domains: {attrs.get('access_domains', 'MISSING')}")
                print(f"      Source: {attrs.get('source', 'MISSING')}")
            print(f"      Text preview: {tu.text[:80]}...")

    if entities:
        print(f"\n🏷️  Sample Entities (first 3):")
        for i, entity in enumerate(entities[:3]):
            attrs = entity.attributes if hasattr(entity, 'attributes') else {}
            print(f"\n  [{i+1}] {entity.title} ({entity.type})")
            print(f"      Has attributes: {bool(attrs)}")
            print(f"      Has text_unit_ids: {hasattr(entity, 'text_unit_ids')}")
            if hasattr(entity, 'text_unit_ids'):
                print(f"      Source text units: {entity.text_unit_ids}")

    print(f"\n{'='*60}\n")


@app.get("/")
async def home():
    """Serve the web UI."""
    static_dir = Path(__file__).parent / "static"
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "data_loaded": text_units is not None,
        "text_units": len(text_units) if text_units else 0,
        "entities": len(entities) if entities else 0,
    }


@app.get("/api/users")
async def get_users():
    """Get available user roles."""
    return {
        "users": [
            {"role": role, "name": data["name"], "domains": data["domains"]}
            for role, data in USERS.items()
        ]
    }


@app.get("/api/stats")
async def get_stats(user_role: str = Query(default="guest")):
    """Get access control statistics for a user."""
    if user_role not in USERS:
        raise HTTPException(status_code=400, detail="Invalid user role")

    user_data = USERS[user_role]

    # Count accessible items
    accessible_text_units = 0
    accessible_entities = 0
    accessible_relationships = 0

    if text_units:
        for tu in text_units:
            if _can_access(tu.attributes, user_data):
                accessible_text_units += 1

    if entities:
        for entity in entities:
            if _can_access(getattr(entity, "attributes", None), user_data):
                accessible_entities += 1

    if relationships:
        for rel in relationships:
            if _can_access(getattr(rel, "attributes", None), user_data):
                accessible_relationships += 1

    return {
        "user_role": user_role,
        "user_name": user_data["name"],
        "domains": user_data["domains"],
        "accessible": {
            "text_units": accessible_text_units,
            "entities": accessible_entities,
            "relationships": accessible_relationships,
        },
        "total": {
            "text_units": len(text_units) if text_units else 0,
            "entities": len(entities) if entities else 0,
            "relationships": len(relationships) if relationships else 0,
        },
    }


@app.post("/api/query")
async def query(request: QueryRequest):
    """Execute a GraphRAG query with access control."""
    if request.user_role not in USERS:
        raise HTTPException(status_code=400, detail="Invalid user role")

    if not text_units or not entities:
        raise HTTPException(status_code=503, detail="Data not loaded")

    user_data = USERS[request.user_role]

    try:
        print(f"\n{'='*80}")
        print(f"🔍 QUERY DEBUG - User: {request.user_role} | Query: {request.query}")
        print(f"{'='*80}")

        # Debug: Show total data before filtering
        print(f"\n📊 TOTAL DATA (before filtering):")
        print(f"  - Text units: {len(text_units)}")
        print(f"  - Entities: {len(entities)}")
        print(f"  - Relationships: {len(relationships)}")

        # Debug: Manually filter to see what access control does
        from graphrag.query.filters.access_control import AccessControlFilter

        access_filter = AccessControlFilter(
            user_id=user_data["id"],
            user_domains=user_data["domains"]
        )

        print(f"\n🔐 ACCESS CONTROL:")
        print(f"  - User ID: {user_data['id']}")
        print(f"  - User domains: {user_data['domains']}")

        # Filter data manually to see results
        filtered_text_units, filtered_entities, filtered_relationships, _ = (
            access_filter.filter_context_data(
                text_units=text_units,
                entities=entities,
                relationships=relationships,
                covariates=None,  # No covariates in this example
            )
        )

        print(f"\n✅ FILTERED DATA:")
        print(f"  - Text units: {len(filtered_text_units)}")
        print(f"  - Entities: {len(filtered_entities)}")
        print(f"  - Relationships: {len(filtered_relationships)}")

        # Show sample of filtered text units
        if filtered_text_units:
            print(f"\n📄 SAMPLE TEXT UNITS (first 2):")
            for i, tu in enumerate(filtered_text_units[:2]):
                print(f"  [{i+1}] ID: {tu.id}")
                print(f"      Access: {tu.attributes.get('access_type', 'unknown')}")
                print(f"      Domains: {tu.attributes.get('access_domains', [])}")
                print(f"      Text: {tu.text[:100]}...")
        else:
            print(f"\n⚠️  NO TEXT UNITS ACCESSIBLE TO THIS USER!")

        # 🚨 CRITICAL DIAGNOSTIC: Check for entities from research_reports
        print(f"\n🔬 ENTITIES FROM RESEARCH_REPORTS:")
        research_entities = []
        for entity in filtered_entities:
            if hasattr(entity, 'text_unit_ids') and entity.text_unit_ids:
                for tu_id in entity.text_unit_ids:
                    source_tu = next((tu for tu in text_units if tu.id == tu_id), None)
                    if source_tu and hasattr(source_tu, 'attributes'):
                        if source_tu.attributes.get('source') == 'research_reports':
                            research_entities.append((entity, source_tu))
                            break

        if research_entities:
            print(f"  ✅ Found {len(research_entities)} entities from research_reports:")
            for i, (entity, source_tu) in enumerate(research_entities[:5]):
                print(f"  [{i+1}] {entity.title} (type: {entity.type})")
                print(f"      Description: {entity.description if entity.description else 'NO DESCRIPTION'}...")
                print(f"      Text unit preview: {source_tu.text[:100]}...")
        else:
            print(f"  ⚠️  NO ENTITIES FOUND FROM RESEARCH_REPORTS!")
            print(f"  This is why doc006 never appears in search results!")
            print(f"\n  Possible reasons:")
            print(f"    1. Indexing didn't extract entities from doc006")
            print(f"    2. Entity extraction failed on that document")
            print(f"    3. The source document doesn't exist or wasn't indexed")

            # Check if research_reports text units exist at all
            research_tus = [tu for tu in filtered_text_units if tu.attributes.get('source') == 'research_reports']
            if research_tus:
                print(f"\n  📄 But we DO have {len(research_tus)} text units from research_reports!")
                print(f"  This means: Entities were NOT extracted from those text units")
                print(f"\n  Sample text unit from research_reports:")
                sample_tu = research_tus[0]
                print(f"    ID: {sample_tu.id}")
                print(f"    Text: {sample_tu.text[:200]}...")
            else:
                print(f"\n  Also NO text units from research_reports accessible to this user")

        # Show sample of filtered entities
        if filtered_entities:
            print(f"\n🏷️  ALL ACCESSIBLE ENTITIES ({len(filtered_entities)} total):")
            print(f"  Showing all entity titles and their sources:")
            entity_sources = {}
            for entity in filtered_entities:
                sources = set()
                if hasattr(entity, 'text_unit_ids') and entity.text_unit_ids:
                    for tu_id in entity.text_unit_ids:
                        source_tu = next((tu for tu in text_units if tu.id == tu_id), None)
                        if source_tu and hasattr(source_tu, 'attributes'):
                            sources.add(source_tu.attributes.get('source', 'unknown'))
                entity_sources[entity.title] = sources

            for title, sources in list(entity_sources.items())[:15]:
                print(f"    - {title}: from {', '.join(sources)}")

            if len(entity_sources) > 15:
                print(f"    ... and {len(entity_sources) - 15} more entities")

        print(f"\n🔧 Creating search engine with filtered data...")

        # Create search engine with access control and custom system prompt
        search_engine = get_local_search_engine_with_access_control(
            config=config,
            reports=reports,
            text_units=text_units,
            entities=entities,
            relationships=relationships,
            covariates={},
            response_type="Multiple Paragraphs",
            description_embedding_store=description_embedding_store,
            user_id=user_data["id"],
            user_domains=user_data["domains"],
            system_prompt=CUSTOM_SYSTEM_PROMPT,
        )

        print(f"\n🚀 Executing search...")

        # Execute search
        result = await search_engine.search(request.query)

        print(f"\n✨ Query completed!")
        print(f"  - Response length: {len(result.response)} chars")
        print(f"  - LLM calls: {getattr(result, 'llm_calls', 'N/A')}")
        print(f"  - Prompt tokens: {getattr(result, 'prompt_tokens', 'N/A')}")

        # Debug: Show which text units were actually used in context
        print(f"\n📄 TEXT UNITS USED IN CONTEXT:")
        if hasattr(result, 'context_data') and isinstance(result.context_data, dict):
            if 'sources' in result.context_data:
                sources_df = result.context_data['sources']
                if len(sources_df) > 0:
                    print(f"  Found {len(sources_df)} text units in context:")
                    for idx, row in sources_df.iterrows():
                        # Try to find the original text unit to show its attributes
                        tu_id = row.get('id', 'unknown')
                        matching_tu = next((tu for tu in text_units if tu.id == tu_id), None)
                        if matching_tu and hasattr(matching_tu, 'attributes'):
                            attrs = matching_tu.attributes
                            print(f"    [{idx+1}] ID: {tu_id[:40]}...")
                            print(f"        Access: {attrs.get('access_type', 'unknown')}")
                            print(f"        Domains: {attrs.get('access_domains', [])}")
                            print(f"        Source: {attrs.get('source', 'unknown')}")
                            print(f"        Text preview: {matching_tu.text[:100]}...")
                        else:
                            print(f"    [{idx+1}] ID: {tu_id[:40]}... (attributes not found)")
                else:
                    print(f"  ⚠️  Sources dataframe is empty!")
            else:
                print(f"  ⚠️  No 'sources' key in context_data")
        else:
            print(f"  ⚠️  No context_data or not a dict")

        # Debug: Inspect the result object
        print(f"\n🔬 RESULT OBJECT INSPECTION:")
        print(f"  - Has context_data: {hasattr(result, 'context_data')}")
        print(f"  - Has context_text: {hasattr(result, 'context_text')}")
        print(f"  - Has context_records: {hasattr(result, 'context_records')}")

        if hasattr(result, 'context_data') and result.context_data:
            print(f"  - context_data type: {type(result.context_data)}")
            print(f"  - context_data keys: {result.context_data.keys() if isinstance(result.context_data, dict) else 'not a dict'}")
            if isinstance(result.context_data, dict):
                for key, value in result.context_data.items():
                    if isinstance(value, list):
                        print(f"    - {key}: {len(value)} items")
                    else:
                        print(f"    - {key}: {type(value)}")

        if hasattr(result, 'context_text'):
            print(f"  - context_text length: {len(result.context_text) if result.context_text else 0} chars")

        if hasattr(result, 'context_records') and result.context_records:
            print(f"  - context_records: {len(result.context_records)} items")

        # Get filtered counts
        stats = await get_stats(request.user_role)

        # Build response - try to extract actual context data
        context_data_info = {"text_units": 0, "entities": 0, "relationships": 0}

        if hasattr(result, 'context_data') and result.context_data:
            if isinstance(result.context_data, dict):
                # Try common key names
                context_data_info["text_units"] = len(result.context_data.get("sources", result.context_data.get("text_units", [])))
                context_data_info["entities"] = len(result.context_data.get("entities", []))
                context_data_info["relationships"] = len(result.context_data.get("relationships", result.context_data.get("relations", [])))

        if hasattr(result, 'context_records') and result.context_records:
            # Alternative: use context_records
            context_data_info["records_used"] = len(result.context_records)

        print(f"\n📦 CONTEXT DATA EXTRACTED:")
        print(f"  {context_data_info}")
        print(f"{'='*80}\n")

        response_data = {
            "answer": result.response,
            "context_data": context_data_info,
            "user_info": {
                "role": request.user_role,
                "name": user_data["name"],
                "domains": user_data["domains"],
            },
            "access_stats": stats["accessible"],
            "debug_info": {
                "filtered_text_units": len(filtered_text_units),
                "filtered_entities": len(filtered_entities),
                "filtered_relationships": len(filtered_relationships),
                "has_context_data": hasattr(result, 'context_data'),
                "context_text_length": len(result.context_text) if hasattr(result, 'context_text') and result.context_text else 0,
            }
        }

        # Add optional fields if they exist
        if hasattr(result, "completion_time"):
            response_data["completion_time"] = result.completion_time
        if hasattr(result, "llm_calls"):
            response_data["llm_calls"] = result.llm_calls
        if hasattr(result, "prompt_tokens"):
            response_data["prompt_tokens"] = result.prompt_tokens

        return response_data

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in query endpoint:\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/docs")
async def get_docs(user_role: str = Query(default="guest")):
    """Get list of accessible documents for a user."""
    if user_role not in USERS:
        raise HTTPException(status_code=400, detail="Invalid user role")

    user_data = USERS[user_role]
    accessible_docs = []

    if text_units:
        for tu in text_units[:20]:  # Limit to first 20 for performance
            if _can_access(tu.attributes, user_data):
                accessible_docs.append({
                    "id": tu.id,
                    "text": tu.text[:200] + "..." if len(tu.text) > 200 else tu.text,
                    "access_type": tu.attributes.get("access_type", "unknown"),
                    "domains": tu.attributes.get("access_domains", []),
                })

    return {"documents": accessible_docs, "count": len(accessible_docs)}


def _can_access(attributes: Optional[dict], user_data: dict) -> bool:
    """Check if user can access an item based on attributes."""
    if not attributes:
        return True

    access_type = attributes.get("access_type", "public")

    if access_type == "public":
        return True

    if access_type == "private":
        owner_id = attributes.get("owner_id")
        return str(owner_id) == user_data["id"] if owner_id and user_data["id"] else False

    if access_type == "domain":
        doc_domains = attributes.get("access_domains", [])
        if isinstance(doc_domains, str):
            doc_domains = [d.strip() for d in doc_domains.split(",")]

        # Convert to set, handling numpy arrays
        try:
            if doc_domains is not None and len(doc_domains) > 0:
                doc_domains_set = set(doc_domains)
            else:
                doc_domains_set = set()
        except (TypeError, ValueError):
            doc_domains_set = set()

        return bool(set(user_data["domains"]) & doc_domains_set)

    return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="GraphRAG Access Control FastAPI Demo")
    parser.add_argument(
        "--project-root",
        type=str,
        required=True,
        help="Path to GraphRAG project root directory",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8045,
        help="Port to bind to",
    )

    args = parser.parse_args()

    # Load data
    load_graphrag_data(args.project_root)

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    print(f"\n{'='*60}")
    print(f"🚀 GraphRAG Access Control API")
    print(f"{'='*60}")
    print(f"📊 API Docs: http://{args.host}:{args.port}/docs")
    print(f"🌐 Web UI:   http://{args.host}:{args.port}/")
    print(f"💚 Health:   http://{args.host}:{args.port}/health")
    print(f"{'='*60}\n")

    # Run server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
