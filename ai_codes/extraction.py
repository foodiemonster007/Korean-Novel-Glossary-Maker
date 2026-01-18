# ===============================
# NOUN EXTRACTION WITH AI
# ===============================
"""
Extracts proper nouns from text using AI in chunks
"""
import json
import time
from google.genai import types
from system import config_loader, file_operations

# AI Prompt for noun extraction (same as before)
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
5. Do NOT extract nouns that have already been identified from regex patterns like "철산고 (鐵山掌)"
**OUTPUT FORMAT:**
You MUST return a SINGLE JSON array of objects.
Each object MUST have EXACTLY these two keys: "hangul", "hanja"
Example: [{{"hangul": "이소룡", "hanja": ""}}, {{"hangul": "철산고", "hanja": "鐵山掌"}}]
"""
HANJA_IDENTIFICATION_NOTE = """IMPORTANT: I have already identified some proper nouns that have Hanja characters explicitly written next to them in parentheses (e.g., "철산고 (鐵山掌)"). Your task is to find ALL other proper nouns written in only **Hangul** throughout the text."""
HANJA_NO_IDENTIFICATION_NOTE = """Your task is to identify and extract ALL proper nouns from the provided text."""

def build_extraction_prompt():
    """Build the extraction prompt based on configuration"""
    if config_loader.HANJA_IDENTIFICATION:
        return SYSTEM_PROMPT_BASE.format(
            genre_description=config_loader.GENRE_DESCRIPTION,
            hanja_instruction=HANJA_IDENTIFICATION_NOTE
        )
    else:
        return SYSTEM_PROMPT_BASE.format(
            genre_description=config_loader.GENRE_DESCRIPTION,
            hanja_instruction=HANJA_NO_IDENTIFICATION_NOTE
        )

SYSTEM_PROMPT_EXTRACTION = build_extraction_prompt()

def extract_nouns_with_ai_by_chunks(client, text_files, master_nouns, existing_hanguls):
    """
    Process files in chunks using AI for noun extraction.
    
    Args:
        client: The pre-configured genai.Client instance 
        text_files: List of text files to process
        master_nouns: Current list of nouns
        existing_hanguls: Set of existing hangul strings for duplicate checking
    
    Returns:
        tuple: (success, master_nouns, existing_hanguls)
    """
    if not text_files:
        return False, master_nouns, existing_hanguls
    
    file_chunks = file_operations.group_files_into_chunks(text_files, config_loader.CHAPTERS_ANALYZED)
    print(f"\n--- Step 2: AI extraction on {len(file_chunks)} chunks ---")
    print(f"  Grouped files into {len(file_chunks)} chunks of up to {config_loader.CHAPTERS_ANALYZED} files each.")
    
    ai_nouns_count = 0
    
    for i, file_chunk in enumerate(file_chunks):
        print(f"\n--- Processing AI chunk {i+1}/{len(file_chunks)} ---")
        print(f"  Files: {[file_operations.get_filename(f) for f in file_chunk]}")
        
        chunk_text = file_operations.combine_files_content(file_chunk)
        
        # AI noun extraction - pass the client to the API call function
        api_nouns = _call_ai_api_with_retries(client, chunk_text, i + 1)
        
        if api_nouns:
            new_nouns_in_chunk = 0
            for noun_data in api_nouns:
                hangul = noun_data['hangul']
                if hangul not in existing_hanguls:
                    new_noun = {
                        'hangul': hangul,
                        'hanja': noun_data['hanja'],
                        'english': '',
                        'category': '',
                        'frequency': 0
                    }
                    master_nouns.append(new_noun)
                    existing_hanguls.add(hangul)
                    ai_nouns_count += 1
                    new_nouns_in_chunk += 1
            
            print(f"  AI discovered {new_nouns_in_chunk} new nouns in this chunk.")
        
        file_operations.save_nouns_json(master_nouns)
        print(f"  Progress saved. Total nouns so far: {len(master_nouns)}")
    
    print(f"\n--- AI extraction complete ---")
    print(f"  Total AI-discovered nouns: {ai_nouns_count}")
    print(f"  Grand total nouns: {len(master_nouns)}")
    
    if not master_nouns:
        print("No nouns found in the text files.")
        return False, master_nouns, existing_hanguls
    
    return True, master_nouns, existing_hanguls

def _call_ai_api_with_retries(client, text_chunk, chunk_index):
    """Internal function to call AI API with retry logic."""
    for attempt in range(config_loader.MAX_RETRIES):
        try:
            print(f"  Attempt {attempt + 1}/{config_loader.MAX_RETRIES} for AI discovery...")
            
            # Use the passed client instance, not creating a new one
            response = client.models.generate_content(
                model=config_loader.MODEL_NAME,
                contents=[SYSTEM_PROMPT_EXTRACTION, text_chunk],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if response and response.text and response.text.strip():
                parsed_json = json.loads(response.text)
                filtered_nouns = []
                for noun in parsed_json:
                    if isinstance(noun, dict) and 'hangul' in noun and len(str(noun['hangul'])) > 1:
                        clean_noun = {
                            'hangul': str(noun['hangul']).strip(),
                            'hanja': str(noun.get('hanja', '')).strip()
                        }
                        filtered_nouns.append(clean_noun)
                return filtered_nouns
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