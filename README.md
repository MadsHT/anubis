# Anubis: Self-Hosted Document RAG Engine

> **Note:** This project is **mostly AI-generated** using Claude AI as part of the development process.

## Overview

Anubis is a self-hosted Retrieval-Augmented Generation (RAG) engine designed to query personal documents with advanced table and image extraction capabilities. Built for rulebooks, technical manuals, and complex PDFs with embedded tables, diagrams, and non-standard layouts.

Unlike existing RAG tools that struggle with document structure, Anubis preserves semantic meaning through intelligent chunking and vision-aware parsing, making it ideal for querying knowledge-intensive documents.

## Key Features

- **Vision-Aware Document Parsing** — Extracts tables as structured data, preserves image context and captions
- **Semantic Chunking** — Intelligent document splitting respects logical breaks, section hierarchy, and table integrity
- **Self-Hosted** — No cloud dependencies beyond optional vision model fallback
- **Dual API** — Query via HTTP endpoints or MCP server for Hermes Agent integration
- **Auto-Indexing** — Background task automatically indexes new documents in a watched folder
- **Production-Ready** — Persistent storage, health checks, error recovery, graceful degradation

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Compose                           │
├──────────────────┬──────────────────────────┬──────────────────┤
│  rag-server      │   PostgreSQL + pgvector  │   Ollama          │
│  (FastAPI+MCP)   │   (Vector Database)      │   (Embeddings)    │
│                  │                          │                   │
│ • HTTP API       │ • Semantic vectors       │ • nomic-embed-    │
│ • MCP tools      │ • 768-dim embeddings     │   text-v1.5       │
│ • Auto-indexing  │ • Chunk metadata         │ • Local inference │
└──────────────────┴──────────────────────────┴──────────────────┘
        ↑                                              ↑
        │                                              │
   HTTP/MCP queries                           Document embeddings
```

## How It Works

### Document Ingestion Pipeline

1. **Document Detection** — New PDFs in `/documents` folder are detected by scheduler
2. **Parsing (Docling)** — Vision transformer extracts text, tables, images, and layout structure
3. **Semantic Chunking** — Documents split intelligently:
   - Respects heading hierarchy and section structure
   - Keeps tables and bullet points intact
   - Preserves page references and metadata
4. **Embedding** — Chunks converted to 768-dim vectors via Ollama embeddings
5. **Storage** — Vectors indexed in PostgreSQL with pgvector extension for fast retrieval

### Query Flow

1. **User Query** — Submitted via HTTP endpoint or MCP tool
2. **Query Embedding** — Query converted to same vector space as documents
3. **Semantic Search** — PostgreSQL pgvector finds top-K most similar chunks
4. **Result Enrichment** — Results augmented with page numbers, document titles, confidence scores
5. **Return to User** — Results ready for LLM reasoning or direct consumption

## Stack

| Component | Technology | Why |
|---|---|---|
| **Document Parsing** | Docling (IBM) | Vision transformer handles tables/images/complex layouts |
| **Embeddings** | nomic-embed-text-v1.5 + Ollama | Fast, local, best-in-class MTEB performance |
| **Vector Database** | PostgreSQL + pgvector | Production-ready, persistent, queryable |
| **API Server** | FastAPI + FastMCP | Single codebase for both HTTP and MCP protocols |
| **Vision Fallback** | Copilot API (pluggable) | For edge cases, fully optional |
| **Auto-Indexing** | APScheduler | 5-minute interval background task |
| **Deployment** | Docker Compose | Self-contained, reproducible, portable |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB+ RAM available
- 20GB+ disk space (for models + database)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/anubis.git
   cd anubis
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

   This starts:
   - FastAPI server on `localhost:8000`
   - PostgreSQL on `localhost:5432` (internal only)
   - Ollama on `localhost:11434` (internal only)

3. **Verify health**
   ```bash
   curl http://localhost:8000/health
   ```

### Usage

#### Index a Document

```bash
curl -X POST http://localhost:8000/documents/index \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/documents/rulebook.pdf",
    "metadata": {
      "title": "Example Rulebook",
      "type": "rulebook"
    }
  }'
```

#### Query Documents

```bash
curl -X POST http://localhost:8000/documents/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the rules for changing loadouts?",
    "top_k": 3
  }'
```

Response:
```json
{
  "results": [
    {
      "chunk_id": "chunk_abc123",
      "document_id": "doc_xyz789",
      "document_title": "Example Rulebook",
      "content": "Loadouts can be changed between missions...",
      "score": 0.92,
      "page_reference": "p. 45"
    }
  ],
  "query_time_ms": 45
}
```

#### List Indexed Documents

```bash
curl http://localhost:8000/documents/list
```

#### MCP Integration

Add to your Hermes Agent config (`~/.hermes/config/config.yaml`):

```yaml
mcp_servers:
  anubis:
    command: docker
    args: ["exec", "anubis-rag-server", "python", "-m", "anubis.mcp"]
