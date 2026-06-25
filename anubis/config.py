"""
Configuration management for Anubis RAG Engine
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.yaml
    """
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables if present
    if os.getenv("DATABASE_URL"):
        config["database"]["url"] = os.getenv("DATABASE_URL")
    if os.getenv("OLLAMA_BASE_URL"):
        config["ollama"]["base_url"] = os.getenv("OLLAMA_BASE_URL")
    if os.getenv("AUTO_INDEX_INTERVAL"):
        config["auto_indexing"]["interval_seconds"] = int(os.getenv("AUTO_INDEX_INTERVAL"))
    
    return config

def get_config_value(config: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Get nested config value by dot-separated path
    Example: get_config_value(config, "database.pool_size", 20)
    """
    keys = path.split(".")
    value = config
    
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
    
    return value if value is not None else default
