# GraphRAG Access Control - Tag-Based Document Access

This example demonstrates how to implement tag-based access control in GraphRAG to filter query results based on user permissions.

## Overview

The access control system allows you to:
- **Tag documents** with access metadata during indexing
- **Filter query results** based on user permissions at query time
- **Control data access** using three access levels: public, domain, and private

## Quick Start Scripts

This directory includes utility scripts to get started quickly:

- **`setup_searchdb.py`** - Creates a test MongoDB database with 2 sample documents
- **`setup_searchdb_extended.py`** - Creates a test MongoDB database with 10 comprehensive sample documents
- **`mongodb_export.py`** - Exports MongoDB documents to JSON/JSONL/CSV for GraphRAG
- **`quick_start.py`** - Creates a complete sample project with test data
- **`app_example.py`** - Flask web application with UI for testing access control

## Access Control Model

### Access Types

1. **Public** (`access_type: "public"`)
   - Accessible to all users
   - No restrictions

2. **Domain** (`access_type: "domain"`)
   - Accessible to users with matching domain tags
   - Example domains: `["finance", "legal", "engineering"]`
   - User needs at least ONE matching domain

3. **Private** (`access_type: "private"`)
   - Accessible only to the document owner
   - Requires `owner_id` to match user's ID

### Metadata Fields

```python
{
    "access_type": "private" | "domain" | "public",
    "owner_id": "user_uuid_or_email",  # For private documents
    "access_domains": ["finance", "legal"],  # For domain-restricted documents
    "source": "mongodb_collection_name"  # Optional source identifier
}
```

## Setup

### 0. Quick Setup with Test Database (Optional)

If you want to test the system immediately without your own data:

```bash
# Install MongoDB Python driver
pip install pymongo

# Option A: Create simple test database (2 documents)
python setup_searchdb.py

# Option B: Create extended test database (10 documents)
python setup_searchdb_extended.py

# The scripts will create a MongoDB database named 'searchdb'
# with collection 'documents' containing test data
```

### 1. MongoDB Document Schema

Your MongoDB collection should contain documents with the following structure:

```json
{
    "id": "doc_123",
    "title": "Q4 Financial Report",
    "text": "Full document content here...",
    "access_type": "private",
    "owner_id": "user_uuid_123",
    "access_domains": ["finance", "legal"],
    "source": "financial_reports",
    "creation_date": "2025-11-13T10:00:00Z"
}
```

### 2. Export Documents from MongoDB

Use the provided export utility to export your documents:

```bash
# Export to JSON
python mongodb_export.py \
    --uri "mongodb://localhost:27017" \
    --database "your_db" \
    --collection "documents" \
    --output "./input/documents.json"

# Export specific documents (e.g., only public documents)
python mongodb_export.py \
    --uri "mongodb://localhost:27017" \
    --database "your_db" \
    --collection "documents" \
    --output "./input/public_docs.json" \
    --filter '{"access_type": "public"}'

# Export to CSV
python mongodb_export.py \
    --uri "mongodb://localhost:27017" \
    --database "your_db" \
    --collection "documents" \
    --output "./input/documents.csv"
```

### 3. Configure GraphRAG

Create or update your `settings.yaml`:

```yaml
input:
  type: json  # or csv
  storage:
    type: file
    base_dir: input
  # IMPORTANT: Include access control fields as metadata
  metadata: ["access_type", "owner_id", "access_domains", "source"]
  text_column: "text"
  title_column: "title"

chunks:
  size: 1200
  overlap: 100
  # Optional: Prepend metadata to chunks for LLM context
  prepend_metadata: false
  chunk_size_includes_metadata: false

# Configure your LLM models (example with Gemini)
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
```

### 4. Index Your Documents

```bash
# Initialize GraphRAG project
graphrag init --root ./your-project

# Copy your settings.yaml to the project directory

# Run indexing
graphrag index --root ./your-project
```

## Usage

