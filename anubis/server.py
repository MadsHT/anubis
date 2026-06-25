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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import modules (will implement in subsequent steps)
try:
    from anubis.config import load_config
    from anubis.database import Database
    from anubis.indexer import AutoIndexer
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
    top_k: int = 3
    include_scores: bool = True
    document_filter: Optional[List[str]] = None

class QueryResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    score: float
    page_reference: Optional[str] = None
    metadata: Optional[dict] = None

class QueryResponse(BaseModel):
    results: List[QueryResult]
    query_time_ms: float

class DocumentListResponse(BaseModel):
    documents: List[dict]

# Global state
app_state = {
    "database": None,
    "auto_indexer": None,
    "config": None,
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
        
        app_state["auto_indexer"] = AutoIndexer(
            database=app_state["database"],
            config=app_state["config"]
        )
        await app_state["auto_indexer"].start()
        logger.info("Auto-indexer started")
        
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
    
    # Check if all critical services are healthy
    all_healthy = all(v in ["connected", "running"] for v in services.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        services=services
    )

@app.post("/documents/index", response_model=IndexDocumentResponse)
async def index_document(request: IndexDocumentRequest):
    """
    Index a single document
    """
    try:
        if not os.path.exists(request.file_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {request.file_path}"
            )
        
        # TODO: Implement actual indexing logic
        # This will call the parser, chunker, embedder, and database
        
        return IndexDocumentResponse(
            status="indexed",
            document_id="doc_placeholder",
            chunks_created=0,
            vectors_stored=0,
            processing_time_ms=0.0
        )
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query indexed documents
    """
    try:
        if not request.query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # TODO: Implement actual query logic
        # This will call the embedder, database vector search, and result formatting
        
        return QueryResponse(
            results=[],
            query_time_ms=0.0
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
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
