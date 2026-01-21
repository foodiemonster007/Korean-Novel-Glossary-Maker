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
    print(f"✓ Configuration saved to {config_path}")

def load_config(config_path="config.json"):
    """Load configuration from JSON file"""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️  Error: {config_path} is not valid JSON!")
            return None
    return None

def ask_yes_no(question, default="n"):
    """Ask a yes/no question and return boolean"""
    while True:
        answer = input(f"{question} (y/n) [default: {default}]: ").strip().lower()
        if answer == "":
            answer = default
        if answer in ["y", "yes"]:
            return True
        elif answer in ["n", "no"]:
            return False
        else:
            print("Please answer 'y' or 'n'")

def ask_int(question, default, min_val=1, max_val=100):
    """Ask for an integer with validation"""
    while True:
        answer = input(f"{question} [default: {default}]: ").strip()
        if answer == "":
            return default
        try:
            value = int(answer)
            if min_val <= value <= max_val:
                return value
            else:
                print(f"Please enter a number between {min_val} and {max_val}")
        except ValueError:
            print("Please enter a valid number")

def ask_string(question, default, required=False):
    """Ask for a string input"""
    while True:
        answer = input(f"{question} [default: {default}]: ").strip()
        if answer == "":
            if required and default == "":
                print("This field is required!")
                continue
            return default
        return answer

def modify_config_interactive(config):
    """Interactive configuration modification"""
    print("\n" + "=" * 60)
    print("MODIFY CONFIGURATION")
    print("=" * 60)
    print("\nFor each setting, press Enter to keep current value or enter new value.")
    
    # API Settings
    print("\n" + "-" * 40)
    print("API SETTINGS")
    print("-" * 40)
    
    # Check for environment variable first
    env_gemini_key = os.environ.get('GEMINI_API_KEY')
    if env_gemini_key:
        print(f"⚠️  GEMINI_API_KEY environment variable is set ({env_gemini_key[:8]}...)")
        print("  (This will override any value in config)")
        config["API_KEY"] = ""
    
    config["API_KEY"] = ask_string("Gemini API Key", config.get("API_KEY", ""))
    config["MODEL_NAME"] = ask_string("Model Name", config.get("MODEL_NAME", "gemini-2.5-flash"))
    
    # File & Folder Settings
    print("\n" + "-" * 40)
    print("FILE & FOLDER SETTINGS")
    print("-" * 40)
    
    config["RAWS_FOLDER"] = ask_string("Folder with Korean novel text files", config.get("RAWS_FOLDER", "raws"))
    config["NOUNS_JSON_FILE"] = ask_string("Glossary JSON filename", config.get("NOUNS_JSON_FILE", "nouns.json"))
    config["OUTPUT_EXCEL"] = ask_string("Output Excel filename", config.get("OUTPUT_EXCEL", "glossary.xlsx"))
    
    ref_file = ask_string("Reference Excel file (optional)", config.get("REFERENCE_FILE", ""))
    config["REFERENCE_FILE"] = ref_file if ref_file else ""
    
    # Genre Selection
    print("\n" + "-" * 40)
    print("GENRE SELECTION")
    print("-" * 40)
    
    genres = ["murim", "rofan", "modern", "game", "westfan", "dungeon"]
    current_genre = config.get("GENRE", "murim")
    
    if current_genre not in genres:
        current_genre = "murim"
    
    print(f"Available genres: {', '.join(genres)}")
    
    while True:
        answer = input(f"Genre [default: {current_genre}]: ").strip().lower()
        if answer == "":
            config["GENRE"] = current_genre
            break
        elif answer in genres:
            config["GENRE"] = answer
            break
        else:
            print(f"Invalid genre. Must be one of: {', '.join(genres)}")
    
    # Processing Options
    print("\n" + "-" * 40)
    print("PROCESSING OPTIONS")
    print("-" * 40)
    
    config["HANJA_IDENTIFICATION"] = ask_yes_no("Identify hanja in text?", 
                                                "y" if config.get("HANJA_IDENTIFICATION", True) else "n")
    
    # Add SAVE_NEW_ONLY option
    config["SAVE_NEW_ONLY"] = ask_yes_no("Export only new glossary terms?", 
                                         "y" if config.get("SAVE_NEW_ONLY", False) else "n")
    if config["SAVE_NEW_ONLY"]:
        print("  ⓘ Only terms not in the original glossary will be exported to Excel.")
    
    config["LOCAL_MODEL"] = ask_yes_no("Use local ML model (instead of Gemini)?", 
                                       "y" if config.get("LOCAL_MODEL", False) else "n")
    
    if config["LOCAL_MODEL"]:
        env_dict_key = os.environ.get('KRDICT_API_KEY')
        if env_dict_key:
            print(f"⚠️  KRDICT_API_KEY environment variable is set ({env_dict_key[:8]}...)")
            print("  (This will override any value in config)")
            config["DICT_API_KEY"] = ""
        
        config["DICT_API_KEY"] = ask_string("KRDICT API Key (for dictionary checking)", 
                                           config.get("DICT_API_KEY", ""))
    else:
        config["DICT_API_KEY"] = ""
    
    config["GUESS_HANJA"] = ask_yes_no("Guess missing hanja?", 
                                       "y" if config.get("GUESS_HANJA", False) else "n")
    
    config["DO_CATEGORIZATION"] = ask_yes_no("Categorize terms?", 
                                            "y" if config.get("DO_CATEGORIZATION", False) else "n")
    
    config["DO_TRANSLATION"] = ask_yes_no("Translate terms to English?", 
                                         "y" if config.get("DO_TRANSLATION", True) else "n")
    
    config["SIMPLIFIED_CHINESE_CONVERSION"] = ask_yes_no("Convert hanja to Simplified Chinese?", 
                                                        "y" if config.get("SIMPLIFIED_CHINESE_CONVERSION", False) else "n")
    
    # Batch Sizes
    print("\n" + "-" * 40)
    print("BATCH SIZES")
    print("(Higher = faster, but may hit API limits)")
    print("-" * 40)
    
    config["CHAPTERS_ANALYZED"] = ask_int("Chapters analyzed simultaneously", 
                                         config.get("CHAPTERS_ANALYZED", 10), 1, 50)
    
    config["CATEGORIZATION_BATCH_SIZE"] = ask_int("Categorization batch size", 
                                                 config.get("CATEGORIZATION_BATCH_SIZE", 50), 1, 100)
    
    config["TRANSLATION_BATCH_SIZE"] = ask_int("Translation batch size", 
                                              config.get("TRANSLATION_BATCH_SIZE", 50), 1, 100)
    
    config["HANJA_GUESSING_BATCH_SIZE"] = ask_int("Hanja guessing batch size", 
                                                 config.get("HANJA_GUESSING_BATCH_SIZE", 50), 1, 100)
    
    # Error Handling
    print("\n" + "-" * 40)
    print("ERROR HANDLING")
    print("-" * 40)
    
    config["MAX_RETRIES"] = ask_int("Max retries on API failure", 
                                   config.get("MAX_RETRIES", 3), 1, 20)
    
    config["RETRY_DELAY"] = ask_int("Retry delay (seconds)", 
                                   config.get("RETRY_DELAY", 31), 1, 300)
    
    # Fixed values
    config["ERROR_LOG"] = "error.txt"
    
    return config

