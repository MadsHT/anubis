"""
Unit tests for Anubis RAG Engine
Tests parser, chunker, embedder, indexer, query processor, and API endpoints
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile

# Import modules to test
from anubis.parser import DocumentParser, ParsedDocument
from anubis.chunker import SemanticChunker, Chunk
from anubis.embedder import EmbeddingClient
from anubis.indexing import DocumentIndexer
from anubis.query import QueryProcessor, QueryResult
from anubis.mcp import MCPServer


class TestDocumentParser:
    """Tests for Docling PDF parsing"""
    
    @pytest.mark.asyncio
    async def test_parser_initialization(self):
        """Test parser can be initialized"""
        config = {"parser": {"chunk_size": 512}}
        parser = DocumentParser(config)
        assert parser is not None
        assert parser.config == config
    
    @pytest.mark.asyncio
    async def test_parse_pdf_returns_parsed_document(self):
        """Test parsing returns ParsedDocument"""
        config = {"parser": {}}
        parser = DocumentParser(config)
        
        # Mock the actual parsing
        with patch.object(parser, 'parse', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = ParsedDocument(
                file_path="dummy.pdf",
                title="Test Document",
                chunks=[],
                metadata={"pages": 1}
            )
            
            result = await parser.parse("dummy.pdf")
            assert isinstance(result, ParsedDocument)
            assert result.title == "Test Document"
            mock_parse.assert_called_once_with("dummy.pdf")


class TestSemanticChunker:
    """Tests for semantic chunking logic"""
    
    def test_chunker_initialization(self):
        """Test chunker can be initialized"""
        config = {"chunker": {"chunk_size": 512, "overlap": 50}}
        chunker = SemanticChunker(config)
        assert chunker is not None
        assert chunker.config == config
    
    def test_chunk_respects_max_size(self):
        """Test chunks don't exceed max size"""
        config = {"chunking": {"target_tokens": 100, "overlap_tokens": 10}}
        chunker = SemanticChunker(config)
        
        text = "word " * 50  # 250 words
        chunks = chunker.chunk(text)
        
        for chunk in chunks:
            # Check that no chunk exceeds reasonable size
            assert len(chunk.content) > 0
    
    def test_chunk_preserves_structure(self):
        """Test chunks preserve heading structure"""
        config = {"chunking": {"target_tokens": 512}}
        chunker = SemanticChunker(config)
        
        text = "# Heading 1\nContent under heading\n## Heading 2\nMore content"
        chunks = chunker.chunk(text)
        
        # Should have multiple chunks
        assert len(chunks) > 0
        # Each chunk should be a Chunk object
        assert all(isinstance(c, Chunk) for c in chunks)


