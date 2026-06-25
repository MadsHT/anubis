"""
Pytest configuration and fixtures for Anubis tests
"""

import pytest
import asyncio
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_pdf_path(tmp_path):
    """Create a temporary PDF file path for testing"""
    pdf_file = tmp_path / "test_document.pdf"
    # Write minimal PDF structure (not a real PDF for speed)
    pdf_file.write_bytes(b"%PDF-1.4\n%EOF")
    return str(pdf_file)


@pytest.fixture
def test_config():
    """Provide test configuration"""
    return {
        "server": {
            "host": "127.0.0.1",
            "port": 8000,
            "workers": 1
        },
        "database": {
            "url": "postgresql://test:test@localhost/anubis_test"
        },
        "ollama": {
            "host": "localhost",
            "port": 11434,
            "model": "nomic-embed-text-v1.5"
        },
        "parser": {
            "chunk_size": 512
        },
        "chunker": {
            "chunk_size": 256,
            "overlap": 50,
            "max_chunks": 1000
        },
        "indexer": {
            "batch_size": 32,
            "index_interval": 300
        }
    }
