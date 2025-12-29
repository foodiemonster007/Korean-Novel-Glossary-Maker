# ===============================
# HANJA GUESSING WITH AI
# ===============================
"""
Guesses missing Hanja characters using AI
"""
import json
import time
from google import genai
from google.genai import types
from system import config_loader

# AI Prompt for hanja guessing
SYSTEM_PROMPT_HANJA_GUESS = """You are an expert in Traditional Chinese characters (Hanja) and Korean language. Your task is to predict the MOST LIKELY Traditional Chinese characters for Korean proper nouns that have missing hanja.

**INPUT:** You will receive a JSON array of noun objects, each with "hangul", "english", "category", and "hanja" fields. Some "hanja" fields may be empty.

**CRITICAL RULES:**
1. **ONLY FILL EMPTY HANJA FIELDS**: Only add Hanja characters to objects where the "hanja" field is currently empty ("")
2. **PRESERVE EXISTING HANJA**: Do not change any objects that already have Hanja characters
3. **USE CONTEXT CLUES**: Use the "hangul", "english", and "category" fields to determine appropriate Hanja

**ANALYSIS APPROACH FOR EACH NOUN WITH EMPTY HANJA:**
1. **USE ENGLISH AS PRIMARY CLUE**: The English translation provides the meaning that needs to be represented in Hanja
2. **USE CATEGORY FOR CHARACTER SELECTION**: The "category" field determines the type of Hanja characters to use
3. **USE HANGUL FOR SOUND CORRESPONDENCE**: The hangul provides the Korean pronunciation that should correspond to the Hanja reading
4. **CONSIDER GENRE CONVENTIONS**: {genre_description} has specific Hanja usage patterns

**CHARACTER SELECTION GUIDELINES BY CATEGORY:**

A. **For "character names" category:**
   - Use STANDARD Korean name Hanja characters that match common surname/given name patterns
   - Examples: 김 → 金, 이 → 李, 박 → 朴, 천희 → 天熙

B. **For "skills and techniques" category:**
   - Use martial arts/magic-appropriate characters
   - Examples: "Iron Mountain Palm" → 鐵山掌, "Flying Sword" → 飛劍

C. **For "character titles" category:**
   - Use honorific/status-appropriate characters
   - Examples: "Sword Saint" → 劍聖, "Martial Lord" → 武尊

D. **For "locations and organizations" category:**
   - Use place/group-appropriate characters
   - Examples: "Shaolin Temple" → 少林寺, "Martial Alliance" → 武林盟

E. **For "item names" category:**
   - Use object/material-appropriate characters
   - Examples: "Clear Wind Sword" → 淸風劍, "Heavenly Demon Sword" → 天魔劍

F. **For "misc" category:**
   - Use characters that best match the English meaning

**INSTRUCTIONS:**
1. Process each noun object in the input JSON array
2. For objects with empty "hanja" field, add appropriate Traditional Chinese characters
3. For objects with existing "hanja", leave them unchanged
4. Return a JSON array of objects with the SAME length and order as the input

**OUTPUT FORMAT:**
Return a JSON array of objects. Each object must have: "hangul", "hanja", "category", "english"
Example: [{{"hangul": "이소룡", "hanja": "李小龙", "category": "character names", "english": "Lee Soryong"}}, {{"hangul": "철산고", "hanja": "鐵山掌", "category": "skills and techniques", "english": "Iron Mountain Palm"}}]
"""

def guess_missing_hanja_with_ai(client, noun_list, batch_size=None):
    """Guess missing hanja using AI. Returns updated noun list with filled hanja."""
    if batch_size is None:
        batch_size = config_loader.HANJA_GUESSING_BATCH_SIZE
    
    if not noun_list:
        return noun_list

    # Track which indices need hanja guessing
    needs_hanja_indices = []
    needs_hanja_items = []
    
    for i, noun in enumerate(noun_list):
        # Check if hanja is already filled (non-empty string) or if no english translation
        if not noun.get('hanja') and noun.get('english'):
            needs_hanja_indices.append(i)
            needs_hanja_items.append(noun)
    
    if not needs_hanja_items:
        print("\n--- All nouns already have hanja, skipping AI hanja guessing ---")
        return noun_list
    
    print(f"\n--- Starting AI hanja guessing for {len(needs_hanja_items)} nouns (skipping {len(noun_list) - len(needs_hanja_items)} already have hanja) ---")
    
    # Process only the nouns that need hanja guessing in batches
    for i in range(0, len(needs_hanja_items), batch_size):
        batch_indices = needs_hanja_indices[i:i + batch_size]
        batch_items = needs_hanja_items[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(needs_hanja_items) + batch_size - 1) // batch_size
        
        print(f"  Processing batch {batch_num}/{total_batches} ({len(batch_items)} nouns)")
        
        try:
            # Prepare the input data for the AI (all fields)
            input_data = []
            for noun in batch_items:
                input_data.append({
                    "hangul": noun.get('hangul', ''),
                    "hanja": noun.get('hanja', ''),
                    "category": noun.get('category', 'misc'),
                    "english": noun.get('english', '')
                })
            
            # Format the prompt with genre description
            prompt = SYSTEM_PROMPT_HANJA_GUESS.format(
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
                        updated_batch = json.loads(response.text)
                        
                        # Verify the output has the expected format
                        if isinstance(updated_batch, list) and len(updated_batch) == len(batch_items):
                            # Update hanja in the original noun_list at the correct indices
                            for j, idx in enumerate(batch_indices):
                                new_hanja = updated_batch[j].get('hanja', '')
                                # Only update if we got a new hanja (not empty)
                                if new_hanja:
                                    noun_list[idx]['hanja'] = new_hanja
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
                # If all retries failed, keep original hanja (which is empty)
                print(f"    Failed to guess hanja for batch {batch_num}")
            
            # Small delay between batches
            if i + batch_size < len(needs_hanja_items):
                time.sleep(1)
                
        except Exception as e:
            print(f"  Error processing batch {batch_num}: {e}")
            # Don't update hanja if there's an error
    
    print("--- AI hanja guessing complete ---")
    return noun_list