def run_pipeline_with_config(config_path="config.json"):
    """Run the pipeline with the given config file"""
    config = load_config(config_path)
    if not config:
        print(f"❌ Error: Config file {config_path} not found!")
        return False
    
    # Show current config summary
    print("\n" + "=" * 60)
    print("CURRENT CONFIGURATION")
    print("=" * 60)
    
    print(f"\n📁 Files:")
    print(f"  • Novel folder: {config.get('RAWS_FOLDER', 'raws')}")
    print(f"  • Output file: {config.get('OUTPUT_EXCEL', 'glossary.xlsx')}")
    print(f"  • Genre: {config.get('GENRE', 'murim')}")
    
    print(f"\n⚙️  Processing:")
    options = []
    if config.get("DO_TRANSLATION", True): options.append("Translation")
    if config.get("DO_CATEGORIZATION", False): options.append("Categorization")
    if config.get("HANJA_IDENTIFICATION", True): options.append("Hanja ID")
    if config.get("SAVE_NEW_ONLY", False): options.append("Save New Only")
    print(f"  • Enabled: {', '.join(options) if options else 'None'}")
    
    # Ask if user wants to modify
    modify = ask_yes_no("\nDo you want to modify the configuration?", "n")
    
    if modify:
        config = modify_config_interactive(config)
        # Save the modified config
        save_config(config, config_path)
        print(f"\n✓ Configuration updated and saved to {config_path}")
    else:
        print("\n✓ Using current configuration without changes.")
    
    # === API KEY HANDLING ===
    # Check for API key from all sources
    env_gemini_key = os.environ.get('GEMINI_API_KEY')
    config_gemini_key = config.get("API_KEY", "").strip()
    
    # Decide which key to use
    final_api_key = ""
    if env_gemini_key:
        print("✓ Using GEMINI_API_KEY from environment variable")
        final_api_key = env_gemini_key
    elif config_gemini_key and config_gemini_key != "YOUR_GEMINI_API_KEY_HERE":
        print("✓ Using API_KEY from configuration file")
        final_api_key = config_gemini_key
    else:
        # If still no key, ASK THE USER
        print("\n🔑 Gemini API Key not found.")
        final_api_key = input("Please enter your Gemini API key now: ").strip()
    
    # CRITICAL: Update the config with the final key
    config["API_KEY"] = final_api_key
    
    # Optional: Do the same for KRDICT key if needed
    if config.get("LOCAL_MODEL", False):
        env_dict_key = os.environ.get('KRDICT_API_KEY')
        config_dict_key = config.get("DICT_API_KEY", "").strip()
        
        if env_dict_key:
            print("✓ Using KRDICT_API_KEY from environment variable")
            config["DICT_API_KEY"] = env_dict_key
        elif not config_dict_key:
            config["DICT_API_KEY"] = input("Enter KRDICT API key (or press Enter to skip): ").strip()
    
    # Update config_loader with the configuration
    for key, value in config.items():
        if hasattr(config_loader, key):
            setattr(config_loader, key, value)
    
    print("\n" + "=" * 60)
    print("Starting Korean Novel Glossary Maker")
    print("=" * 60)
    
    success = run_noun_extraction_pipeline()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ NOVEL GLOSSARY MAKER COMPLETED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ NOVEL GLOSSARY MAKER HAS FAILED.")
        print("=" * 60)
    
    return success

