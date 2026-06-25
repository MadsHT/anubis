"""
Embedding generation with Ollama for Anubis RAG Engine
Uses nomic-embed-text-v1.5 for semantic embeddings
"""

import logging
import httpx
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)

class EmbeddingClient:
    """Generate embeddings via Ollama using nomic-embed-text-v1.5"""
    
    def __init__(self, config: dict):
        self.config = config
        self.base_url = config["ollama"]["base_url"]
        self.model = config["ollama"]["embedding_model"]
        self.timeout = config["ollama"].get("request_timeout", 300)
        self.batch_size = config.get("performance", {}).get("embedding_batch_size", 32)
        
        logger.info(f"EmbeddingClient initialized: {self.model} @ {self.base_url}")
    
    async def ensure_model_loaded(self) -> bool:
        """
        Ensure the embedding model is loaded in Ollama
        Pulls it if not present
        """
        try:
            if self.config["ollama"].get("pull_on_startup", True):
                logger.info(f"Checking if {self.model} is available...")
                await self.pull_model()
            return True
        except Exception as e:
            logger.error(f"Failed to ensure model: {e}")
            return False
    
    async def pull_model(self) -> bool:
        """
        Pull model from Ollama registry if not present
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Pulling {self.model}...")
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": self.model}
                ) as response:
                    async for line in response.aiter_lines():
                        # Log progress
                        if "status" in line:
                            logger.debug(f"Pull progress: {line[:100]}")
                
                if response.status_code == 200:
                    logger.info(f"Model {self.model} ready")
                    return True
                else:
                    logger.error(f"Pull failed with status {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Model pull error: {e}")
            return False
    
    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            768-dimensional embedding vector or None on error
        """
        try:
            if not text or not text.strip():
                return None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embed",
                    json={
                        "model": self.model,
                        "input": text
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings:
                        return embeddings[0]
                else:
                    logger.error(f"Embedding failed: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None
    
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts efficiently
        Uses batching to reduce overhead
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors (or None for failed items)
        """
        results = [None] * len(texts)
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i+self.batch_size]
            
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/embed",
                        json={
                            "model": self.model,
                            "input": batch
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        embeddings = data.get("embeddings", [])
                        
                        # Map embeddings back to original indices
                        for j, emb in enumerate(embeddings):
                            results[i + j] = emb
                    else:
                        logger.error(f"Batch embedding failed: {response.status_code}")
            
            except Exception as e:
                logger.error(f"Batch embedding error: {e}")
        
        logger.debug(f"Embedded {len([r for r in results if r])} of {len(texts)} texts")
        return results
    
    async def health_check(self) -> bool:
        """
        Check if Ollama is healthy and accessible
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
