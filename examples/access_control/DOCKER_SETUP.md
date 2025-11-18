# MongoDB Docker Setup for GraphRAG Access Control

This guide shows how to set up GraphRAG with a MongoDB Docker container.

## Your Docker Compose Configuration

```yaml
services:
  mongodb:
    image: mongo:7.0
    container_name: authdb-mongodb
    restart: unless-stopped
    ports:
      - "27018:27017"  # Note: External port is 27018
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password123
      MONGO_INITDB_DATABASE: test
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/data/configdb
    networks:
      - authdb-network
```

## Connection Details

- **Host**: `localhost`
- **Port**: `27018` (mapped from container's 27017)
- **Username**: `admin`
- **Password**: `password123`
- **Connection URI**: `mongodb://admin:password123@localhost:27018/`

---

## Quick Setup

### 1. Start MongoDB Container

```bash
# Start your MongoDB container
docker-compose up -d

# Verify it's running
docker ps | grep authdb-mongodb

# Check health
docker-compose ps
```

### 2. Create Test Database

```bash
cd examples/access_control

# Install pymongo if needed
pip install pymongo

# Create test database with 2 documents
python setup_searchdb_docker.py

# Or create extended test database with 10 documents
python setup_searchdb_docker.py --database searchdb
```

**Expected output:**
```
🔌 Connecting to MongoDB at: mongodb://admin:password123@localhost:27018/
📊 Database: searchdb

Connecting to MongoDB...
✅ Connected to MongoDB successfully!
✅ Inserted 2 documents
✅ Created indexes

📊 Database: searchdb
📦 Collection: documents
📄 Document count: 2
```

### 3. Verify Data in MongoDB

```bash
# Connect to MongoDB shell in container
docker exec -it authdb-mongodb mongosh -u admin -p password123

# Or use mongosh from host
mongosh "mongodb://admin:password123@localhost:27018/"
```

**In MongoDB shell:**
```javascript
// Switch to searchdb
use searchdb

// Count documents
db.documents.count()
// Output: 2

// View documents
db.documents.find().pretty()

// Check access types
db.documents.distinct("access_type")
// Output: ["domain", "public"]

// Check domains
db.documents.distinct("access_domains")
// Output: [[], ["finance", "executive", "legal"]]

// Find finance documents
db.documents.find({"access_domains": "finance"}).pretty()

// Exit
exit
```

### 4. Export to JSON for GraphRAG

```bash
# Export from Docker MongoDB
python mongodb_export.py \
  --uri "mongodb://admin:password123@localhost:27018/" \
  --database "searchdb" \
  --collection "documents" \
  --output "../../my-graphrag-project/input/documents.json"
```

**Expected output:**
```
Exported 2 documents to ../../my-graphrag-project/input/documents.json
```

### 5. Verify the Export

```bash
# Check the exported file
cat ../../my-graphrag-project/input/documents.json | jq '.[0]'

# Or use Python
python -c "import json; print(json.dumps(json.load(open('../../my-graphrag-project/input/documents.json'))[0], indent=2))"
```

---

## Full Workflow with Your Docker Setup

### Complete End-to-End Setup

```bash
# 1. Start MongoDB
docker-compose up -d
docker-compose ps  # Verify running

# 2. Create GraphRAG project
mkdir my-graphrag-project
cd my-graphrag-project
graphrag init --root .

# 3. Create test database
cd ../graphrag/examples/access_control
python setup_searchdb_docker.py

# 4. Export to JSON
python mongodb_export.py \
  --uri "mongodb://admin:password123@localhost:27018/" \
  --database "searchdb" \
  --collection "documents" \
  --output "../../my-graphrag-project/input/documents.json"

# 5. Configure GraphRAG
cd ../../my-graphrag-project

# Edit .env
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env

# Edit settings.yaml
cat > settings.yaml << 'EOF'
input:
  type: json
  file_type: json
  base_dir: "input"
  file_pattern: ".*\\.json$"
  text_column: "text"
  title_column: "title"
  metadata: ["access_type", "owner_id", "access_domains", "source"]

chunks:
  size: 1200
  overlap: 100

models:
  default_chat_model:
    type: chat
    auth_type: api_key
    api_key: ${GEMINI_API_KEY}
    model_provider: gemini
    model: gemini-2.0-flash-exp

  default_embedding_model:
    type: embedding
    auth_type: api_key
    api_key: ${GEMINI_API_KEY}
    model_provider: gemini
    model: text-embedding-004
EOF

# 6. Run indexing
graphrag index --root .

# 7. Test with web UI
cd ../graphrag/examples/access_control
python app_example.py --project-root ../../my-graphrag-project

# 8. Open browser to http://localhost:5000
```

---

## Adding Your Own Data to MongoDB

### Using mongosh in Docker Container

```bash
# Connect to container
docker exec -it authdb-mongodb mongosh -u admin -p password123

# Switch to searchdb
use searchdb

# Insert a document
db.documents.insertOne({
  "id": "doc_custom_001",
  "title": "My Custom Document",
  "text": "Your document content here...",
  "access_type": "domain",
  "owner_id": null,
  "access_domains": ["engineering", "product"],
  "source": "searchdb.documents",
  "created_at": new Date()
})

// Verify
db.documents.find({"id": "doc_custom_001"}).pretty()

// Exit
exit
```

### Using Python Script

```python
from pymongo import MongoClient
from datetime import datetime

# Connect
client = MongoClient("mongodb://admin:password123@localhost:27018/")
db = client['searchdb']
collection = db['documents']

# Insert document
doc = {
    "id": "doc_custom_002",
    "title": "Another Document",
    "text": "Content goes here...",
    "access_type": "private",
    "owner_id": "user_123",
    "access_domains": [],
    "source": "searchdb.documents",
    "created_at": datetime.now()
}

result = collection.insert_one(doc)
print(f"Inserted document with ID: {result.inserted_id}")

# Verify
count = collection.count_documents({})
print(f"Total documents: {count}")

client.close()
```

---

## Troubleshooting

### Issue: Cannot connect to MongoDB

```bash
# Check if container is running
docker ps | grep authdb-mongodb

# Check container logs
docker logs authdb-mongodb

# Restart container
docker-compose restart mongodb

# Check if port 27018 is accessible
nc -zv localhost 27018
# Or
telnet localhost 27018
```

### Issue: Authentication failed

```bash
# Verify credentials in docker-compose.yml
# Make sure you're using the correct username/password

# Test connection
mongosh "mongodb://admin:password123@localhost:27018/" --eval "db.adminCommand('ping')"
```

### Issue: Database not found after creation

```bash
# Connect to MongoDB
mongosh "mongodb://admin:password123@localhost:27018/"

# List databases
show dbs

# Switch to searchdb (creates it if doesn't exist)
use searchdb

# Insert a test document to persist the database
db.test.insertOne({test: 1})

# Now it should appear
show dbs
```

### Issue: Port conflict (27018 already in use)

```bash
# Check what's using the port
lsof -i :27018

# Change the port in docker-compose.yml
# ports:
#   - "27019:27017"  # Use 27019 instead

# Update connection URI
# mongodb://admin:password123@localhost:27019/
```

---

## Script Options

### setup_searchdb_docker.py

```bash
# Custom database name
python setup_searchdb_docker.py --database mydb

# Custom MongoDB URI
python setup_searchdb_docker.py \
  --uri "mongodb://user:pass@host:port/"

# Both
python setup_searchdb_docker.py \
  --uri "mongodb://admin:password123@localhost:27018/" \
  --database searchdb
```

### mongodb_export.py

```bash
# Export with filter
python mongodb_export.py \
  --uri "mongodb://admin:password123@localhost:27018/" \
  --database "searchdb" \
  --collection "documents" \
  --filter '{"access_type": "public"}' \
  --output "public_only.json"

# Export to CSV
python mongodb_export.py \
  --uri "mongodb://admin:password123@localhost:27018/" \
  --database "searchdb" \
  --collection "documents" \
  --output "documents.csv"

# Export to JSONL
python mongodb_export.py \
  --uri "mongodb://admin:password123@localhost:27018/" \
  --database "searchdb" \
  --collection "documents" \
  --output "documents.jsonl"
```

---

## Environment Variables

Create a `.env` file for easier management:

```bash
# .env
MONGODB_URI=mongodb://admin:password123@localhost:27018/
MONGODB_DATABASE=searchdb
GEMINI_API_KEY=your_gemini_key_here
```

**Use in scripts:**

```python
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("MONGODB_URI")
database = os.getenv("MONGODB_DATABASE")
```

---

## Docker Commands Reference

```bash
# Start MongoDB
docker-compose up -d

# Stop MongoDB
docker-compose down

# View logs
docker logs authdb-mongodb -f

# Execute shell in container
docker exec -it authdb-mongodb bash

# Connect to MongoDB shell
docker exec -it authdb-mongodb mongosh -u admin -p password123

# Restart MongoDB
docker-compose restart mongodb

# Check status
docker-compose ps

# Stop and remove (keeps volumes)
docker-compose down

# Stop and remove everything including data
docker-compose down -v
```

---

## Next Steps

1. ✅ MongoDB running in Docker
2. ✅ Test database created with `setup_searchdb_docker.py`
3. ✅ Data exported with `mongodb_export.py`
4. ⏭️ Configure GraphRAG with `settings.yaml`
5. ⏭️ Run indexing with `graphrag index --root .`
6. ⏭️ Test with web UI `python app_example.py`

---

## Production Considerations

For production use with Docker:

1. **Use Docker Secrets** instead of environment variables
2. **Enable SSL/TLS** for MongoDB connections
3. **Use named volumes** for data persistence (already in your compose)
4. **Set resource limits** in docker-compose.yml
5. **Enable authentication** on all databases (already done)
6. **Regular backups** of MongoDB data

```yaml
# Example production additions
services:
  mongodb:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    command: mongod --auth --tlsMode requireTLS --tlsCertificateKeyFile /etc/ssl/mongodb.pem
```

---

## Summary

Your Docker setup is ready! The key differences from standard setup:

| Setting | Standard | Your Docker Setup |
|---------|----------|-------------------|
| Port | 27017 | **27018** |
| Auth | Optional | **Required (admin/password123)** |
| URI | `mongodb://localhost:27017/` | `mongodb://admin:password123@localhost:27018/` |
| Connection | Direct | **Through Docker bridge** |

All scripts in this directory now support your Docker configuration! 🚀