```

Then query via Hermes:
```
You: What are the loadout rules in my documents?
Hermes: [calls Anubis MCP tool] → [reasons over results] → Here are the rules...
```

## API Reference

### Endpoints

#### `POST /documents/index`
Index a single document.

**Request:**
```json
{
  "file_path": "/documents/example.pdf",
  "metadata": {
    "title": "Optional Title",
    "type": "Optional Category",
    "version": "Optional Version"
  }
}
```

**Response:**
```json
{
  "status": "indexed",
  "document_id": "doc_abc123",
  "chunks_created": 247,
  "vectors_stored": 247,
  "processing_time_ms": 1234
}
```

#### `POST /documents/query`
Query indexed documents.

**Request:**
```json
{
  "query": "Your question here",
  "top_k": 3,
  "include_scores": true
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "chunk_001",
      "document_id": "doc_abc123",
      "document_title": "Example Rulebook",
      "content": "Relevant excerpt...",
      "score": 0.92,
      "page_reference": "p. 45",
      "metadata": {
        "chunk_type": "text"
      }
    }
  ],
  "query_time_ms": 45
}
```

#### `GET /documents/list`
List all indexed documents.

**Response:**
```json
{
  "documents": [
    {
      "document_id": "doc_abc123",
      "title": "Example Rulebook",
      "indexed_date": "2026-06-25T10:30:00Z",
      "chunks": 247,
      "file_size_mb": 12.5
    }
  ]
}
```

#### `DELETE /documents/{document_id}`
Remove a document and its embeddings.

**Response:**
```json
{
  "status": "deleted",
  "document_id": "doc_abc123",
  "chunks_removed": 247
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "ollama": "connected",
    "auto_indexer": "running"
  }
}
```

## Configuration

Edit `docker-compose.yml` to customize:

- **Embedding model:** Change `OLLAMA_MODELS` to use different embedding models
- **Auto-index interval:** Modify `APScheduler` settings in `config.yaml`
- **Chunk size:** Adjust `CHUNK_TARGET_TOKENS` (default: 300-500)
- **Vector DB:** PostgreSQL connection string via `DATABASE_URL`

## Performance

- **Index time:** ~2 min per 100 pages
- **Query latency (p50):** <100ms
- **Query latency (p99):** <500ms
- **Memory usage:** ~4GB total (Ollama + Postgres combined)
- **Disk usage:** ~20GB for models + database

## Limitations

- Single-node deployment (no distributed indexing)
- Vector-only search (no full-text fallback yet)
- No built-in access control (assumes single-user homelab)
- Chunk re-indexing updates all vectors (no partial updates)

## Future Enhancements

- [ ] BM25 hybrid search (text + vector combined)
- [ ] ColPali visual document search
- [ ] Document versioning and change tracking
- [ ] Citation links back to source PDFs
- [ ] Multi-language support
- [ ] Fine-tuned embedding models

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs -f

# Verify Docker Compose is working
docker-compose ps
```

### Slow queries
- Check PostgreSQL index creation: `docker exec anubis-postgres psql -U postgres -d rag_db -c '\di'`
- Monitor resource usage: `docker stats`

### Ollama connection errors
- Ensure Ollama service is healthy: `curl http://localhost:11434/api/tags`
- Check Ollama has models: `docker exec anubis-ollama ollama list`

### Out of memory
- Reduce Ollama model size or switch to smaller embedding model
- Increase container memory limits in `docker-compose.yml`

## Development

### Local Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run server locally
python -m anubis.server
```

### Project Structure
```
anubis/
├── docker-compose.yml       # Service orchestration
├── Dockerfile               # RAG server image
├── requirements.txt         # Python dependencies
├── anubis/
│   ├── __init__.py
│   ├── server.py           # FastAPI app
│   ├── mcp.py              # MCP server implementation
│   ├── parser.py           # Docling integration
│   ├── chunker.py          # Semantic chunking
│   ├── embedder.py         # Ollama embeddings
│   ├── database.py         # PostgreSQL + pgvector
│   ├── indexer.py          # Auto-indexing logic
│   └── config.py           # Configuration
├── tests/
├── docs/
└── README.md
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

## Support

- **Issues:** GitHub Issues for bugs and feature requests
- **Discussions:** GitHub Discussions for questions and ideas

---

**Built with self-hosted simplicity in mind. No cloud required.**
