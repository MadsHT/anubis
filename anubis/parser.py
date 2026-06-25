"""
Document parsing with Docling for Anubis RAG Engine
Extracts text, tables, images, and structure from PDFs
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import ConversionStatus

logger = logging.getLogger(__name__)

@dataclass
class ParsedChunk:
    """Represents a parsed chunk from a document"""
    content: str
    chunk_type: str  # "text", "table", "image_caption"
    page_num: Optional[int] = None
    page_reference: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ParsedDocument:
    """Represents a fully parsed document"""
    file_path: str
    title: str
    chunks: List[ParsedChunk]
    total_pages: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentParser:
    """Parse PDFs and extract structure using Docling"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.converter = DocumentConverter()
        logger.info("DocumentParser initialized with Docling")
    
    async def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse a PDF document and extract all content
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ParsedDocument with extracted chunks
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not path.suffix.lower() == ".pdf":
                raise ValueError(f"Unsupported file type: {path.suffix}")
            
            logger.info(f"Parsing document: {path.name}")
            
            # Convert document using Docling
            result = self.converter.convert(file_path)
            
            if result.status != ConversionStatus.SUCCESS:
                raise RuntimeError(f"Conversion failed with status: {result.status}")
            
            # Extract chunks from converted document
            chunks = self._extract_chunks(result.document)
            
            parsed_doc = ParsedDocument(
                file_path=str(file_path),
                title=path.stem,
                chunks=chunks,
                total_pages=self._estimate_pages(result.document),
                metadata={
                    "file_size_bytes": path.stat().st_size,
                    "parser": "docling"
                }
            )
            
            logger.info(f"Parsed {path.name}: {len(chunks)} chunks extracted")
            return parsed_doc
            
        except Exception as e:
            logger.error(f"Parsing failed for {file_path}: {e}")
            raise
    
    def _extract_chunks(self, document) -> List[ParsedChunk]:
        """
        Extract chunks from Docling document
        Handles text, tables, and image captions
        """
        chunks = []
        
        try:
            # Get markdown representation (Docling outputs markdown with structure)
            markdown = document.export_to_markdown()
            
            # Parse markdown into structured chunks
            # Docling preserves tables as markdown tables, headings, etc.
            chunks = self._split_markdown_into_chunks(markdown)
            
            # Enhance chunks with page numbers if available
            chunks = self._add_page_references(chunks, document)
            
            return chunks
            
        except Exception as e:
            logger.warning(f"Error extracting chunks: {e}. Falling back to raw text.")
            # Fallback: return raw document text as single chunk
            try:
                text = document.export_to_text()
                return [ParsedChunk(
                    content=text,
                    chunk_type="text",
                    metadata={"extraction_method": "fallback"}
                )]
            except Exception as fallback_e:
                logger.error(f"Fallback extraction also failed: {fallback_e}")
                return []
    
    def _split_markdown_into_chunks(self, markdown: str) -> List[ParsedChunk]:
        """
        Split markdown content into semantic chunks
        Respects heading hierarchy and table boundaries
        """
        chunks = []
        lines = markdown.split("\n")
        
        current_chunk = []
        current_heading_level = 0
        current_chunk_type = "text"
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Detect headings
            if line.startswith("#"):
                # Save current chunk if it has content
                if current_chunk:
                    chunk_text = "\n".join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(ParsedChunk(
                            content=chunk_text,
                            chunk_type=current_chunk_type
                        ))
                    current_chunk = []
                
                # Start new chunk with heading
                current_heading_level = len(line) - len(line.lstrip("#"))
                current_chunk = [line]
                current_chunk_type = "text"
            
            # Detect table start
            elif line.strip().startswith("|"):
                # Save current chunk
                if current_chunk and not any(c.startswith("|") for c in current_chunk):
                    chunk_text = "\n".join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(ParsedChunk(
                            content=chunk_text,
                            chunk_type=current_chunk_type
                        ))
                    current_chunk = []
                
                # Collect full table
                table_lines = [line]
                i += 1
                while i < len(lines) and (lines[i].strip().startswith("|") or lines[i].strip() == ""):
                    table_lines.append(lines[i])
                    i += 1
                i -= 1
                
                table_text = "\n".join(table_lines).strip()
                if table_text:
                    chunks.append(ParsedChunk(
                        content=table_text,
                        chunk_type="table"
                    ))
                current_chunk = []
            
            # Regular content
            elif line.strip():
                current_chunk.append(line)
            
            # Empty line
            elif current_chunk and line.strip() == "":
                # Paragraph break - consider ending chunk if it's long enough
                if len("\n".join(current_chunk)) > 500:
                    chunk_text = "\n".join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(ParsedChunk(
                            content=chunk_text,
                            chunk_type=current_chunk_type
                        ))
                    current_chunk = []
                else:
                    current_chunk.append(line)
            
            i += 1
        
        # Save final chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text:
                chunks.append(ParsedChunk(
                    content=chunk_text,
                    chunk_type=current_chunk_type
                ))
        
        return chunks
    
    def _add_page_references(self, chunks: List[ParsedChunk], document) -> List[ParsedChunk]:
        """
        Try to add page number references to chunks
        """
        try:
            # Docling's document model may have page information
            # This is a best-effort attempt; exact page mapping depends on document structure
            for i, chunk in enumerate(chunks):
                # Estimate page based on chunk position (rough heuristic)
                # In production, Docling may provide actual page markers
                chunk.page_num = i // 5 + 1  # Rough estimate
                chunk.page_reference = f"p. {chunk.page_num}"
        except Exception as e:
            logger.debug(f"Could not add page references: {e}")
        
        return chunks
    
    def _estimate_pages(self, document) -> Optional[int]:
        """
        Estimate total pages from document metadata
        """
        try:
            # Try to get page count from document metadata
            if hasattr(document, "pages"):
                return len(document.pages)
            # Fallback: estimate based on content size
            return None
        except Exception:
            return None
