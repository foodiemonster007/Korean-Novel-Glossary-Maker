# ===============================
# NOUN CATEGORIZATION WITH AI
# ===============================
"""
Categorizes nouns into predefined categories using AI
"""
import json
import time
from google import genai
from google.genai import types
from system import config_loader

# AI Prompt for categorization
SYSTEM_PROMPT_CATEGORIZATION = """You are an expert in {genre_description} terminology and classification. Your task is to categorize each proper noun into exactly one of these categories: {categories}.

**INPUT:** You will receive a JSON array of noun objects, each with "hangul" and "hanja" fields.

**CRITICAL CATEGORIZATION RULES:**
1. **PRIORITIZE HANJA FOR ANALYSIS**: When hanja is available (not empty), use it as the primary source to determine the category. Hanja provides the meaning and context.
2. **FALLBACK TO HANGUL**: When hanja is empty, analyze the hangul term based on its structure and common {genre_description} conventions.
3. **CONSIDER GENRE CONTEXT**: {genre_description} has specific conventions for each category.

**CATEGORY DEFINITIONS:**
1. "character names": Personal names of individual characters, beings, or creatures.
2. "skills and techniques": Martial arts techniques, magic spells, special abilities, combat moves.
3. "character titles": Titles, ranks, honorifics, epithets, or nicknames for characters.
4. "locations and organizations": Places, buildings, realms, sects, clans, guilds, factions, groups.
5. "item names": Weapons, artifacts, tools, equipment, magical items, special objects.
6. "misc": Anything that doesn't fit clearly into the above categories but is still a proper noun.

**INSTRUCTIONS:**
1. Analyze each noun object in the input JSON array
2. For each noun, examine both the hanja (if available and not empty) and hangul
3. Assign the most appropriate category based on the definitions above
4. Return a JSON array of objects with the SAME length and order as the input
5. Each object in the output must have: "hangul", "hanja", "category"

**OUTPUT FORMAT:**
Return a JSON array of objects. Each object must have: "hangul", "hanja", "category"
Example: [{{"hangul": "이소룡", "hanja": "", "category": "character names"}}, {{"hangul": "철산고", "hanja": "鐵山掌", "category": "skills and techniques"}}, {{"hangul": "소림사", "hanja": "少林寺", "category": "locations and organizations"}}]
"""

def categorize_nouns_with_ai(client, noun_list, batch_size=None):
    """Categorize nouns using AI. Returns updated noun list with categories."""
    if batch_size is None:
        batch_size = config_loader.CATEGORIZATION_BATCH_SIZE
    
    if not noun_list:
        return noun_list

    print(f"\n--- Starting AI categorization for {len(noun_list)} nouns ---")
    
    # Track which indices need categorization
    needs_categorization_indices = []
    needs_categorization_items = []
    
    for i, noun in enumerate(noun_list):
        # Check if category is already filled (not None, not empty string, etc.)
        if not noun.get('category'):
            needs_categorization_indices.append(i)
            needs_categorization_items.append(noun)
    
    if not needs_categorization_items:
        print("--- All nouns already categorized, skipping AI ---")
        return noun_list
    
    print(f"  Processing {len(needs_categorization_items)} nouns that need categorization")
    
    # Process only the nouns that need categorization in batches
    for i in range(0, len(needs_categorization_items), batch_size):
        batch_indices = needs_categorization_indices[i:i + batch_size]
        batch_items = needs_categorization_items[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(needs_categorization_items) + batch_size - 1) // batch_size
        
        print(f"  Processing batch {batch_num}/{total_batches} ({len(batch_items)} nouns)")
        
        try:
            # Prepare the input data for the AI
            input_data = []
            for noun in batch_items:
                input_data.append({
                    "hangul": noun.get('hangul', ''),
                    "hanja": noun.get('hanja', '')
                })
            
            # Format the prompt
            prompt = SYSTEM_PROMPT_CATEGORIZATION.format(
                genre_description=config_loader.GENRE_DESCRIPTION,
                categories=json.dumps(config_loader.CATEGORIES)
            )
            
            # Add the input data to the prompt
            full_prompt = f"{prompt}\n\nInput JSON array:\n{json.dumps(input_data, ensure_ascii=False)}"
            
            for attempt in range(config_loader.MAX_RETRIES):
                try:
                    response = client.models.generate_content(
                        model=config_loader.MODEL_NAME,
                        contents=full_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )
                    
                    if response and response.text and response.text.strip():
                        categorized_batch = json.loads(response.text)
                        
                        # Verify the output has the expected format
                        if isinstance(categorized_batch, list) and len(categorized_batch) == len(batch_items):
                            # Update the original noun_list at the correct indices
                            for j, idx in enumerate(batch_indices):
                                noun_list[idx]['category'] = categorized_batch[j].get('category', 'misc')
                            break
                        else:
                            print(f"    Warning: Invalid response format on attempt {attempt + 1}")
                    else:
                        print(f"    Warning: Empty response on attempt {attempt + 1}")
                    
                except Exception as e:
                    print(f"    Error on attempt {attempt + 1}: {e}")
                
                if attempt < config_loader.MAX_RETRIES - 1:
                    time.sleep(config_loader.RETRY_DELAY)
            else:
                # If all retries failed, assign 'misc' category
                print(f"    Failed to categorize batch {batch_num}, assigning 'misc'")
                for idx in batch_indices:
                    noun_list[idx]['category'] = 'misc'
            
            # Small delay between batches
            if i + batch_size < len(needs_categorization_items):
                time.sleep(1)
                
        except Exception as e:
            print(f"  Error processing batch {batch_num}: {e}")
            # Assign 'misc' category to failed batch
            for idx in batch_indices:
                noun_list[idx]['category'] = 'misc'
    
    print("--- AI categorization complete ---")
    return noun_list