def setup_colab():
    """Setup helper for Google Colab"""
    print("Setting up for Google Colab...")
    print("\nTo use this tool in Colab:")
    print("1. Upload your Korean novel text files to a folder named 'raws'")
    print("2. Optionally set environment variables:")
    print("   - %env GEMINI_API_KEY=your_key_here")
    print("   - %env KRDICT_API_KEY=your_key_here")
    print("3. Run: !python cli.py --config config.json")
    print("\nOr use the interactive mode: !python cli.py --interactive")
    
    print("\nExample Colab cell:")
    print("```python")
    print("# Set API keys as environment variables (optional)")
    print("%env GEMINI_API_KEY=AIzaSy...")
    print("%env KRDICT_API_KEY=your_krdict_key")
    print("!git clone https://github.com/foodiemonster007/Korean-Novel-Glossary-Maker")
    print("%cd Korean-Novel-Glossary-Maker")
    print("!python cli.py --interactive")
    print("```")

def create_sample_config():
    """Create a sample configuration file"""
    # Check for environment variables
    env_gemini_key = os.environ.get('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')
    env_dict_key = os.environ.get('KRDICT_API_KEY', '')
    
    sample_config = {
        "API_KEY": env_gemini_key if env_gemini_key != 'YOUR_GEMINI_API_KEY_HERE' else "YOUR_GEMINI_API_KEY_HERE",
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
        "SAVE_NEW_ONLY": False,  # Add this line
        "LOCAL_MODEL": False,
        "GUESS_HANJA": False,
        "DO_CATEGORIZATION": False,
        "DO_TRANSLATION": True,
        "SIMPLIFIED_CHINESE_CONVERSION": False,
        "GENRE": "murim",
        "ERROR_LOG": "error.txt",
        "DICT_API_KEY": env_dict_key if env_dict_key else ""
    }
    
    save_config(sample_config, "sample_config.json")
    print("Sample config created: sample_config.json")
    
    if env_gemini_key and env_gemini_key != 'YOUR_GEMINI_API_KEY_HERE':
        print("✓ Used GEMINI_API_KEY from environment variable")
    
    if env_dict_key:
        print("✓ Used KRDICT_API_KEY from environment variable")
    
    print("Please review and edit the config file as needed!")

