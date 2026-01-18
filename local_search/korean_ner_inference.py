#!/usr/bin/env python3
"""
Korean NER Inference Pipeline with Config-based Processing
Main file that maintains the original interface for compatibility.
"""

import json
import os
import sys
from datetime import datetime
import time
from typing import List, Dict, Any, Tuple, Optional

# Get current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
ner_system_dir = os.path.join(current_dir, 'ner_system')

# Add ner_system directory to Python path so we can import modules directly
if ner_system_dir not in sys.path:
    sys.path.insert(0, ner_system_dir)

# Now import from ner_system directory
try:
    # Import modules directly (they're now in the Python path)
    from ner_processor import KoreanNERProcessor
    from novel_processor import NovelProcessor
    from pipeline import run_local_ner_pipeline as modular_run_local_ner_pipeline
    print("Successfully imported ner_system modules")
except ImportError as e:
    print(f"Error importing ner_system modules: {e}")
    print(f"Python path: {sys.path}")
    print(f"ner_system_dir: {ner_system_dir}")
    
    # List files in ner_system directory
    if os.path.exists(ner_system_dir):
        print(f"Files in ner_system directory:")
        for f in os.listdir(ner_system_dir):
            print(f"  - {f}")
    raise

# Add parent directory to path to import config_loader
sys.path.append(os.path.join(current_dir, '..'))

def run_local_ner_pipeline(master_nouns: Optional[List[Dict[str, Any]]] = None) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Wrapper to run local NER pipeline - maintains original interface.
    
    This function is called by the main pipeline in main.py.
    
    Returns:
        Tuple of (updated_master_nouns, glossary_path) or (None, None) if failed.
    """
    try:
        # Import config_loader from parent directory's system folder
        from system import config_loader
        
        config_path = os.path.join(current_dir, "config.json")
        
        # Load local configuration (contains NER_MODEL_PATH, OUTPUT_DIR, LOG_DIR, etc.)
        with open(config_path, 'r', encoding='utf-8') as f:
            local_ner_config = json.load(f)
        
        # Convert relative paths to absolute paths
        model_path = local_ner_config["paths"]["model_path"]
        output_dir = local_ner_config["paths"]["output_directory"]
        log_dir = local_ner_config["paths"]["log_directory"]
        
        # Convert to absolute paths
        if not os.path.isabs(model_path):
            model_path = os.path.join(current_dir, model_path)
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(current_dir, output_dir)
        if not os.path.isabs(log_dir):
            log_dir = os.path.join(current_dir, log_dir)
        
        # Build configuration by combining:
        # 1. RAWS_FOLDER and DICT_API_KEY from config_loader (main pipeline)
        # 2. Local config for model paths, output directories, and processing settings
        local_config = {
            "paths": {
                "novel_directory": config_loader.RAWS_FOLDER,  # From main pipeline
                "model_path": model_path,  # Local - absolute path
                "output_directory": output_dir,  # Local - absolute path
                "log_directory": log_dir  # Local - absolute path
            },
            "api_keys": {
                "krdict_api_key": config_loader.DICT_API_KEY or "YOUR_KRDICT_API_KEY_HERE"  # From main pipeline
            },
            "processing": local_ner_config.get("processing", {
                "use_gpu": True,
                "chunk_size": 512,
                "batch_size": 32,
                "remove_blank_lines": True,
                "encoding": "utf-8",
                "checkpoint_interval": 10
            }),
            "output": local_ner_config.get("output", {
                "include_original_text": True,
                "include_context": True,
                "group_by_chapter": False,
                "confidence_threshold": 0.7
            })
        }
        
        print("\nLocal NER Configuration loaded.")
        print(f"  - Novel directory: {config_loader.RAWS_FOLDER}")
        print(f"  - Model path: {model_path}")
        print(f"  - Output directory: {output_dir}")
        
        # Ensure directories exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)
        
        # Check if model exists
        if not os.path.exists(model_path):
            print(f"WARNING: Model path does not exist: {model_path}")
            print("Please make sure the NER model is downloaded and placed in the correct directory.")
            return master_nouns, None
        
        # Call the modular pipeline with the combined configuration
        return modular_run_local_ner_pipeline(master_nouns, local_config)
        
    except Exception as e:
        print(f"Error in local NER pipeline: {e}")
        import traceback
        traceback.print_exc()
        return master_nouns, None

def main():
    """Main function to run the Korean NER pipeline as standalone."""
    # For standalone use, load config
    config_path = os.path.join(current_dir, "config.json")
    
    if not os.path.exists(config_path):
        # Create default config for standalone use
        default_config = {
            "paths": {
                "novel_directory": "./novel_chapters",
                "model_path": "./ner_model",
                "output_directory": "./ner_output",
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
        config = default_config
    else:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Loaded configuration from: {config_path}")
    
    # Initialize processors
    ner_processor = KoreanNERProcessor(config)
    novel_processor = NovelProcessor(config)
    
    try:
        glossary = novel_processor.process_novel(ner_processor)
        output_file = novel_processor.export_glossary(glossary)
        
        print("\n" + "="*60)
        print("PROCESSING COMPLETE")
        print("="*60)
        
        if glossary['entities']:
            sample_count = min(10, len(glossary['entities']))
            print(f"\nSample detailed entities (showing {sample_count} of {len(glossary['entities'])}):")
            
            for i, entity in enumerate(glossary['entities'][:sample_count]):
                flag_status = "AMBIGUOUS" if entity['flag'] else "CLEAR"
                chapter_info = f" (Ch. {entity.get('chapter', 'N/A')})" if 'chapter' in entity else ""
                print(f"  {i+1:2d}. '{entity['text']}' ({entity['type']}){chapter_info}")
                print(f"       Confidence: {entity['confidence']:.3f} - Status: {flag_status}")
        
        print(f"\nDetailed glossary saved to: {output_file}")
        
        # Generate summary report
        summary_file = output_file.replace('.json', '_summary.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"NOVEL PROCESSING SUMMARY\n")
            f.write(f"=======================\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total chapters: {glossary['metadata']['total_chapters']}\n")
            f.write(f"Total text length: {glossary['metadata']['total_text_length']:,} characters\n")
            f.write(f"Total entities found: {glossary['metadata']['total_entities']}\n")
            f.write(f"Clear entities: {glossary['statistics']['clear_count']}\n")
            f.write(f"Ambiguous entities: {glossary['statistics']['ambiguous_count']}\n")
            f.write(f"Ambiguity rate: {glossary['statistics']['ambiguity_rate']:.2%}\n")
            f.write(f"Average confidence: {glossary['statistics']['average_confidence']:.3f}\n")
            f.write(f"Processing time: {glossary['metadata']['processing_time']:.1f} seconds\n")
            f.write(f"Processing mode: {glossary['metadata']['processing_mode']}\n")
            f.write(f"Batch size: {glossary['metadata']['batch_size']}\n")
            f.write(f"\nOutput files:\n")
            f.write(f"  - Detailed glossary: {output_file}\n")
            f.write(f"  - Simplified glossary: {os.path.join(config['paths']['output_directory'], 'glossary.json')}\n")
        
        print(f"Summary report: {summary_file}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\nProcessing interrupted. Checkpoint saved.")
        print("Run the script again to resume from checkpoint.")
        print("\nPlease check:")
        print("  1. Novel directory exists with files")
        print("  2. Model path is correct")
        print("  3. API key is valid (if using dictionary lookup)")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())