#!/usr/bin/env python3
# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""FastAPI web application demonstrating GraphRAG with access control."""

from pathlib import Path
from typing import Optional

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from graphrag.config.load_config import load_config
from graphrag.query.factory import get_local_search_engine_with_access_control
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)

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
    global config, text_units, entities, relationships, reports, project_root

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

    print(f"✓ Loaded {len(text_units)} text units")
    print(f"✓ Loaded {len(entities)} entities")
    print(f"✓ Loaded {len(relationships)} relationships")
    print(f"✓ Loaded {len(reports)} community reports")


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


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Execute a GraphRAG query with access control."""
    if request.user_role not in USERS:
        raise HTTPException(status_code=400, detail="Invalid user role")

    if not text_units or not entities:
        raise HTTPException(status_code=503, detail="Data not loaded")

    user_data = USERS[request.user_role]

    try:
        # Create search engine with access control
        search_engine = get_local_search_engine_with_access_control(
            config=config,
            reports=reports,
            text_units=text_units,
            entities=entities,
            relationships=relationships,
            user_id=user_data["id"],
            user_domains=user_data["domains"],
        )

        # Execute search
        result = await search_engine.asearch(request.query)

        # Get filtered counts
        stats = await get_stats(request.user_role)

        return QueryResponse(
            answer=result.response,
            context_data={
                "text_units": len(result.context_data.get("sources", [])),
                "entities": len(result.context_data.get("entities", [])),
                "relationships": len(result.context_data.get("relationships", [])),
            },
            user_info={
                "role": request.user_role,
                "name": user_data["name"],
                "domains": user_data["domains"],
            },
            access_stats=stats["accessible"],
        )

    except Exception as e:
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
        return bool(set(doc_domains) & set(user_data["domains"]))

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
        default=8000,
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
