# Comprehensive Entity Type Taxonomy

This document describes the 15 entity types configured for the GraphRAG knowledge base, designed to capture information across all sectors (Wikipedia-like coverage).

## Entity Types Overview

| Entity Type | Description | Examples | Use Cases |
|------------|-------------|----------|-----------|
| **organization** | Companies, institutions, agencies, NGOs, government bodies | Microsoft, MIT, WHO, FBI, Greenpeace | Corporate info, institutional relationships, org structures |
| **person** | People, executives, researchers, authors, leaders | Satya Nadella, Bill Gates, researchers, CEOs | Leadership, authorship, expertise, biographical info |
| **geo** | Geographic locations, cities, countries, regions, facilities | New York, California, Europe, Building 42, datacenter | Location-based queries, regional analysis, facility mapping |
| **event** | Events, conferences, incidents, milestones, launches | Product launch, conference, merger, breakthrough | Timeline analysis, historical context, event tracking |
| **technology** | Software, hardware, AI models, platforms, systems, tools | GPT-4, Azure, Linux, quantum computing, NLP | Technical architecture, technology stack, capabilities |
| **product** | Products, services, offerings, solutions | Office 365, iPhone, consulting services, SaaS platform | Product portfolios, competitive analysis, offerings |
| **concept** | Abstract ideas, theories, methodologies, frameworks, principles | Agile, machine learning, sustainability, DevOps | Knowledge management, methodology tracking, conceptual relationships |
| **industry** | Sectors, markets, business domains, verticals | Healthcare, finance, technology, manufacturing | Industry analysis, market segmentation, domain expertise |
| **metric** | KPIs, statistics, measurements, percentages, financial figures | Revenue, market share, 99.9% uptime, ROI | Performance tracking, benchmarking, quantitative analysis |
| **regulation** | Laws, policies, standards, compliance requirements, guidelines | GDPR, SOC 2, FDA approval, HIPAA | Compliance tracking, regulatory analysis, legal requirements |
| **project** | Initiatives, programs, research projects, campaigns | Digital transformation, vaccine development, Mars mission | Project tracking, initiative management, research programs |
| **patent** | Intellectual property, inventions, trademarks | Patent #123456, trademark registration, invention | IP management, innovation tracking, competitive intelligence |
| **skill** | Competencies, capabilities, expertise areas, qualifications | Python programming, cloud architecture, data science | Skills mapping, talent management, expertise location |
| **document** | Reports, papers, publications, studies, specifications | White paper, research paper, technical spec, annual report | Document management, reference tracking, citation networks |
| **currency** | Financial instruments, money, investments, stocks | USD, Bitcoin, MSFT stock, venture capital | Financial analysis, investment tracking, market data |

## Entity Type Selection Guide

### When Multiple Types Could Apply

Some entities could fit multiple categories. Use these guidelines:

**Technology vs Product**
- **Technology**: Core technical capability or platform (e.g., "Azure Cloud Platform", "React Framework")
- **Product**: Market offering with pricing/packaging (e.g., "Office 365 Subscription", "iPhone 15 Pro")

**Organization vs Industry**
- **Organization**: Specific named entity (e.g., "Microsoft")
- **Industry**: Category or sector (e.g., "Technology Industry", "Healthcare Sector")

**Event vs Project**
- **Event**: Time-bounded occurrence (e.g., "2024 Product Launch", "Annual Conference")
- **Project**: Ongoing initiative (e.g., "Digital Transformation Initiative", "Research Program")

**Concept vs Skill**
- **Concept**: Theoretical framework or methodology (e.g., "Agile Methodology", "Machine Learning")
- **Skill**: Practical competency (e.g., "Agile Project Management", "Machine Learning Engineering")

**Metric vs Currency**
- **Metric**: Performance measurement (e.g., "45% growth rate", "99.9% uptime")
- **Currency**: Monetary value (e.g., "$50 million", "€10M investment")

## Examples from Acme Corporation Documents

### doc006 - Research and Development

**Original Text:**
```
Acme's research division is investing heavily in artificial intelligence and machine learning.
The AI research team has developed a new natural language processing model that outperforms GPT-3
on specific enterprise tasks. Research spending for 2024 totaled $120 million. The company filed
15 new patents related to distributed computing and AI technologies. Research partnerships
established with MIT and Stanford University.
```

**Extracted Entities:**

| Entity | Type | Description |
|--------|------|-------------|
| Acme's research division | organization | Research division of Acme Corporation focused on AI and ML |
| AI research team | organization | Team that developed NLP model |
| artificial intelligence | technology | Core technology area of investment |
| machine learning | technology | Core technology area of investment |
| natural language processing model | technology | NLP model developed by Acme's research team |
| GPT-3 | technology | Benchmark model for comparison |
| enterprise tasks | concept | Specific use cases where Acme's model excels |
| 2024 | event | Year of research spending |
| $120 million | currency | Total research spending amount |
| 15 new patents | patent | Intellectual property filed |
| distributed computing | technology | Technology area of patent filings |
| AI technologies | technology | Technology area of patent filings |
| MIT | organization | Research partnership university |
| Stanford University | organization | Research partnership university |

