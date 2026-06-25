"""
Auto-indexing background task for Anubis RAG Engine
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class AutoIndexer:
    """Background auto-indexing service"""
    
    def __init__(self, database, config: Dict[str, Any]):
        self.database = database
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.indexed_files = {}  # Track file mtimes
    
    async def start(self):
        """Start the auto-indexer"""
        try:
            interval = self.config["auto_indexing"].get("interval_seconds", 300)
            self.scheduler.add_job(
                self._index_documents,
                'interval',
                seconds=interval,
                id='auto_index_job',
                name='Auto-index documents'
            )
            self.scheduler.start()
            self.is_running = True
            logger.info(f"Auto-indexer started (interval: {interval}s)")
        except Exception as e:
            logger.error(f"Failed to start auto-indexer: {e}")
            raise
    
    async def stop(self):
        """Stop the auto-indexer"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
            self.is_running = False
            logger.info("Auto-indexer stopped")
        except Exception as e:
            logger.error(f"Failed to stop auto-indexer: {e}")
    
    async def _index_documents(self):
        """Scan documents folder and index new/modified files"""
        try:
            documents_path = Path(self.config["document_processing"]["documents_path"])
            
            if not documents_path.exists():
                logger.warning(f"Documents path does not exist: {documents_path}")
                return
            
            # Scan for PDF files
            for pdf_file in documents_path.glob("*.pdf"):
                try:
                    mtime = os.path.getmtime(pdf_file)
                    
                    # Check if file is new or modified
                    if pdf_file.name not in self.indexed_files or self.indexed_files[pdf_file.name] < mtime:
                        logger.info(f"Detected new/modified file: {pdf_file.name}")
                        
                        # TODO: Trigger indexing
                        # await self._index_file(pdf_file)
                        
                        self.indexed_files[pdf_file.name] = mtime
                
                except Exception as e:
                    logger.error(f"Error processing {pdf_file.name}: {e}")
        
        except Exception as e:
            logger.error(f"Auto-indexing scan failed: {e}")
    
    async def _index_file(self, file_path: Path):
        """Index a single file (placeholder)"""
        try:
            logger.info(f"Indexing {file_path.name}...")
            # TODO: Implement actual indexing
            # This will call parser, chunker, embedder, and database
        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")
