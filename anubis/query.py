"""
Query processing for Anubis RAG Engine
Handles semantic search and result formatting
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Single query result"""
    chunk_id: str
    document_id: str
    content: str
    similarity_score: float
    page_reference: Optional[str] = None
    chunk_type: str = "text"
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "similarity_score": self.similarity_score,
            "page_reference": self.page_reference,
            "chunk_type": self.chunk_type,
            "metadata": self.metadata
        }

class QueryProcessor:
    """
    Process queries against indexed documents
    """
    
    def __init__(self, database, embedder, config):
        self.database = database
        self.embedder = embedder
        self.config = config
        logger.info("QueryProcessor initialized")
    
    async def search(self, query_text: str, top_k: int = 5,
                    document_filter: Optional[List[str]] = None,
                    similarity_threshold: float = 0.0) -> List[QueryResult]:
        """
        Execute semantic search
        
        Args:
            query_text: Natural language query
            top_k: Number of results to return
            document_filter: Optional list of document IDs to restrict search
            similarity_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of QueryResult objects
        """
        try:
            logger.info(f"Processing query: '{query_text}'")
            
            # Generate query embedding
            query_embedding = await self.embedder.embed(query_text)
            if not query_embedding:
                logger.error("Failed to embed query")
                return []
            
            logger.debug(f"Query embedding generated (dim={len(query_embedding)})")
            
            # Vector search
            raw_results = await self.database.search_vectors(
                query_embedding,
                top_k=min(top_k * 2, 50)  # Get extra for filtering
            )
            
            if not raw_results:
                logger.info("No results found")
                return []
            
            # Convert to QueryResult objects
            results = []
            for raw in raw_results:
                # Apply similarity threshold
                score = raw.get("score", 0.0)
                if score < similarity_threshold:
                    continue
                
                result = QueryResult(
                    chunk_id=raw.get("chunk_id"),
                    document_id=raw.get("document_id"),
                    content=raw.get("content"),
                    similarity_score=score,
                    page_reference=raw.get("page_reference"),
                    chunk_type=raw.get("chunk_type", "text"),
                    metadata=raw.get("metadata")
                )
                results.append(result)
            
            # Apply document filter
            if document_filter:
                results = [r for r in results if r.document_id in document_filter]
            
            # Return top_k
            results = results[:top_k]
            
            logger.info(f"Returning {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            return []
    
    async def search_by_document(self, document_id: str, query_text: str,
                                top_k: int = 5) -> List[QueryResult]:
        """
        Search within a specific document only
        """
        return await self.search(query_text, top_k=top_k, document_filter=[document_id])
    
    def format_results_for_context(self, results: List[QueryResult]) -> str:
        """
        Format query results as context for LLM
        """
        if not results:
            return "No results found."
        
        lines = []
        for i, result in enumerate(results, 1):
            header = f"Result {i} (similarity: {result.similarity_score:.2%})"
            if result.page_reference:
                header += f" - Page {result.page_reference}"
            lines.append(f"## {header}")
            lines.append(result.content)
            lines.append("")
        
        return "\n".join(lines)
