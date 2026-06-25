"""
Database management and pgvector integration for Anubis RAG Engine
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text, Column, String, Integer, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

Base = declarative_base()

class DocumentChunk(Base):
    """Document chunk with embedding vector"""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(Vector(768), nullable=True, index=True)
    chunk_type = Column(String, default="text")  # text, table, image_caption
    page_num = Column(Integer)
    page_reference = Column(String)
    metadata_json = Column(String)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Document(Base):
    """Indexed document metadata"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(String, nullable=False, unique=True)
    title = Column(String)
    document_type = Column(String)
    file_size_bytes = Column(Integer)
    chunk_count = Column(Integer, default=0)
    metadata_json = Column(String)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Database:
    """Database connection and operations manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_url = config["database"]["url"]
        self.engine = None
        self.SessionLocal = None
    
    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            self.engine = create_engine(
                self.db_url,
                pool_size=self.config["database"].get("pool_size", 20),
                max_overflow=self.config["database"].get("max_overflow", 40),
                echo=self.config["database"].get("echo", False)
            )
            
            # Create tables
            Base.metadata.create_all(self.engine)
            
            # Create pgvector extension
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            
            # Create vector index for faster search
            with self.engine.connect() as conn:
                try:
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS ix_embedding_vector ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
                    ))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Could not create vector index: {e}")
            
            self.SessionLocal = sessionmaker(bind=self.engine)
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
    
    def get_session(self) -> Session:
        """Get a database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        session = self.get_session()
        try:
            doc = session.query(Document).filter(Document.id == document_id).first()
            if doc:
                return {
                    "id": doc.id,
                    "file_path": doc.file_path,
                    "title": doc.title,
                    "chunk_count": doc.chunk_count,
                    "created_at": doc.created_at.isoformat()
                }
            return None
        finally:
            session.close()
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents"""
        session = self.get_session()
        try:
            docs = session.query(Document).all()
            return [
                {
                    "document_id": doc.id,
                    "title": doc.title or doc.file_path,
                    "indexed_date": doc.created_at.isoformat(),
                    "chunks": doc.chunk_count,
                    "file_size_mb": doc.file_size_bytes / (1024 * 1024) if doc.file_size_bytes else 0
                }
                for doc in docs
            ]
        finally:
            session.close()
    
    async def store_document(self, file_path: str, title: str = None, metadata: Dict = None) -> str:
        """Store document metadata and return document_id"""
        session = self.get_session()
        try:
            doc = Document(
                file_path=file_path,
                title=title or file_path,
                metadata_json=str(metadata or {})
            )
            session.add(doc)
            session.commit()
            doc_id = doc.id
            session.refresh(doc)
            return doc_id
        finally:
            session.close()
    
    async def store_chunks(self, document_id: str, chunks: List[Dict[str, Any]]) -> int:
        """Store document chunks and return count"""
        session = self.get_session()
        try:
            for chunk in chunks:
                doc_chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk.get("index", 0),
                    content=chunk.get("content", ""),
                    embedding=chunk.get("embedding"),
                    chunk_type=chunk.get("type", "text"),
                    page_num=chunk.get("page_num"),
                    page_reference=chunk.get("page_reference"),
                    metadata_json=str(chunk.get("metadata", {}))
                )
                session.add(doc_chunk)
            
            session.commit()
            
            # Update chunk count
            doc = session.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.chunk_count = session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id
                ).count()
                session.commit()
            
            return len(chunks)
        finally:
            session.close()
    
    async def delete_document(self, document_id: str) -> int:
        """Delete document and its chunks, return chunk count removed"""
        session = self.get_session()
        try:
            # Get chunk count before deletion
            chunk_count = session.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).count()
            
            # Delete chunks
            session.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            
            # Delete document
            session.query(Document).filter(
                Document.id == document_id
            ).delete()
            
            session.commit()
            return chunk_count
        finally:
            session.close()
    
    async def search_vectors(self, embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        session = self.get_session()
        try:
            results = session.query(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.content,
                DocumentChunk.page_reference,
                DocumentChunk.chunk_type,
                DocumentChunk.metadata_json,
                (1 - (DocumentChunk.embedding.l2_distance(embedding))).label("score")
            ).order_by("score").limit(top_k).all()
            
            return [
                {
                    "chunk_id": r[0],
                    "document_id": r[1],
                    "content": r[2],
                    "page_reference": r[3],
                    "chunk_type": r[4],
                    "score": float(r[6]),
                    "metadata": r[5]
                }
                for r in results
            ]
        finally:
            session.close()
