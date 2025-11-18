# Re-indexing Guide for Improved Entity Extraction

## Why Re-index?

The current indexed data is missing entities from the `research_reports` document (doc006) because:
1. The `technology` entity type was not in the configuration
2. `max_gleanings` was set to 1 (only one extraction attempt)

## What Was Fixed

✅ Added `technology` to entity types
✅ Increased `max_gleanings` from 1 to 2
✅ Updated entity extraction prompt

## Expected Improvements

After re-indexing, these entities should be extracted from doc006:
- **AI research team** → ORGANIZATION
- **MIT** → ORGANIZATION
- **Stanford University** → ORGANIZATION
- **GPT-3** → TECHNOLOGY or EVENT
- **NLP model** → TECHNOLOGY
- **machine learning** → TECHNOLOGY

## How to Re-index

### Option 1: Full Re-index (Recommended)

```bash
# 1. Navigate to project directory
cd /home/user/graphrag/my-project

# 2. Clean old cache and output (optional but recommended)
rm -rf cache/*
rm -rf output/*/artifacts/*.parquet
rm -rf output/lancedb

# 3. Run indexing
python -m graphrag index --root .

# 4. Wait for completion (may take 5-15 minutes depending on document size)

# 5. Verify entities were extracted
python3 -c "
import pandas as pd
import glob

# Find the entities parquet file
entity_files = glob.glob('output/*/artifacts/*entities.parquet')
if entity_files:
    df = pd.read_parquet(entity_files[0])
    print(f'Total entities: {len(df)}')
    print('\nEntities containing AI/research keywords:')
    research_entities = df[df['title'].str.contains('AI|MIT|STANFORD|RESEARCH|NLP|GPT', case=False, na=False)]
    print(research_entities[['title', 'type', 'description']].to_string())
else:
    print('No entity files found yet')
"
```

### Option 2: Quick Check (Skip full re-index)

If you want to test without re-indexing everything:

```bash
# Just check current entities
cd /home/user/graphrag/my-project
python3 -c "
import pandas as pd
import glob

entity_files = glob.glob('output/*/artifacts/*entities.parquet')
if entity_files:
    df = pd.read_parquet(entity_files[0])

    # Check text_unit_ids to see which entities come from research_reports
    text_units = pd.read_parquet(glob.glob('output/*/artifacts/*text_units.parquet')[0])
    research_tu_ids = text_units[text_units['source'] == 'research_reports']['id'].tolist()

    print('Entities from research_reports:')
    for idx, row in df.iterrows():
        if row.get('text_unit_ids') and any(tu_id in research_tu_ids for tu_id in row['text_unit_ids']):
            print(f'  - {row[\"title\"]} ({row[\"type\"]})')
"
```

## Verification

After re-indexing, run a test query:

```bash
cd /home/user/graphrag/examples/access_control
python app_fastapi.py --project-root ../../my-project
```

Then query: **"tell me about Acme's research division AI research team"**

Expected output:
```
🔬 ENTITIES FROM RESEARCH_REPORTS:
  ✅ Found 3+ entities from research_reports:
  [1] AI RESEARCH TEAM (type: ORGANIZATION)
  [2] MIT (type: ORGANIZATION)
  [3] STANFORD UNIVERSITY (type: ORGANIZATION)
```

## If Re-indexing Fails

If you still don't see entities from research_reports after re-indexing:

1. **Check the LLM logs** in `my-project/logs/` for entity extraction errors
2. **Increase temperature** in settings.yaml to make extraction more creative:
   ```yaml
   models:
     default_chat_model:
       temperature: 0.9  # Increased from 0.7
   ```
3. **Try a different model** if llama3.1 struggles with entity extraction
4. **Check doc006 is in input** by running: `cat input/documents.json | jq '.[] | select(.id=="doc006")'`

## Troubleshooting

**Problem:** Re-indexing takes too long
**Solution:** Comment out non-essential documents in input/documents.json, or reduce `max_gleanings` back to 1

**Problem:** Out of memory errors
**Solution:** Reduce `concurrent_requests` in settings.yaml from 4 to 2

**Problem:** LLM timeouts
**Solution:** Increase `max_tokens` in settings.yaml

## Next Steps

After successful re-indexing with entities from research_reports, the query should return detailed information about:
- AI research team's NLP model
- Performance comparison with GPT-3
- Research partnerships with MIT and Stanford
- $120 million research spending
- 15 new patents filed
