#!/usr/bin/env python3
# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Utility to export documents from MongoDB with access control metadata for GraphRAG indexing."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from bson import ObjectId
    from pymongo import MongoClient
except ImportError as e:
    msg = "pymongo is required for MongoDB export. Install it with: pip install pymongo"
    raise ImportError(msg) from e


def convert_to_json_serializable(obj: Any) -> Any:
    """Convert MongoDB objects to JSON-serializable format.

    Args:
        obj: Object to convert (datetime, ObjectId, dict, list, etc.)

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    else:
        return obj


def export_documents_to_json(
    mongodb_uri: str,
    database_name: str,
    collection_name: str,
    output_file: str | Path,
    query_filter: dict[str, Any] | None = None,
):
    """Export documents from MongoDB to JSON format for GraphRAG.

    Args:
        mongodb_uri: MongoDB connection URI (e.g., "mongodb://localhost:27017")
        database_name: Name of the database
        collection_name: Name of the collection containing documents
        output_file: Path to output JSON file
        query_filter: Optional MongoDB query filter to select specific documents

    Example MongoDB document schema:
        {
            "id": "doc_123",
            "title": "Q4 Financial Report",
            "text": "Full document text here...",
            "access_type": "private",  # "public" | "domain" | "private"
            "owner_id": "user_uuid_123",
            "access_domains": ["finance", "legal"],
            "source": "internal_db",  # Optional source identifier
            "creation_date": "2025-11-13T10:00:00Z"
        }
    """
    client = MongoClient(mongodb_uri)
    db = client[database_name]
    collection = db[collection_name]

    # Query documents
    query = query_filter if query_filter else {}
    documents = list(collection.find(query))

    # Convert MongoDB objects to JSON-serializable format
    serializable_docs = [convert_to_json_serializable(doc) for doc in documents]

    # Write to JSON file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(serializable_docs, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(documents)} documents to {output_path}")
    client.close()


def export_documents_to_jsonl(
    mongodb_uri: str,
    database_name: str,
    collection_name: str,
    output_file: str | Path,
    query_filter: dict[str, Any] | None = None,
):
    """Export documents from MongoDB to JSONL format (one document per line).

    Args:
        mongodb_uri: MongoDB connection URI
        database_name: Name of the database
        collection_name: Name of the collection
        output_file: Path to output JSONL file
        query_filter: Optional MongoDB query filter
    """
    client = MongoClient(mongodb_uri)
    db = client[database_name]
    collection = db[collection_name]

    query = query_filter if query_filter else {}

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8") as f:
        for doc in collection.find(query):
            # Convert MongoDB objects to JSON-serializable format
            serializable_doc = convert_to_json_serializable(doc)
            f.write(json.dumps(serializable_doc, ensure_ascii=False) + "\n")
            count += 1

    print(f"Exported {count} documents to {output_path}")
    client.close()


def export_documents_to_csv(
    mongodb_uri: str,
    database_name: str,
    collection_name: str,
    output_file: str | Path,
    query_filter: dict[str, Any] | None = None,
):
    """Export documents from MongoDB to CSV format for GraphRAG.

    Args:
        mongodb_uri: MongoDB connection URI
        database_name: Name of the database
        collection_name: Name of the collection
        output_file: Path to output CSV file
        query_filter: Optional MongoDB query filter

    Note: access_domains will be converted to comma-separated string
    """
    try:
        import pandas as pd
    except ImportError as e:
        msg = "pandas is required for CSV export. Install it with: pip install pandas"
        raise ImportError(msg) from e

    client = MongoClient(mongodb_uri)
    db = client[database_name]
    collection = db[collection_name]

    query = query_filter if query_filter else {}
    documents = list(collection.find(query))

    # Convert MongoDB objects to JSON-serializable format first
    serializable_docs = [convert_to_json_serializable(doc) for doc in documents]

    # Convert to pandas DataFrame
    df = pd.DataFrame(serializable_docs)

    # Convert access_domains list to comma-separated string
    if "access_domains" in df.columns:
        df["access_domains"] = df["access_domains"].apply(
            lambda x: ",".join(x) if isinstance(x, list) else x
        )

    # Write to CSV
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"Exported {len(documents)} documents to {output_path}")
    client.close()


def main():
    """Example usage of MongoDB export functions."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Export documents from MongoDB for GraphRAG indexing with access control"
    )
    parser.add_argument(
        "--uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI",
    )
    parser.add_argument("--database", required=True, help="Database name")
    parser.add_argument("--collection", required=True, help="Collection name")
    parser.add_argument(
        "--output", required=True, help="Output file path (.json, .jsonl, or .csv)"
    )
    parser.add_argument(
        "--filter",
        help='MongoDB query filter as JSON string (e.g., \'{"access_type": "public"}\')',
    )

    args = parser.parse_args()

    # Parse filter if provided
    query_filter = json.loads(args.filter) if args.filter else None

    # Determine export format based on file extension
    output_path = Path(args.output)
    if output_path.suffix == ".json":
        export_documents_to_json(
            args.uri, args.database, args.collection, output_path, query_filter
        )
    elif output_path.suffix == ".jsonl":
        export_documents_to_jsonl(
            args.uri, args.database, args.collection, output_path, query_filter
        )
    elif output_path.suffix == ".csv":
        export_documents_to_csv(
            args.uri, args.database, args.collection, output_path, query_filter
        )
    else:
        print(f"Unsupported file format: {output_path.suffix}")
        print("Supported formats: .json, .jsonl, .csv")


if __name__ == "__main__":
    main()
