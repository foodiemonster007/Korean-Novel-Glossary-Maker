# ===============================
# CONFIGURATION LOADER
# ===============================
"""
Loads and validates configuration from config.json
"""
import json
import os

# Default configurations
CONFIG_FILE = "config.json"

# Load configuration
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
else:
    print(f"Warning: {CONFIG_FILE} not found. Using default configuration.")
    config = {}

# Extract configuration values
API_KEY = config.get("API_KEY", "")
MODEL_NAME = config.get("MODEL_NAME", "gemini-2.5-pro")
RAWS_FOLDER = config.get("RAWS_FOLDER", "raws")
NOUNS_JSON_FILE = config.get("NOUNS_JSON_FILE", "nouns.json")
REFERENCE_FILE = config.get("REFERENCE_FILE", "murim_reference.xlsx")
OUTPUT_EXCEL = config.get("OUTPUT_EXCEL", "nouns_replace.xlsx")
ERROR_LOG = config.get("ERROR_LOG", "error.txt")
CHAPTERS_ANALYZED = config.get("CHAPTERS_ANALYZED", 5)
CATEGORIZATION_BATCH_SIZE = config.get("CATEGORIZATION_BATCH_SIZE", 20)
TRANSLATION_BATCH_SIZE = config.get("TRANSLATION_BATCH_SIZE", 15)
HANJA_GUESSING_BATCH_SIZE = config.get("HANJA_GUESSING_BATCH_SIZE", 15)
MAX_RETRIES = config.get("MAX_RETRIES", 10)
RETRY_DELAY = config.get("RETRY_DELAY", 30)
HANJA_IDENTIFICATION = config.get("HANJA_IDENTIFICATION", True)
LOCAL_MODEL = config.get("LOCAL_MODEL", False)
DICT_API_KEY = config.get("DICT_API_KEY", "")
GUESS_HANJA = config.get("GUESS_HANJA", True)
DO_CATEGORIZATION = config.get("DO_CATEGORIZATION", True)
DO_TRANSLATION = config.get("DO_TRANSLATION", True)
SIMPLIFIED_CHINESE_CONVERSION = config.get("SIMPLIFIED_CHINESE_CONVERSION", True)
GENRE = config.get("GENRE", "murim")
GENRE_DESCRIPTIONS = config.get("GENRE_DESCRIPTIONS", {
    "murim": "Korean martial arts novels",
    "rofan": "Korean romance fantasy novels", 
    "modern": "Korean modern day novels",
    "game": "Korean novels about video games",
    "westfan": "Korean western fantasy novels",
    "dungeon": "Korean modern day fantasy novels"
})
CATEGORIES = config.get("CATEGORIES", [
    "character names",
    "skills and techniques", 
    "character titles",
    "locations and organizations",
    "item names",
    "misc"
])

# Validate GENRE setting
if GENRE not in GENRE_DESCRIPTIONS:
    print(f"Warning: Unknown GENRE '{GENRE}'. Defaulting to 'murim'.")
    GENRE = "murim"

GENRE_DESCRIPTION = GENRE_DESCRIPTIONS[GENRE]

print(f"Configuration loaded from {CONFIG_FILE}")