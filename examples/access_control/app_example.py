#!/usr/bin/env python3
# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Example Flask web application demonstrating GraphRAG with access control."""

from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from graphrag.config.load_config import load_config
from graphrag.query.factory import get_local_search_engine_with_access_control
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.utils.storage import PipelineStorage

app = Flask(__name__, static_folder='static')

# Global variables to hold loaded data
config = None
text_units = None
entities = None
relationships = None
reports = None

# Mock user database (in production, use real authentication)
USERS = {
    "finance_user": {
        "id": "user_finance_123",
        "domains": ["finance", "legal"],
        "api_key": "finance_key_123",
    },
    "engineering_user": {
        "id": "user_eng_456",
        "domains": ["engineering", "product"],
        "api_key": "eng_key_456",
    },
    "marketing_user": {
        "id": "user_marketing_789",
        "domains": ["marketing", "sales"],
        "api_key": "marketing_key_789",
    },
    "public_user": {
        "id": None,  # Public access, no user ID
        "domains": [],
        "api_key": "public_key_000",
    },
}


def load_graphrag_data(project_root: str):
    """Load GraphRAG indexed data and configuration."""
    global config, text_units, entities, relationships, reports

    # Load configuration (load_config expects root directory, not settings.yaml path)
    config = load_config(Path(project_root))

    # Load indexed data
    output_dir = Path(project_root) / "output"

    # Find the latest artifacts directory (GraphRAG creates timestamped subdirs)
    artifacts_dirs = sorted(output_dir.glob("*/artifacts"))
    if not artifacts_dirs:
        # Fallback: try direct output dir (newer GraphRAG versions)
        artifacts_dir = output_dir
    else:
        artifacts_dir = artifacts_dirs[-1]  # Get the latest

    print(f"Loading artifacts from: {artifacts_dir}")

    # Helper function to find parquet files with different naming conventions
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

    print(f"Loaded {len(text_units)} text units")
    print(f"Loaded {len(entities)} entities")
    print(f"Loaded {len(relationships)} relationships")
    print(f"Loaded {len(reports)} community reports")


def authenticate_user(api_key: str) -> dict | None:
    """Authenticate user based on API key."""
    for username, user_data in USERS.items():
        if user_data["api_key"] == api_key:
            return {"username": username, **user_data}
    return None


