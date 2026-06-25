# Anubis RAG Engine - Deployment Guide

## Quick Start with Docker Compose

### Prerequisites
- Docker & Docker Compose installed
- 4GB+ RAM available
- 20GB+ storage for models and database

### Deployment Steps

1. **Clone or download the repository**
   ```bash
   git clone https://github.com/MadsHT/anubis.git
   cd anubis
   ```

2. **Set up environment variables** (optional, uses defaults otherwise)
   ```bash
   cp .env.example .env
   # Edit .env and set DB_USER, DB_PASSWORD, DB_NAME if desired
   ```

3. **Start the stack**
   ```bash
   docker-compose up -d
   ```
   
   This will:
   - Build the Anubis FastAPI application
   - Start PostgreSQL with pgvector extension
   - Start Ollama for embeddings
   - Create all necessary volumes

4. **Verify services are running**
   ```bash
   docker-compose ps
   docker-compose logs rag-server
   ```

5. **Pull embedding model into Ollama** (one-time setup)
   ```bash
   docker exec anubis-ollama ollama pull nomic-embed-text-v1.5
   ```

### Accessing the Services

- **Anubis API**: http://localhost:8000
  - Health check: http://localhost:8000/health
  - API docs: http://localhost:8000/docs

- **Ollama API**: http://localhost:11434
  - List models: http://localhost:11434/api/tags

- **PostgreSQL**: localhost:5432
  - User: `anubis_user` (or `$DB_USER`)
  - Password: `anubis_password` (or `$DB_PASSWORD`)
  - Database: `anubis_db` (or `$DB_NAME`)

### Configuration

The Anubis service reads `config.yaml` at startup. To customize:

1. Edit `config.yaml` in the repo
2. Rebuild the container: `docker-compose build --no-cache rag-server`
3. Restart: `docker-compose restart rag-server`

Key configurable settings:
- `chunking.target_tokens`: Token size for document chunks (default 400)
- `performance.vector_search_threshold`: Relevance threshold for results (default 0.3)
- `auto_indexing.interval_seconds`: How often to scan for new documents (default 300s)

### Adding Documents

1. Copy PDF files to the documents volume:
   ```bash
   docker exec -it anubis-rag-server bash
   # Then copy files to /documents
   ```

   Or, if you have a local path mounted:
   ```bash
   cp your-document.pdf ./documents/
   ```

2. Anubis will automatically index new documents based on `auto_indexing.interval_seconds`

### Querying Documents

Via API:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "your question here", "top_k": 3}'
```

### Stopping the Stack

```bash
docker-compose down
```

To also remove volumes (WARNING: deletes data):
```bash
docker-compose down -v
```

### Troubleshooting

**Ollama model not loading:**
```bash
docker logs anubis-ollama
docker exec anubis-ollama ollama pull nomic-embed-text-v1.5
```

**Database connection errors:**
```bash
docker logs anubis-postgres
# Check password and DB_USER/DB_PASSWORD env vars match
```

**No documents being indexed:**
```bash
docker exec anubis-rag-server tail -f /app/logs/anubis.log
# Check /documents volume exists and is writable
```

### Portainer Deployment

1. In Portainer, go to **Stacks** → **Add Stack**
2. Paste the content of `docker-compose.yml`
3. Set environment variables in the **Env** section:
   - `DB_USER=anubis_user`
   - `DB_PASSWORD=your-secure-password`
   - `DB_NAME=anubis_db`
4. Deploy
5. Once running, manually pull the embedding model:
   ```bash
   docker exec anubis-ollama ollama pull nomic-embed-text-v1.5
   ```

### Next Steps

- Load documents into the `/documents` volume
- Test queries via the API
- Integrate with Hermes MCP server for vault integration
- Monitor logs and performance

---

For issues or questions, see the main README.md or open an issue on GitHub.
