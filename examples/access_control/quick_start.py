#!/usr/bin/env python3
# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Quick start example for GraphRAG with access control."""

import json
from pathlib import Path


def create_sample_documents():
    """Create sample documents with access control metadata."""
    documents = [
        # Public documents
        {
            "id": "doc_001",
            "title": "Company Mission Statement",
            "text": "Our mission is to empower every person and organization on the planet to achieve more.",
            "access_type": "public",
            "owner_id": None,
            "access_domains": [],
            "source": "public_website",
        },
        {
            "id": "doc_002",
            "title": "Product Overview",
            "text": "Our flagship product helps teams collaborate effectively using AI-powered insights.",
            "access_type": "public",
            "owner_id": None,
            "access_domains": [],
            "source": "public_website",
        },
        # Domain-restricted documents (Finance)
        {
            "id": "doc_003",
            "title": "Q4 2024 Financial Report",
            "text": "Revenue increased 25% year-over-year to $500M. Operating expenses were $300M, resulting in net income of $150M.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["finance", "executive"],
            "source": "financial_reports",
        },
        {
            "id": "doc_004",
            "title": "Budget Allocation 2025",
            "text": "Engineering budget: $50M, Marketing budget: $30M, Operations budget: $20M.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["finance", "executive"],
            "source": "financial_reports",
        },
        # Domain-restricted documents (Engineering)
        {
            "id": "doc_005",
            "title": "System Architecture Design",
            "text": "The platform uses a microservices architecture with Kubernetes orchestration. Data is stored in PostgreSQL and cached in Redis.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["engineering", "product"],
            "source": "engineering_docs",
        },
        {
            "id": "doc_006",
            "title": "API Security Guidelines",
            "text": "All APIs must use OAuth 2.0 authentication. Rate limiting is set to 1000 requests per hour per user.",
            "access_type": "domain",
            "owner_id": None,
            "access_domains": ["engineering"],
            "source": "engineering_docs",
        },
        # Private documents
        {
            "id": "doc_007",
            "title": "Personal Performance Review - John Doe",
            "text": "John exceeded expectations in Q4. Strong leadership skills demonstrated in the product launch.",
            "access_type": "private",
            "owner_id": "user_hr_manager",
            "access_domains": [],
            "source": "hr_system",
        },
        {
            "id": "doc_008",
            "title": "Confidential Strategy Memo",
            "text": "Plans for new product launch in Q2 2025. Target market: enterprise customers in healthcare.",
            "access_type": "private",
            "owner_id": "user_ceo",
            "access_domains": [],
            "source": "executive_docs",
        },
    ]

    return documents


def setup_sample_project():
    """Set up a sample GraphRAG project with access control."""
    project_root = Path("./sample_access_control_project")
    input_dir = project_root / "input"

    # Create directories
    input_dir.mkdir(parents=True, exist_ok=True)

    # Create sample documents
    documents = create_sample_documents()

    # Save to JSON
    input_file = input_dir / "documents.json"
    with input_file.open("w") as f:
        json.dump(documents, f, indent=2)

    print(f"Created {len(documents)} sample documents in {input_file}")

    # Create settings.yaml
    settings = """
input:
  type: json
  storage:
    type: file
    base_dir: input
  file_pattern: ".*\\.json$"
  metadata: ["access_type", "owner_id", "access_domains", "source"]
  text_column: "text"
  title_column: "title"

chunks:
  size: 300
  overlap: 50
  prepend_metadata: false
  chunk_size_includes_metadata: false

models:
  default_chat_model:
    type: chat
    auth_type: api_key
    api_key: ${GEMINI_API_KEY}
    model_provider: gemini
    model: gemini-2.5-flash-lite

  default_embedding_model:
    type: embedding
    auth_type: api_key
    api_key: ${GEMINI_API_KEY}
    model_provider: gemini
    model: gemini-embedding-001
"""

    settings_file = project_root / "settings.yaml"
    with settings_file.open("w") as f:
        f.write(settings)

    print(f"Created settings file: {settings_file}")

    # Create .env template
    env_template = """# GraphRAG Configuration
GEMINI_API_KEY=your_gemini_api_key_here
"""

    env_file = project_root / ".env.template"
    with env_file.open("w") as f:
        f.write(env_template)

    print(f"Created .env template: {env_file}")

    # Create README
    readme = """# Sample Access Control Project

This is a sample GraphRAG project demonstrating access control.

## Setup

1. Copy `.env.template` to `.env` and add your Gemini API key:
   ```bash
   cp .env.template .env
   # Edit .env and add your GEMINI_API_KEY
   ```

2. Run indexing:
   ```bash
   graphrag index --root .
   ```

3. Test queries with different access levels:
   ```python
   from graphrag.query.factory import get_local_search_engine_with_access_control
   # See examples/access_control/README.md for full example
   ```

## Sample Documents

- **Public** (2 docs): Company mission, product overview
- **Finance domain** (2 docs): Financial reports, budget
- **Engineering domain** (2 docs): Architecture, API docs
- **Private** (2 docs): Performance review, strategy memo

## Test Users

1. **Finance User**: `user_id=None`, `domains=["finance"]`
   - Can access: public + finance domain docs

2. **Engineering User**: `user_id=None`, `domains=["engineering"]`
   - Can access: public + engineering domain docs

3. **HR Manager**: `user_id="user_hr_manager"`, `domains=[]`
   - Can access: public + their private doc

4. **Public User**: `user_id=None`, `domains=[]`
   - Can access: only public docs
"""

    readme_file = project_root / "README.md"
    with readme_file.open("w") as f:
        f.write(readme)

    print(f"Created README: {readme_file}")
    print("\n" + "=" * 50)
    print("Sample project created successfully!")
    print("=" * 50)
    print(f"\nProject location: {project_root.absolute()}")
    print("\nNext steps:")
    print(f"1. cd {project_root}")
    print("2. cp .env.template .env")
    print("3. Edit .env and add your GEMINI_API_KEY")
    print("4. graphrag index --root .")
    print("\nSee examples/access_control/README.md for query examples.")


if __name__ == "__main__":
    setup_sample_project()
