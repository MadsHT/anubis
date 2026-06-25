# Anubis RAG Engine Test Suite

Comprehensive test coverage for all Anubis components.

## Running Tests

### All tests
```bash
pytest
```

### By category
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Parser tests
pytest -m parser

# With coverage report
pytest --cov=anubis --cov-report=html
```

### Async tests
```bash
# Run only async tests
pytest -m asyncio

# Run excluding async tests
pytest -m "not asyncio"
```

### Verbose output
```bash
pytest -v -s  # -s shows print statements
```

## Test Structure

```
tests/
├── conftest.py           # Pytest configuration and fixtures
├── __init__.py
└── test_anubis.py        # Main test file (12+ test classes)

Test Classes:
- TestDocumentParser      # PDF parsing with Docling
- TestSemanticChunker     # Chunk logic and boundaries
- TestEmbeddingClient     # Ollama embeddings client
- TestDocumentIndexer     # End-to-end indexing pipeline
- TestQueryProcessor      # Semantic search and ranking
- TestMCPServer           # MCP tool interface
- TestFastAPIIntegration  # HTTP endpoint tests
```

## Key Test Coverage

### Unit Tests
- **Parser:** Initialization, PDF parsing, metadata extraction
- **Chunker:** Chunk size limits, structure preservation, heading detection
- **Embedder:** Ollama connectivity, vector generation, batch processing, failure handling
- **Indexer:** Document indexing, chunk storage, error recovery
- **Query Processor:** Semantic search, similarity filtering, result formatting
- **MCP Server:** Tool definitions, parameter validation, response structure

### Integration Tests
- FastAPI `/health` endpoint
- FastAPI `/documents/index` endpoint with file upload
- FastAPI `/documents/query` endpoint with semantic search
- End-to-end indexing pipeline (parse → chunk → embed → store)
- End-to-end query pipeline (embed → search → format)

## Fixtures

```python
# Shared fixtures in conftest.py:
- event_loop           # Async event loop for async tests
- mock_pdf_path        # Temporary PDF file for testing
- test_config          # Mock configuration object
```

## Mocking Strategy

Tests use `unittest.mock` to mock external services:
- **Docling** — Mocked for fast unit tests (avoid actual PDF parsing)
- **Ollama** — Mocked HTTP responses (avoid container dependency)
- **PostgreSQL** — Mocked database queries (avoid real database)
- **File System** — Uses `tempfile` for isolated test files

This keeps tests **fast, isolated, and reproducible** without requiring services to be running.

## Coverage Goals

- Parser: 80%+ (complex Docling integration)
- Chunker: 90%+ (core logic, deterministic)
- Embedder: 75%+ (async HTTP, mocked)
- Indexer: 85%+ (pipeline orchestration)
- Query: 90%+ (search logic)
- MCP: 85%+ (tool interface)
- API: 70%+ (endpoints, some mocked)

## Running with Coverage

```bash
pytest --cov=anubis --cov-report=html
# Opens htmlcov/index.html
```

## Debugging Tests

```bash
# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s

# Run single test
pytest tests/test_anubis.py::TestDocumentParser::test_parser_initialization

# Verbose + full traceback
pytest -vv --tb=long
```

## Notes

- Tests marked `@pytest.mark.asyncio` run in async context
- Fixtures with `async` in the name are async fixtures
- Mock objects are used extensively to avoid external dependencies
- Test database is in-memory (not persisted) by default
- All tests should complete in <30s (pytest timeout setting)
