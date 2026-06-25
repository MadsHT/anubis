"""
FastMCP server for Anubis RAG Engine
Implements Model Context Protocol for Hermes integration
"""

import logging
import os
from typing import Any
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

def create_mcp_server(mcp_handler) -> FastMCP:
    """
    Create FastMCP server with Anubis tools
    
    Args:
        mcp_handler: MCPServer instance with query/index methods
    
    Returns:
        FastMCP server instance
    """
    
    mcp = FastMCP("Anubis RAG Engine", "0.1.0")
    
    @mcp.tool()
    async def anubis_query(query: str, top_k: int = 5, 
                          document_filter: list = None) -> dict:
        """
        Search indexed documents using semantic similarity
        
        Args:
            query: Natural language query
            top_k: Number of results (max 20)
            document_filter: Optional document IDs to search within
        
        Returns:
            Dictionary with results and metadata
        """
        results = await mcp_handler.query(query, top_k=min(top_k, 20), 
                                          document_filter=document_filter)
        
        return {
            "status": "success",
            "query": query,
            "result_count": len(results),
            "results": results
        }
    
    @mcp.tool()
    async def anubis_list_documents() -> dict:
        """
        List all indexed documents
        
        Returns:
            Dictionary with document list and count
        """
        docs = await mcp_handler.list_documents()
        
        return {
            "status": "success",
            "document_count": len(docs),
            "documents": docs
        }
    
    @mcp.tool()
    async def anubis_index_document(file_path: str, title: str = None) -> dict:
        """
        Index a new document for RAG
        
        Args:
            file_path: Absolute path to PDF
            title: Optional document title
        
        Returns:
            Dictionary with indexing status
        """
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": f"File not found: {file_path}"
            }
        
        result = await mcp_handler.index_document(file_path, title=title)
        return result
    
    @mcp.tool()
    async def anubis_document_info(document_id: str) -> dict:
        """
        Get detailed information about an indexed document
        
        Args:
            document_id: Document ID
        
        Returns:
            Dictionary with document metadata
        """
        info = await mcp_handler.get_document_info(document_id)
        
        if not info:
            return {
                "status": "error",
                "message": f"Document not found: {document_id}"
            }
        
        return {
            "status": "success",
            "document": info
        }
    
    logger.info("FastMCP server created with 4 tools")
    return mcp
