#!/usr/bin/env python3
"""
CLI for Korean Novel Glossary Maker
Command-line interface for Google Colab and terminal use
"""
import argparse
import json
import os
import sys
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import run_noun_extraction_pipeline
from system import config_loader

def save_config(config_dict, config_path="config.json"):
    """Save configuration to JSON file"""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)
    print(f"Configuration saved to {config_path}")

def load_config(config_path="config.json"):
    """Load configuration from JSON file"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def run_pipeline_with_config(config_path="config.json"):
    """Run the pipeline with the given config file"""
    config = load_config(config_path)
    if not config:
        print(f"Error: Config file {config_path} not found!")
        return False
    
    # Update config_loader with the loaded configuration
    for key, value in config.items():
        if hasattr(config_loader, key):
            setattr(config_loader, key, value)
    
    print("=" * 60)
    print("Starting Korean Novel Glossary Maker")
    print("=" * 60)
    
    success = run_noun_extraction_pipeline()
    
    if success:
        print("\n" + "=" * 60)
        print("NOVEL GLOSSARY MAKER COMPLETED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("NOVEL GLOSSARY MAKER HAS FAILED.")
        print("=" * 60)
    
    return success

def setup_colab():
    """Setup helper for Google Colab"""
    print("Setting up for Google Colab...")
    print("\nTo use this tool in Colab:")
    print("1. Upload your Korean novel text files to a folder named 'raws'")
    print("2. Create a config.json file with your settings")
    print("3. Run: !python cli.py --config config.json")
    print("\nYou can also use the interactive mode: !python cli.py --interactive")

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "API_KEY": "YOUR_GEMINI_API_KEY_HERE",
        "MODEL_NAME": "gemini-2.5-flash",
        "RAWS_FOLDER": "raws",
        "NOUNS_JSON_FILE": "nouns.json",
        "REFERENCE_FILE": "",
        "OUTPUT_EXCEL": "glossary.xlsx",
        "CHAPTERS_ANALYZED": 10,
        "CATEGORIZATION_BATCH_SIZE": 50,
        "TRANSLATION_BATCH_SIZE": 50,
        "HANJA_GUESSING_BATCH_SIZE": 50,
        "MAX_RETRIES": 3,
        "RETRY_DELAY": 31,
        "HANJA_IDENTIFICATION": True,
        "LOCAL_MODEL": False,
        "GUESS_HANJA": False,
        "DO_CATEGORIZATION": False,
        "DO_TRANSLATION": True,
        "SIMPLIFIED_CHINESE_CONVERSION": False,
        "GENRE": "murim",
        "ERROR_LOG": "error.txt",
        "DICT_API_KEY": ""
    }
    
    save_config(sample_config, "sample_config.json")
    print("Sample config created: sample_config.json")
    print("Please edit it with your API key and settings!")

def interactive_setup():
    """Interactive configuration setup"""
    print("\n" + "=" * 60)
    print("Korean Novel Glossary Maker - Interactive Setup")
    print("=" * 60)
    
    config = {}
    
    # Get basic settings
    config["API_KEY"] = input("Enter your Gemini API key: ").strip()
    config["MODEL_NAME"] = input("Model name [gemini-2.5-flash]: ").strip() or "gemini-2.5-flash"
    
    # Folder settings
    print("\nFolder Settings:")
    config["RAWS_FOLDER"] = input("Folder containing Korean novel text files [raws]: ").strip() or "raws"
    config["NOUNS_JSON_FILE"] = input("Glossary JSON filename [nouns.json]: ").strip() or "nouns.json"
    config["OUTPUT_EXCEL"] = input("Output Excel filename [glossary.xlsx]: ").strip() or "glossary.xlsx"
    
    # Optional reference file
    ref_file = input("Reference Excel file (optional, press Enter to skip): ").strip()
    config["REFERENCE_FILE"] = ref_file if ref_file else ""
    
    # Genre selection
    print("\nAvailable genres: murim, rofan, modern, game, westfan, dungeon")
    config["GENRE"] = input("Genre [murim]: ").strip() or "murim"
    
    # Processing options
    print("\nProcessing Options (y/n):")
    config["HANJA_IDENTIFICATION"] = input("Identify hanja? [y]: ").strip().lower() != 'y'
    config["LOCAL_MODEL"] = input("Use local ML model instead of Gemini? [n]: ").strip().lower() == 'n'
    
    if config["LOCAL_MODEL"]:
        config["DICT_API_KEY"] = input("KRDICT API key (for dictionary checking): ").strip()
    
    config["GUESS_HANJA"] = input("Guess missing hanja? [n]: ").strip().lower() != 'n'
    config["DO_CATEGORIZATION"] = input("Categorize terms? [n]: ").strip().lower() != 'n'
    config["DO_TRANSLATION"] = input("Translate terms? [y]: ").strip().lower() != 'y'
    config["SIMPLIFIED_CHINESE_CONVERSION"] = input("Convert to Simplified Chinese? [y]: ").strip().lower() != 'n'
    
    # Batch sizes
    print("\nBatch Sizes:")
    try:
        config["CHAPTERS_ANALYZED"] = int(input("Chapters analyzed simultaneously [10]: ").strip() or "10")
        config["CATEGORIZATION_BATCH_SIZE"] = int(input("Categorization batch size [50]: ").strip() or "50")
        config["TRANSLATION_BATCH_SIZE"] = int(input("Translation batch size [50]: ").strip() or "50")
        config["HANJA_GUESSING_BATCH_SIZE"] = int(input("Hanja guessing batch size [50]: ").strip() or "50")
    except ValueError:
        print("Using default values for batch sizes")
        config["CHAPTERS_ANALYZED"] = 10
        config["CATEGORIZATION_BATCH_SIZE"] = 50
        config["TRANSLATION_BATCH_SIZE"] = 50
        config["HANJA_GUESSING_BATCH_SIZE"] = 50
    
    # Retry settings
    try:
        config["MAX_RETRIES"] = int(input("Max retries [3]: ").strip() or "3")
        config["RETRY_DELAY"] = int(input("Retry delay in seconds [31]: ").strip() or "31")
    except ValueError:
        config["MAX_RETRIES"] = 3
        config["RETRY_DELAY"] = 31
    
    # Save config
    config_filename = input("\nSave config as [config.json]: ").strip() or "config.json"
    save_config(config, config_filename)
    
    print(f"\nConfiguration saved to {config_filename}")
    print("You can now run: python cli.py --config {config_filename}")
    
    run_now = input("\nRun the pipeline now? (y/n): ").strip().lower()
    if run_now == 'y':
        return run_pipeline_with_config(config_filename)
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Korean Novel Glossary Maker CLI')
    parser.add_argument('--config', type=str, default='config.json', 
                       help='Configuration file path (default: config.json)')
    parser.add_argument('--interactive', action='store_true',
                       help='Interactive setup mode')
    parser.add_argument('--sample', action='store_true',
                       help='Create a sample configuration file')
    parser.add_argument('--colab', action='store_true',
                       help='Show Google Colab setup instructions')
    
    args = parser.parse_args()
    
    if args.sample:
        create_sample_config()
    elif args.colab:
        setup_colab()
    elif args.interactive:
        interactive_setup()
    elif os.path.exists(args.config):
        run_pipeline_with_config(args.config)
    else:
        print(f"Config file '{args.config}' not found!")
        print("\nOptions:")
        print("  --interactive    Start interactive setup")
        print("  --sample         Create sample configuration")
        print("  --colab          Show Google Colab instructions")
        print(f"  --config FILE    Use specific config file")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())