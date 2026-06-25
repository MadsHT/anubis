"""
Anubis RAG Engine - Main FastAPI Server
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import sys
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import modules
try:
    from anubis.config import load_config
    from anubis.database import Database
    from anubis.indexer import AutoIndexer
    from anubis.parser import DocumentParser
    from anubis.chunker import SemanticChunker
    from anubis.embedder import EmbeddingClient
    from anubis.indexing import DocumentIndexer
    from anubis.mcp import MCPServer
    from anubis.query import QueryProcessor
    from anubis.fastmcp_adapter import create_mcp_server
except ImportError as e:
    logger.warning(f"Module import warning: {e}")

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    services: dict
    version: str = "0.1.0"

class IndexDocumentRequest(BaseModel):
    file_path: str
    metadata: Optional[dict] = None

class IndexDocumentResponse(BaseModel):
    status: str
    document_id: str
    chunks_created: int
    vectors_stored: int
    processing_time_ms: float

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    document_filter: Optional[List[str]] = None
    similarity_threshold: float = 0.0

class QueryResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    similarity_score: float
    page_reference: Optional[str] = None
    chunk_type: str = "text"
    metadata: Optional[dict] = None

class QueryResponse(BaseModel):
    results: List[dict]  # List of result dicts
    query_time_ms: float

class DocumentListResponse(BaseModel):
    documents: List[dict]

# Global state
app_state = {
    "database": None,
    "auto_indexer": None,
    "config": None,
    "parser": None,
    "chunker": None,
    "embedder": None,
    "document_indexer": None,
    "query_processor": None,
    "mcp_server": None,
    "fastmcp": None,
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown
    """
    # Startup
    logger.info("Starting Anubis RAG Engine...")
    try:
        app_state["config"] = load_config()
        app_state["database"] = Database(app_state["config"])
        await app_state["database"].initialize()
        logger.info("Database initialized")
        
        # Initialize processing pipeline
        app_state["parser"] = DocumentParser(app_state["config"])
        app_state["chunker"] = SemanticChunker(app_state["config"])
        app_state["embedder"] = EmbeddingClient(app_state["config"])
        
        # Check Ollama health
        embedder_ready = await app_state["embedder"].health_check()
        if not embedder_ready:
            logger.warning("Ollama not available, indexing will fail")
        else:
            logger.info("Ollama connected")
        
        # Initialize document indexer
        app_state["document_indexer"] = DocumentIndexer(
            parser=app_state["parser"],
            chunker=app_state["chunker"],
            embedder=app_state["embedder"],
            database=app_state["database"],
            config=app_state["config"]
        )
        logger.info("Document indexer initialized")
        
        app_state["auto_indexer"] = AutoIndexer(
            database=app_state["database"],
            config=app_state["config"]
        )
        await app_state["auto_indexer"].start()
        logger.info("Auto-indexer started")
        
        # Initialize query processor
        app_state["query_processor"] = QueryProcessor(
            database=app_state["database"],
            embedder=app_state["embedder"],
            config=app_state["config"]
        )
        logger.info("Query processor initialized")
        
        # Initialize MCP server
        app_state["mcp_server"] = MCPServer(
            document_indexer=app_state["document_indexer"],
            database=app_state["database"],
            embedder=app_state["embedder"],
            config=app_state["config"]
        )
        logger.info("MCP server initialized")
        
        # Initialize FastMCP adapter
        try:
            app_state["fastmcp"] = create_mcp_server(app_state["mcp_server"])
            logger.info("FastMCP adapter initialized")
        except Exception as e:
            logger.warning(f"FastMCP initialization failed (optional): {e}")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Anubis RAG Engine...")
    try:
        if app_state["auto_indexer"]:
            await app_state["auto_indexer"].stop()
        if app_state["database"]:
            await app_state["database"].close()
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="Anubis RAG Engine",
    description="Self-hosted document RAG with vision-aware parsing",
    version="0.1.0",
    lifespan=lifespan
)

# Routes

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    """
    services = {
        "database": "unknown",
        "ollama": "unknown",
        "auto_indexer": "unknown"
    }
    
    try:
        if app_state["database"]:
            services["database"] = "connected"
        else:
            services["database"] = "not_initialized"
    except Exception as e:
        services["database"] = f"error: {str(e)}"
    
    try:
        if app_state["auto_indexer"]:
            services["auto_indexer"] = "running" if app_state["auto_indexer"].is_running else "stopped"
        else:
            services["auto_indexer"] = "not_initialized"
    except Exception as e:
        services["auto_indexer"] = f"error: {str(e)}"
    
    try:
        if app_state["embedder"]:
            # Test Ollama connection using sync httpx
            try:
                with httpx.Client(timeout=5) as client:
                    response = client.get(
                        f"{app_state['embedder'].base_url}/api/tags"
                    )
                    if response.status_code == 200:
                        services["ollama"] = "ready"
                    else:
                        services["ollama"] = "unavailable"
            except Exception as e:
                services["ollama"] = f"error"
        else:
            services["ollama"] = "not_initialized"
    except Exception as e:
        services["ollama"] = f"error: {str(e)}"
    
    # Check if all critical services are healthy
    all_healthy = all(v in ["connected", "running", "ready"] for v in services.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        services=services
    )

@app.post("/documents/index", response_model=IndexDocumentResponse)
async def index_document(request: IndexDocumentRequest):
    """
    Index a single document end-to-end
    """
    import time
    start_time = time.time()
    
    try:
        if not app_state["document_indexer"]:
            raise HTTPException(status_code=503, detail="Indexer not initialized")
        
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
        
        logger.info(f"Indexing request: {request.file_path}")
        
        # Run indexing
        doc_id = await app_state["document_indexer"].index_document(request.file_path)
        
        if not doc_id:
            raise HTTPException(status_code=500, detail="Indexing failed: no document ID returned")
        
        # Get document info
        doc_info = await app_state["database"].get_document(doc_id)
        chunks_created = doc_info.get("chunk_count", 0) if doc_info else 0
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Successfully indexed {request.file_path}: {doc_id} ({chunks_created} chunks in {elapsed_ms:.0f}ms)")
        
        return IndexDocumentResponse(
            status="indexed",
            document_id=doc_id,
            chunks_created=chunks_created,
            vectors_stored=chunks_created,
            processing_time_ms=elapsed_ms
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query indexed documents using semantic search
    """
    import time
    start_time = time.time()
    
    try:
        if not request.query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not app_state["query_processor"]:
            raise HTTPException(status_code=503, detail="Query processor not initialized")
        
        logger.info(f"Query: {request.query}")
        
        # Execute search
        results = await app_state["query_processor"].search(
            query_text=request.query,
            top_k=request.top_k or 5,
            document_filter=request.document_filter,
            similarity_threshold=request.similarity_threshold or 0.0
        )
        
        # Convert to dicts
        result_dicts = [r.to_dict() for r in results]
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Query returned {len(results)} results in {elapsed_ms:.0f}ms")
        
        return QueryResponse(
            results=result_dicts,
            query_time_ms=elapsed_ms,
            result_count=len(results)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/list", response_model=DocumentListResponse)
async def list_documents():
    """
    List all indexed documents
    """
    try:
        # TODO: Implement document listing from database
        return DocumentListResponse(documents=[])
    except Exception as e:
        logger.error(f"Listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its embeddings
    """
    try:
        # TODO: Implement document deletion
        return {
            "status": "deleted",
            "document_id": document_id,
            "chunks_removed": 0
        }
    except Exception as e:
        logger.error(f"Deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Anubis RAG Engine",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)