def interactive_setup():
    """Interactive configuration setup - creates NEW config"""
    print("\n" + "=" * 60)
    print("Korean Novel Glossary Maker - Interactive Setup")
    print("=" * 60)
    
    config = {}
    
    # Get Gemini API key (check env first)
    print("\nGemini API Key:")
    print("(Or set GEMINI_API_KEY environment variable)")
    
    default_gemini = os.environ.get('GEMINI_API_KEY', '')
    if default_gemini:
        print(f"✓ Found GEMINI_API_KEY in environment (first 8 chars: {default_gemini[:8]}...)")
        use_env = input("Use environment variable? (y/n, default: y): ").strip().lower() or 'y'
        if use_env == 'y':
            config["API_KEY"] = default_gemini
        else:
            config["API_KEY"] = input("Enter Gemini API key: ").strip()
    else:
        config["API_KEY"] = input("Enter Gemini API key: ").strip()
    
    # Model name
    config["MODEL_NAME"] = input("\nModel name [gemini-2.5-flash]: ").strip() or "gemini-2.5-flash"
    
    # Folder settings
    print("\n" + "-" * 40)
    print("Folder Settings:")
    config["RAWS_FOLDER"] = input("Folder containing Korean novel text files [raws]: ").strip() or "raws"
    config["NOUNS_JSON_FILE"] = input("Glossary JSON filename [nouns.json]: ").strip() or "nouns.json"
    config["OUTPUT_EXCEL"] = input("Output Excel filename [glossary.xlsx]: ").strip() or "glossary.xlsx"
    
    # Optional reference file
    ref_file = input("\nReference Excel file (optional, press Enter to skip): ").strip()
    config["REFERENCE_FILE"] = ref_file if ref_file else ""
    
    # Genre selection
    print("\n" + "-" * 40)
    print("Genre Selection:")
    print("Available genres: murim, rofan, modern, game, westfan, dungeon")
    config["GENRE"] = input("Genre [murim]: ").strip() or "murim"
    
    # Processing options
    print("\n" + "-" * 40)
    print("Processing Options (y/n):")
    
    config["HANJA_IDENTIFICATION"] = input("Identify hanja in text? (e.g., 천마(天魔)) [y]: ").strip().lower() != 'n'
    
    # Add SAVE_NEW_ONLY option
    config["SAVE_NEW_ONLY"] = input("Export only new glossary terms? [n]: ").strip().lower() != 'n'
    if config["SAVE_NEW_ONLY"]:
        print("  ⓘ Only terms not in the original glossary will be exported to Excel.")
    
    config["LOCAL_MODEL"] = input("Use local ML model instead of Gemini? [n]: ").strip().lower() == 'y'
    
    if config["LOCAL_MODEL"]:
        # Check for KRDICT API key in environment
        default_krdict = os.environ.get('KRDICT_API_KEY', '')
        if default_krdict:
            print(f"✓ Found KRDICT_API_KEY in environment (first 8 chars: {default_krdict[:8]}...)")
            use_env = input("Use environment variable? (y/n, default: y): ").strip().lower() or 'y'
            if use_env == 'y':
                config["DICT_API_KEY"] = default_krdict
            else:
                config["DICT_API_KEY"] = input("KRDICT API key (for dictionary checking): ").strip()
        else:
            config["DICT_API_KEY"] = input("KRDICT API key (for dictionary checking): ").strip()
    else:
        config["DICT_API_KEY"] = ""
    
    config["GUESS_HANJA"] = input("Guess missing hanja? (e.g., if only 천마 is given) [n]: ").strip().lower() != 'n'
    config["DO_CATEGORIZATION"] = input("Categorize terms? [n]: ").strip().lower() != 'n'
    config["DO_TRANSLATION"] = input("Translate terms to English? [y]: ").strip().lower() != 'n'
    config["SIMPLIFIED_CHINESE_CONVERSION"] = input("Convert hanja to Simplified Chinese? [n]: ").strip().lower() != 'n'
    
    # Batch sizes
    print("\n" + "-" * 40)
    print("Batch Sizes (higher = faster but may hit API limits):")
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
    print("\n" + "-" * 40)
    print("Error Handling:")
    try:
        config["MAX_RETRIES"] = int(input("Max retries on API failure [3]: ").strip() or "3")
        config["RETRY_DELAY"] = int(input("Retry delay in seconds [31]: ").strip() or "31")
    except ValueError:
        config["MAX_RETRIES"] = 3
        config["RETRY_DELAY"] = 31
    
    # Error log
    config["ERROR_LOG"] = "error.txt"
    
    # Save config
    config_filename = input("\nSave config as [config.json]: ").strip() or "config.json"
    save_config(config, config_filename)
    
    print(f"\n✓ Configuration saved to {config_filename}")
    
    # Ask if user wants to run now
    run_now = input("\nRun the pipeline now? (y/n): ").strip().lower()
    if run_now == 'y':
        print("\n" + "=" * 60)
        print("Starting pipeline...")
        print("=" * 60)
        return run_pipeline_with_config(config_filename)
    
    return True

