#!/usr/bin/env python3
# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Setup MongoDB with comprehensive test data for GraphRAG access control."""

from datetime import datetime

try:
    from pymongo import MongoClient
except ImportError as e:
    msg = "pymongo is required. Install it with: pip install pymongo"
    raise ImportError(msg) from e


def setup_extended_test_database(uri="mongodb://localhost:27017"):
    """Create searchdb database with comprehensive test documents.

    Creates 10 test documents covering various access scenarios:
    - 2 public documents
    - 6 domain-restricted documents (finance, engineering, legal, product)
    - 2 private documents

    Args:
        uri: MongoDB connection URI
    """

    client = MongoClient(uri)

    # Drop and recreate
    if 'searchdb' in client.list_database_names():
        print("⚠️  Dropping existing 'searchdb' database...")
        client.drop_database('searchdb')

    db = client['searchdb']
    collection = db['documents']

    # Comprehensive test documents
    documents = [
        # 1. Public - Company Info
        {
            "id": "doc_public_001",
            "title": "Company Mission and Values",
            "text": "Our mission is to empower every person and organization on the planet to achieve more. We believe in innovation, diversity, and sustainability.",
            "access_type": "public",
            "owner_id": None,
            "access_domains": [],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 1),
            "author": "Communications",
            "department": "Marketing"
        },

        # 2. Public - Product Info
        {
            "id": "doc_public_002",
            "title": "Product Overview",
            "text": "Our flagship product helps teams collaborate effectively using AI-powered insights. Available in cloud and on-premise deployments.",
            "access_type": "public",
            "owner_id": None,
            "access_domains": [],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 5),
            "author": "Product Marketing",
            "department": "Marketing"
        },

        # 3. Domain - Finance Q4 Report
        {
            "id": "doc_finance_001",
            "title": "Q4 2024 Financial Results",
            "text": "Revenue for Q4 2024 was $500M (25% YoY growth). Operating expenses: $300M. Net income: $150M. Profit margins improved from 28% to 30%.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["finance", "executive"],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 13),
            "author": "CFO Office",
            "department": "Finance"
        },

        # 4. Domain - Finance Budget
        {
            "id": "doc_finance_002",
            "title": "2025 Budget Allocation",
            "text": "Engineering: $50M, Marketing: $30M, Operations: $20M, R&D: $40M. Total budget: $140M for fiscal year 2025.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["finance", "executive"],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 15),
            "author": "Finance Planning",
            "department": "Finance"
        },

        # 5. Domain - Engineering Architecture
        {
            "id": "doc_engineering_001",
            "title": "System Architecture Overview",
            "text": "Our platform uses microservices architecture with Kubernetes orchestration. Data stored in PostgreSQL with Redis caching. API Gateway handles authentication via OAuth 2.0.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["engineering", "devops"],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 10),
            "author": "Engineering Team",
            "department": "Engineering"
        },

        # 6. Domain - Engineering Security
        {
            "id": "doc_engineering_002",
            "title": "Security Guidelines",
            "text": "All APIs must use OAuth 2.0. Rate limiting: 1000 requests/hour per user. Data encrypted at rest with AES-256. TLS 1.3 for all connections.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["engineering", "security"],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 12),
            "author": "Security Team",
            "department": "Engineering"
        },

        # 7. Domain - Legal Compliance
        {
            "id": "doc_legal_001",
            "title": "Data Privacy Compliance",
            "text": "GDPR compliance achieved Q3 2024. CCPA certification pending. Data retention policy: 7 years for financial records, 3 years for user data.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["legal", "compliance", "executive"],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 8),
            "author": "Legal Team",
            "department": "Legal"
        },

        # 8. Private - HR Document
        {
            "id": "doc_private_001",
            "title": "Employee Performance Review - John Doe",
            "text": "John exceeded expectations in Q4. Strong leadership demonstrated during product launch. Recommended for promotion to Senior Engineer.",
            "access_type": "private",
            "owner_id": "user_hr_manager_001",
            "access_domains": [],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 14),
            "author": "HR Manager",
            "department": "HR"
        },

        # 9. Private - Executive Strategy
        {
            "id": "doc_private_002",
            "title": "Confidential: 2025 Strategic Plan",
            "text": "New product launch planned for Q2 2025. Target market: enterprise healthcare. Expected revenue: $200M first year. Acquisition discussions ongoing with Company X.",
            "access_type": "private",
            "owner_id": "user_ceo_001",
            "access_domains": [],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 16),
            "author": "CEO",
            "department": "Executive"
        },

        # 10. Cross-domain - Product & Engineering
        {
            "id": "doc_cross_001",
            "title": "Product Roadmap Q1 2025",
            "text": "New AI features launching January. Mobile app redesign February. API v3 release March. Engineering team scaling to 200 developers.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["product", "engineering", "marketing"],
            "source": "searchdb.documents",
            "created_at": datetime(2024, 11, 17),
            "author": "Product Team",
            "department": "Product"
        }
    ]

    # Insert documents
    result = collection.insert_many(documents)
    print(f"✅ Inserted {len(result.inserted_ids)} documents")

    # Create indexes
    collection.create_index("id", unique=True)
    collection.create_index("access_type")
    collection.create_index("access_domains")
    collection.create_index("department")
    print("✅ Created indexes")

    # Statistics
    print(f"\n📊 Database: searchdb")
    print(f"📦 Collection: documents")
    print(f"📄 Total documents: {collection.count_documents({})}\n")

    # Breakdown by access type
    print("Access Type Breakdown:")
    print(f"  Public: {collection.count_documents({'access_type': 'public'})}")
    print(f"  Domain: {collection.count_documents({'access_type': 'domain'})}")
    print(f"  Private: {collection.count_documents({'access_type': 'private'})}\n")

    # Domain breakdown
    print("Domain Access Breakdown:")
    domains = ["finance", "engineering", "legal", "product", "marketing", "security"]
    for domain in domains:
        count = collection.count_documents({"access_domains": domain})
        print(f"  {domain}: {count} documents")

    print("\n" + "=" * 70)
    print("Sample Documents:")
    print("=" * 70)

    for doc in collection.find().limit(3):
        print(f"\n📄 {doc['title']}")
        print(f"   ID: {doc['id']}")
        print(f"   Access: {doc['access_type']}")
        print(f"   Domains: {doc['access_domains']}")
        print(f"   Text: {doc['text'][:80]}...")

    print("\n" + "=" * 70)
    print("✅ Extended setup complete!")
    print("=" * 70)

    client.close()


def main():
    """Run the extended setup script."""
    import sys

    uri = sys.argv[1] if len(sys.argv) > 1 else "mongodb://localhost:27017"

    print(f"🔌 Connecting to MongoDB at: {uri}\n")

    try:
        setup_extended_test_database(uri)
        print("\n🎉 Ready for GraphRAG!")
        print("\nTest users you can simulate:")
        print("  1. Finance User: domains=['finance', 'executive']")
        print("  2. Engineering User: domains=['engineering', 'devops']")
        print("  3. Product Manager: domains=['product', 'marketing']")
        print("  4. HR Manager: user_id='user_hr_manager_001'")
        print("  5. CEO: user_id='user_ceo_001'")
        print("  6. Public User: no domains, no user_id")
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
