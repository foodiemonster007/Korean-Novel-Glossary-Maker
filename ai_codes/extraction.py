# ===============================
# NOUN EXTRACTION WITH AI
# ===============================
"""
Extracts proper nouns from text using AI
"""
import json
import time
from google import genai
from google.genai import types
from system import config_loader, file_operations

# AI Prompt for noun extraction
SYSTEM_PROMPT_BASE = """You are an expert assistant specializing in {genre_description}. {hanja_instruction}

**PROPER NOUN TYPES TO EXTRACT:**
- Character names (people, beings, creatures)
- Skill names (martial arts, magic, techniques, spells)
- Character titles (honorifics, ranks, epithets)
- Locations (places, buildings, countries, cities, towns, realms, worlds)
- Organizations (sects, clans, guilds, factions)
- Item names (weapons, artifacts, tools, equipment, plants)
- Any other unique proper nouns specific to this story

**EXTRACTION RULES:**
1. Extract the noun in Hangul
2. If no Hanja is provided, leave the hanja field as empty string ""
3. Do not include common nouns or generic terms
4. Focus on unique, story-specific proper nouns

**OUTPUT FORMAT:**
You MUST return a SINGLE JSON array of objects.
Each object MUST have EXACTLY these two keys: "hangul", "hanja"
Example: [{{"hangul": "이소룡", "hanja": ""}}, {{"hangul": "철산고", "hanja": "鐵山掌"}}]
"""

HANJA_IDENTIFICATION_NOTE = """IMPORTANT: I have already identified some proper nouns that have Hanja characters explicitly written next to them in parentheses (e.g., "철산고 (鐵山掌)"). Your task is to find ALL other proper nouns written in only **Hangul** throughout the text."""

HANJA_NO_IDENTIFICATION_NOTE = """Your task is to identify and extract ALL proper nouns from the provided text. """

# Build the extraction prompt based on configuration
if config_loader.HANJA_IDENTIFICATION:
    SYSTEM_PROMPT_EXTRACTION = SYSTEM_PROMPT_BASE.format(
        genre_description=config_loader.GENRE_DESCRIPTION,
        hanja_instruction=HANJA_IDENTIFICATION_NOTE
    )
else:
    SYSTEM_PROMPT_EXTRACTION = SYSTEM_PROMPT_BASE.format(
        genre_description=config_loader.GENRE_DESCRIPTION,
        hanja_instruction=HANJA_NO_IDENTIFICATION_NOTE
    )

def filter_duplicate_nouns(api_nouns, existing_hanguls):
    """Filter out nouns that already exist in the reference set."""
    if not api_nouns:
        return []
    
    filtered_nouns = []
    for noun_data in api_nouns:
        hangul = noun_data['hangul']
        if hangul not in existing_hanguls:
            filtered_nouns.append(noun_data)
    
    return filtered_nouns

def get_nouns_from_api_with_retries(client, text_chunk, chunk_index, existing_hanguls=None):
    """Extract nouns from text chunk using AI with retry logic and filter duplicates."""
    # If no existing_hanguls provided, initialize as empty set
    if existing_hanguls is None:
        existing_hanguls = set()
    
    for attempt in range(config_loader.MAX_RETRIES):
        try:
            print(f"  Attempt {attempt + 1}/{config_loader.MAX_RETRIES} for AI discovery...")
            
            response = client.models.generate_content(
                model=config_loader.MODEL_NAME,
                contents=[SYSTEM_PROMPT_EXTRACTION, text_chunk],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if response and response.text and response.text.strip():
                parsed_json = json.loads(response.text)
                # Ensure each item has exactly "hangul" and "hanja" keys
                filtered_nouns = []
                for noun in parsed_json:
                    if isinstance(noun, dict) and 'hangul' in noun and len(str(noun['hangul'])) > 1:
                        # Create a clean dict with only hangul and hanja keys
                        clean_noun = {
                            'hangul': str(noun['hangul']).strip(),
                            'hanja': str(noun.get('hanja', '')).strip()
                        }
                        filtered_nouns.append(clean_noun)
                
                # Filter out duplicates before returning
                non_duplicate_nouns = filter_duplicate_nouns(filtered_nouns, existing_hanguls)
                return non_duplicate_nouns
            else:
                print("  Warning: API returned an empty or invalid response. Retrying...")
        
        except Exception as e:
            print(f"  Error on attempt {attempt + 1}: {e}")
            if "API key not valid" in str(e):
                file_operations.log_error(chunk_index, "Invalid API Key")
                return None

        if attempt < config_loader.MAX_RETRIES - 1:
            time.sleep(config_loader.RETRY_DELAY)
    
    file_operations.log_error(chunk_index, "Max retries exceeded. API did not return valid data.")
    return None