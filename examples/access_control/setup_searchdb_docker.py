#!/usr/bin/env python3
# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Setup MongoDB test database for GraphRAG access control testing.

This version works with Docker MongoDB instances that require authentication.
"""

from datetime import datetime

try:
    from pymongo import MongoClient
except ImportError as e:
    msg = "pymongo is required. Install it with: pip install pymongo"
    raise ImportError(msg) from e


def setup_test_database(
    uri="mongodb://admin:password123@localhost:27018/",
    database_name="searchdb"
):
    """Create searchdb database with 2 test documents.

    Args:
        uri: MongoDB connection URI with authentication
        database_name: Name of the database to create (default: searchdb)
    """

    # Connect to MongoDB
    print(f"Connecting to MongoDB...")
    client = MongoClient(uri)

    # Test connection
    try:
        client.admin.command('ping')
        print("✅ Connected to MongoDB successfully!")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        print("\nMake sure your MongoDB is running:")
        print("  docker-compose up -d")
        raise

    # Drop existing database (fresh start)
    if database_name in client.list_database_names():
        print(f"⚠️  Dropping existing '{database_name}' database...")
        client.drop_database(database_name)

    # Create database and collection
    db = client[database_name]
    collection = db['documents']

    # Test documents
    documents = [
        # Document 1: Domain-restricted (Finance)
        {
            "id": "doc_001",
            "title": "Q4 2024 Financial Report",
            "text": (
                "Revenue for Q4 2024 was $500 million, representing a 25% increase "
                "year-over-year. Operating expenses were maintained at $300 million, "
                "resulting in a net income of $150 million for the quarter. The engineering "
                "team received a budget allocation of $50 million, marketing received $30 "
                "million, and operations received $20 million for fiscal year 2025. Our "
                "profit margins improved from 28% to 30% compared to Q3 2024."
            ),
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["finance", "executive", "legal"],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 13, 10, 0, 0),
            "author": "CFO Office",
            "department": "Finance"
        },

        # Document 2: Public
        {
            "id": "doc_002",
            "title": "Company Mission and Values",
            "text": (
                "Our mission is to empower every person and organization on the planet to "
                "achieve more. We believe in innovation, diversity, and sustainability. Our "
                "core values include integrity, respect for individuals, accountability, and "
                "passion for technology. We are committed to making a positive impact on "
                "society through our products and services. Our vision is to be the most "
                "trusted technology partner for businesses worldwide."
            ),
            "access_type": "public",
            "owner_id": None,
            "access_domains": [],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 1, 9, 0, 0),
            "author": "Communications Team",
            "department": "Marketing"
        }
    ]

    # Insert documents
    result = collection.insert_many(documents)
    print(f"✅ Inserted {len(result.inserted_ids)} documents")

    # Create indexes
    collection.create_index("id", unique=True)
    collection.create_index("access_type")
    collection.create_index("access_domains")
    print("✅ Created indexes")

    # Verify and display
    print(f"\n📊 Database: {database_name}")
    print(f"📦 Collection: documents")
    print(f"📄 Document count: {collection.count_documents({})}\n")

    print("=" * 70)
    print("Inserted Documents:")
    print("=" * 70)

    for doc in collection.find():
        print(f"\n📄 Document ID: {doc['id']}")
        print(f"   Title: {doc['title']}")
        print(f"   Access Type: {doc['access_type']}")
        print(f"   Access Domains: {doc['access_domains']}")
        print(f"   Text Length: {len(doc['text'])} characters")

    print("\n" + "=" * 70)
    print("✅ Setup complete!")
    print("=" * 70)

    client.close()


def main():
    """Run the setup script."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup MongoDB test database for GraphRAG access control"
    )
    parser.add_argument(
        "--uri",
        default="mongodb://admin:password123@localhost:27018/",
        help="MongoDB connection URI (default: mongodb://admin:password123@localhost:27018/)"
    )
    parser.add_argument(
        "--database",
        default="searchdb",
        help="Database name (default: searchdb)"
    )

    args = parser.parse_args()

    print(f"🔌 Connecting to MongoDB at: {args.uri}\n")
    print(f"📊 Database: {args.database}\n")

    try:
        setup_test_database(args.uri, args.database)
        print("\n🎉 You can now export this data to JSON for GraphRAG!")
        print("\nNext step:")
        print(f"  python mongodb_export.py \\")
        print(f"    --uri '{args.uri}' \\")
        print(f"    --database '{args.database}' \\")
        print(f"    --collection 'documents' \\")
        print(f"    --output './input/documents.json'")
        print("\nOr verify in MongoDB shell:")
        print(f"  mongosh '{args.uri}' --eval 'db.documents.find().pretty()'")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
