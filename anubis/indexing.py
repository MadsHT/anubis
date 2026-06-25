"""
Document indexing pipeline for Anubis RAG Engine
Coordinates parsing, chunking, embedding, and storage
"""

import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from anubis.parser import DocumentParser, ParsedDocument
from anubis.chunker import SemanticChunker, Chunk
from anubis.embedder import EmbeddingClient
from anubis.database import Database, Document, DocumentChunk

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """
    End-to-end document indexing pipeline
    Parse → Chunk → Embed → Store
    """
    
    def __init__(self, parser: DocumentParser, chunker: SemanticChunker, 
                 embedder: EmbeddingClient, database: Database, config: Dict[str, Any]):
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.database = database
        self.config = config
        logger.info("DocumentIndexer initialized")
    
    async def index_document(self, file_path: str) -> Optional[str]:
        """
        Index a single document end-to-end
        Returns document ID on success, None on failure
        """
        try:
            logger.info(f"Starting indexing: {file_path}")
            
            # Step 1: Parse document
            logger.debug(f"Step 1: Parsing {file_path}")
            parsed_doc = await self.parser.parse(file_path)
            
            if not parsed_doc.chunks:
                logger.warning(f"No chunks extracted from {file_path}")
                return None
            
            # Step 2: Chunk content
            logger.debug(f"Step 2: Chunking {len(parsed_doc.chunks)} parsed chunks")
            chunks_to_embed = []
            for parsed_chunk in parsed_doc.chunks:
                # Chunk each parsed section
                chunks = self.chunker.chunk(
                    content=parsed_chunk.content,
                    chunk_type=parsed_chunk.chunk_type,
                    metadata={
                        "page_num": parsed_chunk.page_num,
                        "page_reference": parsed_chunk.page_reference,
                        **(parsed_chunk.metadata or {})
                    }
                )
                chunks_to_embed.extend(chunks)
            
            logger.debug(f"Generated {len(chunks_to_embed)} semantic chunks")
            
            # Step 3: Generate embeddings
            logger.debug(f"Step 3: Generating embeddings for {len(chunks_to_embed)} chunks")
            texts = [chunk.content for chunk in chunks_to_embed]
            embeddings = await self.embedder.embed_batch(texts)
            
            # Step 4: Store in database
            logger.debug(f"Step 4: Storing document and {len(chunks_to_embed)} chunks in database")
            doc_id = await self._store_document(parsed_doc, chunks_to_embed, embeddings)
            
            logger.info(f"Successfully indexed {file_path} (ID: {doc_id})")
            return doc_id
            
        except Exception as e:
            logger.error(f"Indexing failed for {file_path}: {e}")
            return None
    
    async def _store_document(self, parsed_doc: ParsedDocument, chunks: List[Chunk], 
                             embeddings: List[Optional[List[float]]]) -> str:
        """
        Store document metadata and chunks with embeddings to database
        """
        # Store document metadata
        doc_id = await self.database.store_document(
            file_path=parsed_doc.file_path,
            title=parsed_doc.title,
            metadata=parsed_doc.metadata
        )
        
        # Prepare chunks for batch storage
        chunks_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if embedding is None:
                logger.warning(f"Skipping chunk {i}: no embedding generated")
                continue
            
            chunks_data.append({
                "index": i,
                "content": chunk.content,
                "embedding": embedding,
                "type": chunk.chunk_type,
                "page_num": chunk.page_num,
                "page_reference": chunk.page_reference,
                "metadata": chunk.metadata
            })
        
        # Store all chunks
        await self.database.store_chunks(doc_id, chunks_data)
        
        logger.debug(f"Stored document {doc_id} with {len(chunks_data)} chunks")
        return doc_id
    
    async def index_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        Index all PDFs in a folder
        Returns summary of indexing results
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"Not a directory: {folder_path}")
        
        pdf_files = list(folder.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDFs to index")
        
        results = {
            "total": len(pdf_files),
            "successful": 0,
            "failed": 0,
            "doc_ids": []
        }
        
        for pdf_file in pdf_files:
            doc_id = await self.index_document(str(pdf_file))
            if doc_id:
                results["successful"] += 1
                results["doc_ids"].append(doc_id)
            else:
                results["failed"] += 1
        
        logger.info(f"Folder indexing complete: {results['successful']}/{results['total']} successful")
        return results
