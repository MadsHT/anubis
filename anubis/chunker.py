"""
Semantic chunking logic for Anubis RAG Engine
Splits documents intelligently respecting logical boundaries
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import nltk
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

# Download NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

@dataclass
class Chunk:
    """Represents a semantic chunk"""
    index: int
    content: str
    chunk_type: str  # "text", "table", "image_caption"
    token_count: int
    page_num: Optional[int] = None
    page_reference: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SemanticChunker:
    """
    Split documents into semantic chunks using NLTK sentence splitting
    Preserves tables, respects heading hierarchy, avoids splitting mid-sentence
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.target_tokens = config.get("chunking", {}).get("target_tokens", 400)
        self.overlap_tokens = config.get("chunking", {}).get("overlap_tokens", 50)
        self.preserve_tables = config.get("chunking", {}).get("preserve_tables", True)
        logger.info(f"SemanticChunker initialized (target: {self.target_tokens} tokens, overlap: {self.overlap_tokens})")
    
    def chunk(self, content: str, chunk_type: str = "text", metadata: Optional[Dict] = None) -> List[Chunk]:
        """
        Split content into semantic chunks
        
        Args:
            content: Text to chunk
            chunk_type: Type of content ("text", "table", "image_caption")
            metadata: Additional metadata (page_num, page_reference, etc.)
            
        Returns:
            List of Chunk objects
        """
        try:
            if chunk_type == "table":
                # Tables should not be split
                return [Chunk(
                    index=0,
                    content=content,
                    chunk_type="table",
                    token_count=self._count_tokens(content),
                    page_num=metadata.get("page_num") if metadata else None,
                    page_reference=metadata.get("page_reference") if metadata else None,
                    metadata=metadata
                )]
            
            # For text content, use semantic splitting
            return self._split_text_semantic(content, metadata)
            
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            # Fallback: return entire content as single chunk
            return [Chunk(
                index=0,
                content=content,
                chunk_type=chunk_type,
                token_count=self._count_tokens(content),
                metadata={**(metadata or {}), "chunking_error": str(e)}
            )]
    
    def _split_text_semantic(self, text: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """
        Split text into semantic chunks using sentence boundaries
        """
        chunks = []
        
        # Split into sentences
        sentences = sent_tokenize(text)
        
        if not sentences:
            return [Chunk(
                index=0,
                content=text,
                chunk_type="text",
                token_count=self._count_tokens(text),
                page_num=metadata.get("page_num") if metadata else None,
                page_reference=metadata.get("page_reference") if metadata else None,
                metadata=metadata
            )]
        
        # Group sentences into chunks based on token count
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            
            # Check if adding this sentence would exceed target
            if current_tokens + sentence_tokens > self.target_tokens and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk).strip()
                chunks.append(Chunk(
                    index=chunk_index,
                    content=chunk_text,
                    chunk_type="text",
                    token_count=current_tokens,
                    page_num=metadata.get("page_num") if metadata else None,
                    page_reference=metadata.get("page_reference") if metadata else None,
                    metadata=metadata
                ))
                
                chunk_index += 1
                
                # Start new chunk with overlap
                # Keep last sentence(s) from previous chunk for context
                overlap_sentences = []
                overlap_tokens = 0
                for prev_sent in reversed(current_chunk):
                    prev_tokens = self._count_tokens(prev_sent)
                    if overlap_tokens + prev_tokens <= self.overlap_tokens:
                        overlap_sentences.insert(0, prev_sent)
                        overlap_tokens += prev_tokens
                    else:
                        break
                
                current_chunk = overlap_sentences + [sentence]
                current_tokens = overlap_tokens + sentence_tokens
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Save final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            chunks.append(Chunk(
                index=chunk_index,
                content=chunk_text,
                chunk_type="text",
                token_count=current_tokens,
                page_num=metadata.get("page_num") if metadata else None,
                page_reference=metadata.get("page_reference") if metadata else None,
                metadata=metadata
            ))
        
        return chunks
    
    def _count_tokens(self, text: str) -> int:
        """
        Estimate token count using simple word-based heuristic
        (Production would use actual tokenizer like tiktoken)
        """
        # Simple heuristic: ~1.3 tokens per word on average
        words = text.split()
        return int(len(words) * 1.3)
    
    def batch_chunk(self, chunks_with_metadata: List[tuple]) -> List[Chunk]:
        """
        Chunk multiple items efficiently
        
        Args:
            chunks_with_metadata: List of (content, chunk_type, metadata) tuples
            
        Returns:
            Flattened list of all chunks
        """
        all_chunks = []
        
        for content, chunk_type, metadata in chunks_with_metadata:
            chunks = self.chunk(content, chunk_type, metadata)
            all_chunks.extend(chunks)
        
        logger.info(f"Batch chunking: {len(chunks_with_metadata)} items → {len(all_chunks)} chunks")
        return all_chunks
