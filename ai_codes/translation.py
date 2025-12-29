# ===============================
# NOUN TRANSLATION WITH AI
# ===============================
"""
Translates nouns to English using AI
"""
import json
import time
from google import genai
from google.genai import types
from system import config_loader

# AI Prompt for translation
SYSTEM_PROMPT_TRANSLATION = """You are an expert translator specializing in {genre_description} terminology. Your task is to provide ACCURATE English translations for each proper noun.

**INPUT:** You will receive a JSON array of noun objects, each with "hangul", "hanja", and "category" fields.

**CRITICAL TRANSLATION RULES:**

1. **SOURCE PRIORITY ORDER FOR EACH NOUN:**
   - FIRST PRIORITY: Translate from HANJA if it is available and not empty
   - SECOND PRIORITY: Translate from Hangul if Hanja is empty
   - Use the "category" field as CRUCIAL context for choosing the right translation approach

2. **TRANSLATION BY CATEGORY:**

   A. **"character names" category:**
      - Provide ROMANIZATION (transliteration) ONLY
      - Format: "FamilyName GivenName" with exactly ONE space between names
      - NO DASHES, NO PERIODS, NO ADDITIONAL PUNCTUATION
      - Examples: "김천희" → "Kim Cheonhee", "남궁하얀" → "Namgung Hayan", "존 스미스" → "John Smith", "무하메드 알리" → "Muhammad Ali"

   B. **ALL OTHER CATEGORIES (skills and techniques, character titles, locations and organizations, item names, misc):**
      - Provide ACTUAL ENGLISH TRANSLATION of the meaning
      - DO NOT provide romanization
      - Translate the semantic meaning accurately
      - Use genre-appropriate terminology for {genre_description}
      - Examples: 
        - "철산고" (鐵山掌) → "Iron Mountain Palm"
        - "소림사" (少林寺) → "Shaolin Temple"
        - "검성" (劍聖) → "Sword Saint"

3. **GENERAL RULES:**
   - Never include romanized Hangul in parentheses or brackets
   - Never add explanations or notes
   - For multi-word terms, translate the entire concept appropriately

**INSTRUCTIONS:**
1. Process each noun object in the input JSON array
2. For each noun, follow the source priority order and category-specific rules above
3. Add an "english" field to each object with the translation
4. Return a JSON array of objects with the SAME length and order as the input

**OUTPUT FORMAT:**
Return a JSON array of objects. Each object must have: "hangul", "hanja", "category", "english"
Example: [{{"hangul": "이소룡", "hanja": "", "category": "character names", "english": "Lee Soryong"}}, {{"hangul": "철산고", "hanja": "鐵山掌", "category": "skills and techniques", "english": "Iron Mountain Palm"}}]
"""

def translate_nouns_with_ai(client, noun_list, batch_size=None):
    """Translate nouns using AI. Returns updated noun list with english translations."""
    if batch_size is None:
        batch_size = config_loader.TRANSLATION_BATCH_SIZE
    
    if not noun_list:
        return noun_list

    # Track which indices need translation
    needs_translation_indices = []
    needs_translation_items = []
    
    for i, noun in enumerate(noun_list):
        # Check if english is already filled (non-empty string)
        if not noun.get('english'):
            needs_translation_indices.append(i)
            needs_translation_items.append(noun)
    
    if not needs_translation_items:
        print("\n--- All nouns already translated, skipping AI translation ---")
        return noun_list
    
    print(f"\n--- Starting AI translation for {len(needs_translation_items)} nouns (skipping {len(noun_list) - len(needs_translation_items)} already translated) ---")
    
    # Process only the nouns that need translation in batches
    for i in range(0, len(needs_translation_items), batch_size):
        batch_indices = needs_translation_indices[i:i + batch_size]
        batch_items = needs_translation_items[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(needs_translation_items) + batch_size - 1) // batch_size
        
        print(f"  Processing batch {batch_num}/{total_batches} ({len(batch_items)} nouns)")
        
        try:
            # Prepare the input data for the AI
            input_data = []
            for noun in batch_items:
                input_data.append({
                    "hangul": noun.get('hangul', ''),
                    "hanja": noun.get('hanja', ''),
                    "category": noun.get('category', 'misc')
                })
            
            # Format the prompt with genre description
            prompt = SYSTEM_PROMPT_TRANSLATION.format(
                genre_description=config_loader.GENRE_DESCRIPTION
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
                        translated_batch = json.loads(response.text)
                        
                        # Verify the output has the expected format
                        if isinstance(translated_batch, list) and len(translated_batch) == len(batch_items):
                            # Update the original noun_list at the correct indices
                            for j, idx in enumerate(batch_indices):
                                english = translated_batch[j].get('english', '')
                                noun_list[idx]['english'] = english
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
                # If all retries failed, leave english empty
                print(f"    Failed to translate batch {batch_num}")
            
            # Small delay between batches
            if i + batch_size < len(needs_translation_items):
                time.sleep(1)
                
        except Exception as e:
            print(f"  Error processing batch {batch_num}: {e}")
    
    print("--- AI translation complete ---")
    return noun_list