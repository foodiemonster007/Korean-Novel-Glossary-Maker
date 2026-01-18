"""
Configuration loading utilities.
"""

import json
import os
from typing import Dict, Any

def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """Load configuration from JSON file."""
    if not os.path.exists(config_path):
        default_config = {
            "paths": {
                "novel_directory": "./novel_chapters",
                "model_path": "./ner_model",
                "output_directory": "./output",
                "log_directory": "./logs"
            },
            "api_keys": {
                "krdict_api_key": "YOUR_KRDICT_API_KEY_HERE"
            },
            "processing": {
                "use_gpu": True,
                "chunk_size": 512,
                "batch_size": 32,
                "remove_blank_lines": True,
                "encoding": "utf-8",
                "checkpoint_interval": 10
            },
            "output": {
                "include_original_text": True,
                "include_context": True,
                "group_by_chapter": False,
                "confidence_threshold": 0.7
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        
        print(f"Created default config at: {config_path}")
        return default_config
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print(f"Loaded configuration from: {config_path}")
    return config