### doc004 - Technology Division

**Original Text:**
```
Acme Corporation's technology division reported Q4 2024 revenue of $125 million, representing
a 15% increase from Q3. The division focuses on cloud infrastructure and AI-powered analytics.
```

**Extracted Entities:**

| Entity | Type | Description |
|--------|------|-------------|
| Acme Corporation's technology division | organization | Technology division of Acme Corporation |
| Q4 2024 | event | Fourth quarter of 2024 |
| $125 million | currency | Revenue amount |
| 15% increase | metric | Revenue growth percentage |
| Q3 | event | Third quarter (comparison period) |
| cloud infrastructure | technology | Core technology focus |
| AI-powered analytics | product | Product/service offering |

## Benefits of Comprehensive Entity Types

### 1. **Better Entity Coverage**
- Capture 90%+ of entities vs 50% with limited types
- Reduce "missing entity" issues like doc006

### 2. **More Precise Relationships**
```
Before (limited types):
  ACME CORPORATION -- funded by --> $120 MILLION (no relationship, wrong type)

After (comprehensive types):
  ACME CORPORATION -- invested --> $120 MILLION (currency) -- in --> AI RESEARCH TEAM (organization)
```

### 3. **Domain-Specific Queries**
```
Query: "What patents has Acme filed?"
→ Finds all entities of type 'patent'

Query: "What compliance regulations apply?"
→ Finds all entities of type 'regulation'

Query: "What technical skills are mentioned?"
→ Finds all entities of type 'skill'
```

### 4. **Rich Knowledge Graph**
With 15 entity types, the knowledge graph can represent complex domain knowledge:

```
ACME CORPORATION (organization)
  ├─ produces → ACMECLOUD (product)
  ├─ operates_in → TECHNOLOGY INDUSTRY (industry)
  ├─ partnered_with → MIT (organization)
  ├─ filed → PATENT #123 (patent)
  ├─ uses → MACHINE LEARNING (technology)
  ├─ complies_with → GDPR (regulation)
  ├─ achieved → 15% GROWTH (metric)
  ├─ spent → $120 MILLION (currency)
  ├─ launched → AI RESEARCH PROJECT (project)
  └─ applies → AGILE METHODOLOGY (concept)
```

## Performance Considerations

### Indexing Time
- **Before**: 5 types = ~5-10 minutes
- **After**: 15 types = ~7-15 minutes (+40-50% time)

### Entity Count
- **Before**: 18 entities from 12 documents
- **After**: 50-80 entities from 12 documents (2-4x increase)

### Trade-offs

**Pros:**
- ✅ Comprehensive knowledge capture
- ✅ Better query coverage
- ✅ Fewer "no results" scenarios
- ✅ Richer relationship mapping

**Cons:**
- ⚠️ Longer indexing time
- ⚠️ Higher token usage (LLM calls)
- ⚠️ More storage for entities
- ⚠️ Potential for entity type confusion

### Optimization Tips

1. **Start with all 15 types**, then prune unused ones after analysis
2. **Monitor extraction quality** - check if LLM correctly assigns types
3. **Consider domain-specific types** - e.g., add "drug", "gene" for biomedical
4. **Use max_gleanings: 2** to improve quality without huge time increase
5. **Batch similar documents** to optimize LLM caching

## Re-indexing Checklist

After updating entity types from 5 to 15:

- [ ] Updated `entity_extraction.entity_types` in settings.yaml
- [ ] Updated `extract_graph.entity_types` in settings.yaml
- [ ] Cleared cache: `rm -rf my-project/cache/*`
- [ ] Cleared old entities: `rm -rf my-project/output/*/artifacts/*.parquet`
- [ ] Cleared vector store: `rm -rf my-project/output/lancedb`
- [ ] Re-ran indexing: `python -m graphrag index --root my-project`
- [ ] Verified entity count increased: Check entities.parquet
- [ ] Tested queries covering new entity types
- [ ] Reviewed extraction quality in logs

## Next Steps

1. **Re-index** with the new configuration
2. **Analyze** the extracted entities by type
3. **Refine** entity types based on your domain
4. **Add custom types** if needed (e.g., "medical_device", "chemical", "algorithm")

## Custom Entity Types for Specific Domains

If you need even more specificity, consider these additions:

**Healthcare/Biomedical:**
- `drug`, `disease`, `gene`, `protein`, `clinical_trial`, `medical_device`

**Finance/Investment:**
- `fund`, `portfolio`, `security`, `bond`, `derivative`, `exchange`

**Legal:**
- `law`, `case`, `court`, `contract`, `clause`, `jurisdiction`

**Scientific Research:**
- `theory`, `hypothesis`, `experiment`, `dataset`, `publication`, `methodology`

**Software Engineering:**
- `library`, `framework`, `api`, `database`, `algorithm`, `architecture_pattern`

Add these to `entity_types` as needed for your specific domain!
