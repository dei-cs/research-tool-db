# Research Tool Vector Database Service

Vector database service using **ChromaDB (in-memory)** for semantic search capabilities in the Research Tool application.

## Overview

This service provides a REST API for:
- Document ingestion with automatic embedding generation
- Semantic search using vector similarity
- Collection management
- Metadata filtering

## Features

- ✅ **In-memory ChromaDB** - Fast, no persistence needed for development
- ✅ **Automatic embeddings** - ChromaDB handles embedding generation
- ✅ **REST API** - FastAPI with full OpenAPI documentation
- ✅ **Bearer authentication** - API key protection
- ✅ **Collection management** - Multiple isolated document collections
- ✅ **Metadata filtering** - Query documents by metadata
- ✅ **Docker ready** - Containerized deployment

## Architecture

```
research-tool-api → research-tool-db (ChromaDB)
                    ↓
                    Semantic Search
                    ↓
                    Return relevant documents
```

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Navigate to the service directory
cd research-tool-db

# Copy environment file
cp .env.example .env

# Edit .env and set your API key
# VECTORDB_API_KEY=your-secure-key

# Start the service
docker-compose up -d

# Check health
curl http://localhost:8003/health
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export VECTORDB_API_KEY=dev-vectordb-key-12345

# Run the service
uvicorn src.api.app:app --reload --port 8003
```

## API Endpoints

### Health Check

```bash
GET /health
```

### Collection Management

```bash
# Create collection
POST /collections/{collection_name}
Headers: X-API-Key: your-api-key

# List all collections
GET /collections
Headers: X-API-Key: your-api-key

# Delete collection
DELETE /collections/{collection_name}
Headers: X-API-Key: your-api-key

# Get collection count
GET /collections/{collection_name}/count
Headers: X-API-Key: your-api-key
```

### Document Operations

```bash
# Ingest documents
POST /ingest
Headers: 
  X-API-Key: your-api-key
  Content-Type: application/json
Body:
{
  "collection_name": "documents",
  "documents": [
    {
      "id": "doc1",
      "text": "This is a sample document about machine learning.",
      "metadata": {"source": "arxiv", "author": "John Doe"}
    }
  ]
}

# Query documents (semantic search)
POST /query
Headers:
  X-API-Key: your-api-key
  Content-Type: application/json
Body:
{
  "query_text": "machine learning algorithms",
  "n_results": 5,
  "collection_name": "documents",
  "where": {"source": "arxiv"}
}

# Delete document
DELETE /documents/{document_id}?collection_name=documents
Headers: X-API-Key: your-api-key
```

### Database Management

```bash
# Reset entire database (CAUTION: deletes all data)
POST /reset
Headers: X-API-Key: your-api-key
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VECTORDB_API_KEY` | API key for authentication | `dev-vectordb-key-12345` |
| `DEFAULT_COLLECTION` | Default collection name | `documents` |

### Port

- Service runs on port **8003**

## Usage Examples

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8003"
API_KEY = "your-api-key"
headers = {"X-API-Key": API_KEY}

# Ingest documents
response = requests.post(
    f"{BASE_URL}/ingest",
    json={
        "collection_name": "papers",
        "documents": [
            {
                "id": "paper1",
                "text": "Deep learning is a subset of machine learning...",
                "metadata": {"year": 2023, "category": "AI"}
            }
        ]
    },
    headers=headers
)
print(response.json())

# Query documents
response = requests.post(
    f"{BASE_URL}/query",
    json={
        "query_text": "neural networks",
        "n_results": 3,
        "collection_name": "papers"
    },
    headers=headers
)
print(response.json())
```

### cURL Examples

```bash
# Ingest a document
curl -X POST http://localhost:8003/ingest \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "documents",
    "documents": [
      {
        "id": "doc1",
        "text": "Sample document about AI",
        "metadata": {"source": "test"}
      }
    ]
  }'

# Search documents
curl -X POST http://localhost:8003/query \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "artificial intelligence",
    "n_results": 5,
    "collection_name": "documents"
  }'
```

## Integration with Research Tool API

To integrate with `research-tool-api`:

1. **Add environment variable** to `research-tool-api`:
   ```bash
   VECTORDB_URL=http://localhost:8003
   VECTORDB_API_KEY=your-api-key
   ```

2. **Create VectorDB client** in `research-tool-api/src/vectordb_client.py`:
   ```python
   import requests
   from config import settings
   
   class VectorDBClient:
       def __init__(self):
           self.base_url = settings.VECTORDB_URL
           self.headers = {"X-API-Key": settings.VECTORDB_API_KEY}
       
       def query(self, query_text: str, n_results: int = 5):
           response = requests.post(
               f"{self.base_url}/query",
               json={
                   "query_text": query_text,
                   "n_results": n_results
               },
               headers=self.headers
           )
           return response.json()
   ```

3. **Use in routes** for RAG functionality

## Development

### Project Structure

```
research-tool-db/
├── src/
│   ├── __init__.py
│   └── api/
│       ├── __init__.py
│       └── app.py              # Main FastAPI application
├── Dockerfile                  # Docker container definition
├── compose.yml                 # Docker Compose configuration
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

### Testing

```bash
# Check health
curl http://localhost:8003/health

# Test authentication
curl -X GET http://localhost:8003/collections \
  -H "X-API-Key: dev-vectordb-key-12345"
```

## In-Memory vs Persistent Storage

This implementation uses **in-memory ChromaDB**:

**Advantages:**
- ✅ Fast performance
- ✅ No disk I/O overhead
- ✅ Simple setup
- ✅ Perfect for development/testing

**Limitations:**
- ❌ Data lost on restart
- ❌ Not suitable for production
- ❌ Limited by RAM

**For production**, modify `app.py`:

```python
# Change from in-memory:
chroma_client = chromadb.Client(Settings(
    anonymized_telemetry=False,
    allow_reset=True,
))

# To persistent:
chroma_client = chromadb.PersistentClient(path="/app/chroma_data")
```

Then update `Dockerfile` to add volume mount:

```yaml
volumes:
  - ./chroma_data:/app/chroma_data
```

## Monitoring

View logs:
```bash
docker-compose logs -f vectordb
```

Check container status:
```bash
docker-compose ps
```

## Troubleshooting

### Service won't start
- Check if port 8003 is available
- Verify Docker is running
- Check logs: `docker-compose logs vectordb`

### Authentication errors
- Verify API key matches in `.env`
- Check `X-API-Key` header is set correctly

### No results from queries
- Verify documents were ingested successfully
- Check collection name matches
- Try with `n_results` higher value

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8003/docs
- **ReDoc**: http://localhost:8003/redoc

## License

Part of the Research Tool project.