def show_env_help():
    """Show environment variable help"""
    print("\n" + "=" * 60)
    print("ENVIRONMENT VARIABLES SETUP")
    print("=" * 60)
    
    print("\nYou can set these environment variables instead of entering API keys:")
    print("\n1. GEMINI_API_KEY - Your Google Gemini API key")
    print("2. KRDICT_API_KEY - Your Korean dictionary API key (optional)")
    
    print("\nHow to set environment variables:")
    
    print("\nOn Linux/Mac (terminal):")
    print("  export GEMINI_API_KEY='your_key_here'")
    print("  export KRDICT_API_KEY='your_dict_key_here'")
    
    print("\nOn Windows (Command Prompt):")
    print("  set GEMINI_API_KEY=your_key_here")
    print("  set KRDICT_API_KEY=your_dict_key_here")
    
    print("\nOn Windows (PowerShell):")
    print("  $env:GEMINI_API_KEY='your_key_here'")
    print("  $env:KRDICT_API_KEY='your_dict_key_here'")
    
    print("\nIn Google Colab:")
    print("  %env GEMINI_API_KEY=your_key_here")
    print("  %env KRDICT_API_KEY=your_dict_key_here")
    
    print("\nTo use environment variables:")
    print("  1. Set the environment variables")
    print("  2. Run: python cli.py --config config.json")
    print("\nThe tool will automatically use environment variables if available.")

def main():
    parser = argparse.ArgumentParser(
        description='Korean Novel Glossary Maker CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive setup (creates NEW config from scratch)
  python cli.py --interactive
  
  # Use existing config file (asks if you want to modify)
  python cli.py --config my_config.json
  
  # Create sample config
  python cli.py --sample
  
  # Show Colab instructions
  python cli.py --colab
  
  # Show environment variable help
  python cli.py --env-help
  
Using environment variables:
  export GEMINI_API_KEY=your_key_here
  python cli.py --config config.json
        """
    )
    
    parser.add_argument('--config', type=str, default='config.json', 
                       help='Configuration file path (default: config.json)')
    parser.add_argument('--interactive', action='store_true',
                       help='Interactive setup mode (creates NEW config)')
    parser.add_argument('--sample', action='store_true',
                       help='Create a sample configuration file')
    parser.add_argument('--colab', action='store_true',
                       help='Show Google Colab setup instructions')
    parser.add_argument('--env-help', action='store_true',
                       help='Show environment variable setup instructions')
    parser.add_argument('--run', action='store_true',
                       help='Run immediately without asking to modify config')
    
    args = parser.parse_args()
    
    if args.sample:
        create_sample_config()
    elif args.colab:
        setup_colab()
    elif args.env_help:
        show_env_help()
    elif args.interactive:
        interactive_setup()
    elif os.path.exists(args.config):
        if args.run:
            # Run immediately without modification prompt
            run_pipeline_with_config(args.config)
        else:
            # Normal flow with modification prompt
            run_pipeline_with_config(args.config)
    else:
        print(f"❌ Config file '{args.config}' not found!")
        print("\nAvailable options:")
        print("  --interactive    Create new config from scratch")
        print("  --sample         Create sample configuration")
        print("  --colab          Show Google Colab instructions")
        print("  --env-help       Show environment variable setup")
        print("  --run            Run without modification prompt")
        print(f"  --config FILE    Use specific config file")
        
        # Check if environment variables are set
        env_gemini = os.environ.get('GEMINI_API_KEY')
        if env_gemini:
            print(f"\nℹ️  GEMINI_API_KEY environment variable is set ({env_gemini[:8]}...)")
            print("   You can create a config without entering API key:")
            print("   python cli.py --sample")
            print("   python cli.py --config sample_config.json")
        
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())