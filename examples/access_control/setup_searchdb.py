#!/usr/bin/env python3
# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Setup MongoDB test database for GraphRAG access control testing."""

from datetime import datetime

try:
    from pymongo import MongoClient
except ImportError as e:
    msg = "pymongo is required. Install it with: pip install pymongo"
    raise ImportError(msg) from e


def setup_test_database(uri="mongodb://localhost:27017"):
    """Create searchdb database with 2 test documents.

    Args:
        uri: MongoDB connection URI
    """

    # Connect to MongoDB
    client = MongoClient(uri)

    # Drop existing database (fresh start)
    if 'searchdb' in client.list_database_names():
        print("⚠️  Dropping existing 'searchdb' database...")
        client.drop_database('searchdb')

    # Create database and collection
    db = client['searchdb']
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
    print(f"\n📊 Database: searchdb")
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

    # Allow custom MongoDB URI
    uri = sys.argv[1] if len(sys.argv) > 1 else "mongodb://localhost:27017"

    print(f"🔌 Connecting to MongoDB at: {uri}\n")

    try:
        setup_test_database(uri)
        print("\n🎉 You can now export this data to JSON for GraphRAG!")
        print("\nNext step:")
        print("  python mongodb_export.py \\")
        print("    --uri 'mongodb://localhost:27017' \\")
        print("    --database 'searchdb' \\")
        print("    --collection 'documents' \\")
        print("    --output './input/documents.json'")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