### Python API with Access Control

```python
import pandas as pd
from pathlib import Path
from graphrag.config.load_config import load_config
from graphrag.query.indexer_adapters import (
    read_indexer_text_units,
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
)
from graphrag.query.factory import get_local_search_engine_with_access_control
from graphrag.utils.storage import PipelineStorage

# Load configuration
config_path = Path("./your-project/settings.yaml")
config = load_config(config_path)

# Load indexed data
storage = PipelineStorage("./your-project/output")
text_units = read_indexer_text_units(
    pd.read_parquet(storage.get_path("create_final_text_units"))
)
entities = read_indexer_entities(
    pd.read_parquet(storage.get_path("create_final_entities")),
    pd.read_parquet(storage.get_path("create_final_communities")),
    community_level=2,
)
relationships = read_indexer_relationships(
    pd.read_parquet(storage.get_path("create_final_relationships"))
)
reports = read_indexer_reports(
    pd.read_parquet(storage.get_path("create_final_community_reports")),
    pd.read_parquet(storage.get_path("create_final_communities")),
    community_level=2,
)

# Example 1: Query as a finance user
finance_user_id = "user_finance_123"
finance_user_domains = ["finance", "legal"]

search_engine = get_local_search_engine_with_access_control(
    config=config,
    reports=reports,
    text_units=text_units,
    entities=entities,
    relationships=relationships,
    covariates={},
    response_type="multiple paragraphs",
    description_embedding_store=None,  # Configure if using vector search
    user_id=finance_user_id,
    user_domains=finance_user_domains,
)

result = await search_engine.search("What were the Q4 financial results?")
print(result.response)

# Example 2: Query as an engineering user (different access)
engineering_user_id = "user_eng_456"
engineering_user_domains = ["engineering", "product"]

search_engine_eng = get_local_search_engine_with_access_control(
    config=config,
    reports=reports,
    text_units=text_units,
    entities=entities,
    relationships=relationships,
    covariates={},
    response_type="multiple paragraphs",
    description_embedding_store=None,
    user_id=engineering_user_id,
    user_domains=engineering_user_domains,
)

result_eng = await search_engine_eng.search("What are the latest product updates?")
print(result_eng.response)

# Example 3: Public query (no access restrictions)
public_search_engine = get_local_search_engine_with_access_control(
    config=config,
    reports=reports,
    text_units=text_units,
    entities=entities,
    relationships=relationships,
    covariates={},
    response_type="multiple paragraphs",
    description_embedding_store=None,
    user_id=None,  # No user ID
    user_domains=[],  # No domains
)

result_public = await public_search_engine.search("What is our company mission?")
print(result_public.response)
```

### Manual Filtering (Advanced)

If you want more control over the filtering process:

```python
from graphrag.query.filters.access_control import AccessControlFilter

# Create filter for a specific user
user_filter = AccessControlFilter(
    user_id="user_123",
    user_domains=["finance", "engineering"]
)

# Filter data manually
filtered_text_units = user_filter.filter_text_units(text_units)

# Filter entities based on accessible text units
accessible_tu_ids = {tu.id for tu in filtered_text_units}
filtered_entities = user_filter.filter_entities_by_source(
    entities, accessible_tu_ids
)
filtered_relationships = user_filter.filter_relationships_by_source(
    relationships, accessible_tu_ids
)

# Use filtered data with standard search engine
from graphrag.query.factory import get_local_search_engine

search_engine = get_local_search_engine(
    config=config,
    reports=reports,
    text_units=filtered_text_units,
    entities=filtered_entities,
    relationships=filtered_relationships,
    covariates={},
    response_type="multiple paragraphs",
    description_embedding_store=None,
)
```

## How It Works

### Indexing Phase

1. **Document ingestion**: MongoDB documents are exported with access control metadata
2. **Text chunking**: Metadata is propagated to each text chunk
3. **Entity extraction**: Entities are extracted from chunks (inherit source text unit IDs)
4. **Storage**: Text units are stored with access control attributes in `text_units.parquet`

