-- Initialize pgvector extension for Anubis RAG Engine
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tables if not using SQLAlchemy
-- (SQLAlchemy will handle this on app startup, but having it here as reference)

-- Document metadata table
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR PRIMARY KEY,
    file_path VARCHAR NOT NULL UNIQUE,
    title VARCHAR,
    document_type VARCHAR,
    file_size_bytes INTEGER,
    chunk_count INTEGER DEFAULT 0,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Document chunks with embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    chunk_type VARCHAR DEFAULT 'text',
    page_num INTEGER,
    page_reference VARCHAR,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS ix_documents_file_path ON documents(file_path);

-- Vector similarity search index (created with IVFFLAT for efficiency)
-- This will be created by the app on startup
-- CREATE INDEX IF NOT EXISTS ix_embedding_vector ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