@app.route("/api/query", methods=["POST"])
async def query():
    """Query endpoint with access control.

    Request body:
    {
        "query": "What were the Q4 financial results?",
        "api_key": "finance_key_123",
        "response_type": "multiple paragraphs"
    }

    Response:
    {
        "response": "The Q4 financial results...",
        "context_data": [...],
        "user_access": {
            "user_id": "user_finance_123",
            "domains": ["finance", "legal"]
        },
        "stats": {
            "accessible_text_units": 150,
            "accessible_entities": 45,
            "completion_time": 2.5
        }
    }
    """
    try:
        # Parse request
        data = request.get_json()
        query_text = data.get("query")
        api_key = data.get("api_key")
        response_type = data.get("response_type", "multiple paragraphs")

        if not query_text:
            return jsonify({"error": "Query is required"}), 400

        if not api_key:
            return jsonify({"error": "API key is required"}), 401

        # Authenticate user
        user = authenticate_user(api_key)
        if not user:
            return jsonify({"error": "Invalid API key"}), 401

        # Create search engine with user's access control
        search_engine = get_local_search_engine_with_access_control(
            config=config,
            reports=reports,
            text_units=text_units,
            entities=entities,
            relationships=relationships,
            covariates={},
            response_type=response_type,
            description_embedding_store=None,  # Configure if using vector search
            user_id=user["id"],
            user_domains=user["domains"],
        )

        # Perform search
        result = await search_engine.search(query_text)

        # Count accessible data for stats
        from graphrag.query.filters.access_control import AccessControlFilter

        access_filter = AccessControlFilter(
            user_id=user["id"], user_domains=user["domains"]
        )
        accessible_text_units = access_filter.filter_text_units(text_units)
        accessible_tu_ids = {tu.id for tu in accessible_text_units}
        accessible_entities = access_filter.filter_entities_by_source(
            entities, accessible_tu_ids
        )

        # Build response
        response_data = {
            "response": result.response,
            "context_text": result.context_text,
            "user_access": {
                "username": user["username"],
                "user_id": user["id"],
                "domains": user["domains"],
            },
            "stats": {
                "accessible_text_units": len(accessible_text_units),
                "accessible_entities": len(accessible_entities),
                "total_text_units": len(text_units),
                "total_entities": len(entities),
                "completion_time": result.completion_time,
                "llm_calls": result.llm_calls,
                "prompt_tokens": result.prompt_tokens,
                "output_tokens": result.output_tokens,
            },
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users", methods=["GET"])
def list_users():
    """List available test users and their access levels."""
    user_list = []
    for username, user_data in USERS.items():
        user_list.append({
            "username": username,
            "domains": user_data["domains"],
            "api_key": user_data["api_key"],
        })
    return jsonify({"users": user_list})


@app.route("/api/stats", methods=["GET"])
def stats():
    """Get statistics about indexed data."""
    api_key = request.args.get("api_key")

    if not api_key:
        # Return public stats without access control
        return jsonify({
            "total_text_units": len(text_units),
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "total_reports": len(reports),
        })

    # Authenticate and show user-specific stats
    user = authenticate_user(api_key)
    if not user:
        return jsonify({"error": "Invalid API key"}), 401

    from graphrag.query.filters.access_control import AccessControlFilter

    access_filter = AccessControlFilter(user_id=user["id"], user_domains=user["domains"])
    accessible_text_units = access_filter.filter_text_units(text_units)
    accessible_tu_ids = {tu.id for tu in accessible_text_units}
    accessible_entities = access_filter.filter_entities_by_source(
        entities, accessible_tu_ids
    )
    accessible_relationships = access_filter.filter_relationships_by_source(
        relationships, accessible_tu_ids
    )

    return jsonify({
        "user": {
            "username": user["username"],
            "domains": user["domains"],
        },
        "accessible": {
            "text_units": len(accessible_text_units),
            "entities": len(accessible_entities),
            "relationships": len(accessible_relationships),
        },
        "total": {
            "text_units": len(text_units),
            "entities": len(entities),
            "relationships": len(relationships),
            "reports": len(reports),
        },
        "access_percentage": {
            "text_units": round(
                len(accessible_text_units) / len(text_units) * 100, 2
            ),
            "entities": round(len(accessible_entities) / len(entities) * 100, 2),
        },
    })


@app.route("/", methods=["GET"])
def home():
    """Serve the web UI."""
    return send_from_directory('static', 'index.html')


@app.route("/api/docs", methods=["GET"])
def api_docs():
    """API documentation."""
    return """
    <html>
    <head><title>GraphRAG Access Control API</title></head>
    <body>
        <h1>GraphRAG Access Control API</h1>
        <h2>Endpoints</h2>
        <ul>
            <li><strong>GET /</strong> - Web UI</li>
            <li><strong>POST /api/query</strong> - Query with access control</li>
            <li><strong>GET /api/users</strong> - List test users</li>
            <li><strong>GET /api/stats</strong> - Get data statistics</li>
        </ul>

        <h2>Example Query</h2>
        <pre>
curl -X POST http://localhost:5000/api/query \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "What were the Q4 financial results?",
    "api_key": "finance_key_123",
    "response_type": "multiple paragraphs"
  }'
        </pre>

        <h2>Test Users</h2>
        <pre>
Finance User:    api_key=finance_key_123    (domains: finance, legal)
Engineering:     api_key=eng_key_456        (domains: engineering, product)
Marketing:       api_key=marketing_key_789  (domains: marketing, sales)
Public:          api_key=public_key_000     (no restricted access)
        </pre>
    </body>
    </html>
    """


def main():
    """Run the Flask application."""
    import argparse

    parser = argparse.ArgumentParser(
        description="GraphRAG Access Control API Server"
    )
    parser.add_argument(
        "--project-root",
        required=True,
        help="Path to GraphRAG project root directory",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")

    args = parser.parse_args()

    # Load GraphRAG data
    print(f"Loading GraphRAG data from {args.project_root}...")
    load_graphrag_data(args.project_root)
    print("Data loaded successfully!")

    # Run Flask app
    print(f"Starting server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