### Query Phase (Option C: Filtered Context)

1. **Filter text units**: Only text units the user can access are included
2. **Filter entities**: Entities are included if user has access to **at least one** source text unit
3. **Filter relationships**: Relationships are included if user has access to source text units
4. **Build context**: Search uses only the filtered data to generate responses

### Graph Boundary Handling

When an entity appears in multiple documents with different access levels:

**Example:**
- Entity "Q4 Revenue" appears in:
  - Private finance document (accessible to finance team)
  - Public marketing document (accessible to everyone)

**Behavior with Option C:**
- Finance user query → sees entity + private finance context
- Marketing user query → sees entity + public marketing context
- **Same entity, different supporting evidence** based on access

This prevents data leakage while maintaining graph connectivity.

## Testing Access Control

### Test Script

```python
from graphrag.query.filters.access_control import AccessControlFilter
from graphrag.data_model.text_unit import TextUnit

# Create test text units with different access levels
text_units = [
    TextUnit(
        id="tu_1",
        text="Public information",
        attributes={"access_type": "public"}
    ),
    TextUnit(
        id="tu_2",
        text="Finance data",
        attributes={
            "access_type": "domain",
            "access_domains": ["finance"]
        }
    ),
    TextUnit(
        id="tu_3",
        text="Private user notes",
        attributes={
            "access_type": "private",
            "owner_id": "user_123"
        }
    ),
]

# Test as finance user
finance_filter = AccessControlFilter(
    user_id="user_456",
    user_domains=["finance"]
)
filtered = finance_filter.filter_text_units(text_units)
print(f"Finance user sees {len(filtered)} text units")  # Should see tu_1, tu_2

# Test as document owner
owner_filter = AccessControlFilter(
    user_id="user_123",
    user_domains=[]
)
filtered = owner_filter.filter_text_units(text_units)
print(f"Owner sees {len(filtered)} text units")  # Should see tu_1, tu_3

# Test as public user
public_filter = AccessControlFilter(
    user_id=None,
    user_domains=[]
)
filtered = public_filter.filter_text_units(text_units)
print(f"Public user sees {len(filtered)} text units")  # Should see only tu_1
```

## Performance Considerations

1. **Query-time filtering**: Filtering happens at query time, adding minimal overhead
2. **Caching**: Consider caching filtered entity lists per user/domain combination
3. **Indexing**: No performance impact during indexing
4. **Vector stores**: If using vector search, implement ID-based filtering in your vector store

## Security Notes

1. **Default deny**: Unknown access types are denied by default
2. **No metadata = public**: If access control fields are missing, documents are treated as public
3. **Source tracking**: Entities track their source text units for precise access control
4. **Aggregation**: Community reports may aggregate across access levels - handle with care

## Troubleshooting

### Issue: Access control fields not in text_units.parquet

**Solution**: Ensure metadata fields are specified in `settings.yaml`:
```yaml
input:
  metadata: ["access_type", "owner_id", "access_domains", "source"]
```

### Issue: All documents appear as public

**Check**:
1. MongoDB export includes access control fields
2. JSON/CSV has the correct column names
3. Metadata configuration in settings.yaml is correct

### Issue: Empty query results for authorized users

**Debug**:
```python
# Check what text units were loaded
print(f"Total text units: {len(text_units)}")

# Check what was filtered
filtered = access_filter.filter_text_units(text_units)
print(f"Filtered text units: {len(filtered)}")

# Check attributes
for tu in text_units[:5]:
    print(f"Text unit {tu.id}: {tu.attributes}")
```

## Additional Resources

- [GraphRAG Documentation](https://microsoft.github.io/graphrag/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)
- [GraphRAG Configuration](https://microsoft.github.io/graphrag/config/)

## License

Copyright (c) 2024 Microsoft Corporation.
Licensed under the MIT License.