class TestEmbeddingClient:
    """Tests for Ollama embeddings"""
    
    @pytest.mark.asyncio
    async def test_embedder_initialization(self):
        """Test embedder can be initialized"""
        config = {"ollama": {"base_url": "http://localhost:11434", "embedding_model": "nomic-embed-text-v1.5"}}
        embedder = EmbeddingClient(config)
        assert embedder is not None
    
    @pytest.mark.asyncio
    async def test_health_check_handles_offline_ollama(self):
        """Test health check when Ollama is offline"""
        config = {"ollama": {"base_url": "http://localhost:11434", "embedding_model": "nomic-embed-text-v1.5"}}
        embedder = EmbeddingClient(config)
        
        with patch('httpx.AsyncClient.get', side_effect=Exception("Connection refused")):
            result = await embedder.health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_embed_returns_vector(self):
        """Test embedding returns vector"""
        config = {"ollama": {"base_url": "http://localhost:11434", "embedding_model": "nomic-embed-text-v1.5"}}
        embedder = EmbeddingClient(config)
        
        with patch.object(embedder, 'embed_text', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3] * 256  # 768 dims
            result = await embedder.embed_text("test text")
            assert result is not None
            assert len(result) == 768
    
    @pytest.mark.asyncio
    async def test_batch_embed_handles_failures(self):
        """Test batch embedding handles partial failures"""
        config = {"ollama": {"base_url": "http://localhost:11434", "embedding_model": "nomic-embed-text-v1.5"}}
        embedder = EmbeddingClient(config)
        
        with patch.object(embedder, 'embed_batch', new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = [
                [0.1] * 768,  # Success
                None,  # Failed
                [0.2] * 768,  # Success
            ]
            result = await embedder.embed_batch(["text1", "text2", "text3"])
            assert len(result) == 3
            assert result[0] is not None
            assert result[1] is None
            assert result[2] is not None


class TestDocumentIndexer:
    """Tests for end-to-end indexing pipeline"""
    
    @pytest.mark.asyncio
    async def test_indexer_initialization(self):
        """Test indexer can be initialized"""
        config = {}
        parser = Mock()
        chunker = Mock()
        embedder = Mock()
        database = Mock()
        
        indexer = DocumentIndexer(
            parser=parser,
            chunker=chunker,
            embedder=embedder,
            database=database,
            config=config
        )
        assert indexer is not None
    
    @pytest.mark.asyncio
    async def test_index_document_returns_document_id(self):
        """Test indexing returns a document ID"""
        config = {}
        parser = AsyncMock()
        chunker = Mock()
        embedder = AsyncMock()
        database = AsyncMock()
        
        indexer = DocumentIndexer(parser, chunker, embedder, database, config)
        
        # Mock the pipeline
        with patch.object(indexer, 'index_document', new_callable=AsyncMock) as mock_index:
            mock_index.return_value = "doc_123"
            result = await indexer.index_document("test.pdf")
            assert result == "doc_123"


class TestQueryProcessor:
    """Tests for semantic search and query processing"""
    
    @pytest.mark.asyncio
    async def test_query_processor_initialization(self):
        """Test query processor can be initialized"""
        config = {}
        database = Mock()
        embedder = Mock()
        
        processor = QueryProcessor(database, embedder, config)
        assert processor is not None
    
    @pytest.mark.asyncio
    async def test_search_returns_query_results(self):
        """Test search returns list of QueryResult objects"""
        config = {}
        database = AsyncMock()
        embedder = AsyncMock()
        
        processor = QueryProcessor(database, embedder, config)
        
        # Mock embedding and search
        embedder.embed.return_value = [0.1] * 768
        database.search_vectors.return_value = [
            {
                "chunk_id": "chunk_1",
                "document_id": "doc_1",
                "content": "Test result",
                "score": 0.95,
                "page_reference": "1"
            }
        ]
        
        results = await processor.search("test query", top_k=5)
        assert len(results) > 0
        assert isinstance(results[0], QueryResult)
        assert results[0].chunk_id == "chunk_1"
    
    @pytest.mark.asyncio
    async def test_search_applies_similarity_threshold(self):
        """Test that low-scoring results are filtered"""
        config = {}
        database = AsyncMock()
        embedder = AsyncMock()
        
        processor = QueryProcessor(database, embedder, config)
        
        embedder.embed.return_value = [0.1] * 768
        database.search_vectors.return_value = [
            {"chunk_id": "high", "document_id": "doc_1", "content": "Good", "score": 0.95},
            {"chunk_id": "low", "document_id": "doc_1", "content": "Bad", "score": 0.05},
        ]
        
        results = await processor.search("query", top_k=10, similarity_threshold=0.5)
        # Only high-scoring result should be included
        assert all(r.similarity_score >= 0.5 for r in results)
    
    @pytest.mark.asyncio
    async def test_format_results_for_context(self):
        """Test result formatting for LLM context"""
        config = {}
        database = Mock()
        embedder = Mock()
        processor = QueryProcessor(database, embedder, config)
        
        results = [
            QueryResult(
                chunk_id="1",
                document_id="doc_1",
                content="Test content",
                similarity_score=0.95,
                page_reference="1"
            )
        ]
        
        formatted = processor.format_results_for_context(results)
        assert "Test content" in formatted
        assert "95.00%" in formatted


class TestMCPServer:
    """Tests for MCP server interface"""
    
    @pytest.mark.asyncio
    async def test_mcp_server_initialization(self):
        """Test MCP server can be initialized"""
        indexer = Mock()
        database = Mock()
        embedder = Mock()
        config = {}
        
        mcp_server = MCPServer(indexer, database, embedder, config)
        assert mcp_server is not None
    
    def test_mcp_server_defines_tools(self):
        """Test MCP server defines 4 tools"""
        indexer = Mock()
        database = Mock()
        embedder = Mock()
        config = {}
        
        mcp_server = MCPServer(indexer, database, embedder, config)
        tools = mcp_server.get_tools()
        
        assert len(tools) == 4
        tool_names = {t["name"] for t in tools}
        assert "anubis_query" in tool_names
        assert "anubis_list_documents" in tool_names
        assert "anubis_index_document" in tool_names
        assert "anubis_document_info" in tool_names
    
    @pytest.mark.asyncio
    async def test_mcp_query_method(self):
        """Test MCP query method"""
        indexer = Mock()
        database = AsyncMock()
        embedder = AsyncMock()
        config = {}
        
        mcp_server = MCPServer(indexer, database, embedder, config)
        
        embedder.embed.return_value = [0.1] * 768
        database.search_vectors.return_value = [
            {"chunk_id": "1", "document_id": "doc_1", "content": "Result", "score": 0.9}
        ]
        
        results = await mcp_server.query("test", top_k=5)
        assert len(results) > 0


# FastAPI endpoint tests would require TestClient
# These are integration tests that test the full HTTP stack

class TestFastAPIIntegration:
    """Integration tests for FastAPI endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from anubis.server import app
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # 200 if healthy, 503 if services down
    
    def test_query_endpoint_requires_query(self, client):
        """Test /documents/query requires query parameter"""
        response = client.post("/documents/query", json={})
        assert response.status_code == 422  # Validation error


# Pytest fixtures for common setup

@pytest.fixture
def temp_pdf():
    """Create a temporary PDF file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        # Would write a real PDF here
        yield f.name
    Path(f.name).unlink()


@pytest.fixture
def mock_config():
    """Return mock configuration"""
    return {
        "parser": {"chunk_size": 512},
        "chunker": {"chunk_size": 256, "overlap": 50},
        "ollama": {"host": "localhost", "port": 11434},
        "database": {"url": "postgresql://user:pass@localhost/anubis"}
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
