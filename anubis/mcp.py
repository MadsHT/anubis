"""
MCP Server implementation for Anubis RAG Engine
Provides Hermes integration via Model Context Protocol
"""

import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import json

logger = logging.getLogger(__name__)

class MCPServer:
    """
    MCP Server exposing Anubis RAG capabilities to Hermes
    """
    
    def __init__(self, document_indexer, database, embedder, config):
        self.indexer = document_indexer
        self.database = database
        self.embedder = embedder
        self.config = config
        self.tools = self._define_tools()
        logger.info("MCPServer initialized")
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """
        Define MCP tools exposed to Hermes
        """
        return [
            {
                "name": "anubis_query",
                "description": "Search indexed documents using semantic similarity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query (e.g., 'How does the Lancer mech system work?')"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 5, max: 20)",
                            "default": 5
                        },
                        "document_filter": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of document IDs to search within"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "anubis_list_documents",
                "description": "List all indexed documents",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "anubis_index_document",
                "description": "Index a new document for RAG",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to PDF file"
                        },
                        "title": {
                            "type": "string",
                            "description": "Optional document title"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "anubis_document_info",
                "description": "Get detailed information about an indexed document",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "Document ID"
                        }
                    },
                    "required": ["document_id"]
                }
            }
        ]
    
    async def query(self, query_text: str, top_k: int = 5, 
                   document_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Execute semantic search against indexed documents
        """
        try:
            logger.info(f"Query: {query_text} (top_k={top_k})")
            
            # Generate embedding for query
            query_embedding = await self.embedder.embed(query_text)
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Vector search
            results = await self.database.search_vectors(query_embedding, top_k=min(top_k, 20))
            
            # Apply document filter if provided
            if document_filter:
                results = [r for r in results if r.get("document_id") in document_filter]
                results = results[:top_k]
            
            logger.info(f"Found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all indexed documents
        """
        try:
            return await self.database.list_documents()
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    async def index_document(self, file_path: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Index a new document
        """
        try:
            doc_id = await self.indexer.index_document(file_path)
            if not doc_id:
                return {"status": "error", "message": "Indexing failed"}
            
            doc_info = await self.database.get_document(doc_id)
            return {
                "status": "success",
                "document_id": doc_id,
                "document_info": doc_info
            }
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed document information
        """
        try:
            return await self.database.get_document(document_id)
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            return None
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Return list of available MCP tools
        """
        return self.tools
