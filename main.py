#!/usr/bin/env python3
"""
MAIN ENTRY POINT FOR NOUN PROCESSING PIPELINE - GUI VERSION
This script orchestrates the entire noun extraction and processing pipeline
"""
import sys
import os
from google import genai

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from system import config_loader, notification
from system import file_operations, text_processing, frequency_calculation, excel_export
from ai_codes import extraction, categorization, translation, hanja_guessing
from system.hanja_conversion import convert_hanja_to_simplified

def run_noun_extraction_pipeline():
    """Main function for the noun extraction pipeline."""
    print("=" * 60)
    print("STARTING NOUN EXTRACTION PIPELINE")
    print(f"Genre: {config_loader.GENRE} ({config_loader.GENRE_DESCRIPTION})")
    print("=" * 60)
    
    if config_loader.API_KEY == "" or config_loader.API_KEY == "YOUR_API_KEY_HERE":
        print("🚨 Error: Please set your Google AI API key in the configuration.")
        notification.send_notification("API Key Missing", "Please set your Google AI API key.")
        return False

    # STEP 0: Load existing nouns.json (if exists) and optionally merge with reference nouns
    print("\n--- STEP 0: Loading and merging nouns ---")
    
    # Try to load existing nouns.json
    master_nouns = []
    existing_hanguls = set()
    
    try:
        # Load existing nouns.json if it exists
        master_nouns = file_operations.load_nouns_json()
        existing_hanguls = {noun['hangul'] for noun in master_nouns}
        print(f"  Loaded {len(master_nouns)} existing nouns from nouns.json")
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        # If file doesn't exist or is empty/corrupt, start fresh
        print(f"  No existing nouns.json found or error loading: {e}")
        master_nouns = []
        existing_hanguls = set()
    
    # Load reference nouns (optional)
    reference_nouns = file_operations.load_reference_nouns()
    
    if reference_nouns and len(reference_nouns) > 0:
        print(f"  Loaded {len(reference_nouns)} nouns from reference file")
        
        # Add reference nouns that aren't already in master_nouns
        new_noun_count = 0
        for noun in reference_nouns:
            hangul = noun['hangul']
            
            if hangul not in existing_hanguls:
                # Ensure all required fields exist
                if 'frequency' not in noun:
                    noun['frequency'] = 0
                if 'hanja' not in noun:
                    noun['hanja'] = ''
                if 'english' not in noun:
                    noun['english'] = ''
                if 'category' not in noun:
                    noun['category'] = ''
                
                master_nouns.append(noun)
                existing_hanguls.add(hangul)
                new_noun_count += 1
        
        print(f"  Added {new_noun_count} new nouns from reference file")
    else:
        print("  No reference nouns found or reference file is empty")
    
    # Save merged nouns (even if no reference nouns were added)
    file_operations.save_nouns_json(master_nouns)
    print(f"  Total: {len(master_nouns)} nouns in master list")
    
    # Get text files
    text_files = file_operations.get_text_files_from_folder(config_loader.RAWS_FOLDER)
    if not text_files:
        notification.send_notification("Script Failed", 
                                     f"Could not find any text files in '{config_loader.RAWS_FOLDER}'.")
        return False

    file_chunks = file_operations.group_files_into_chunks(text_files, config_loader.CHUNK_SIZE)
    print(f"Grouped files into {len(file_chunks)} chunks of up to {config_loader.CHUNK_SIZE} files each.")

    client = genai.Client(api_key=config_loader.API_KEY)
    all_text_content = []
    
    # STEP 1: Identify nouns (with optional regex hanja identification)
    for i, file_chunk in enumerate(file_chunks):
        print(f"\n--- Processing chunk {i+1}/{len(file_chunks)} ---")
        print(f"  Files: {[file_operations.get_filename(f) for f in file_chunk]}")
        
        chunk_text = file_operations.combine_files_content(file_chunk)
        all_text_content.append(chunk_text)
        
        # Optional regex extraction based on HANJA_IDENTIFICATION flag
        if config_loader.HANJA_IDENTIFICATION:
            regex_nouns = text_processing.extract_hanja_nouns_with_regex(chunk_text)
            for noun_data in regex_nouns:
                hangul = noun_data['hangul']
                if hangul not in existing_hanguls:
                    # Convert to the format with hangul and hanja keys
                    new_noun = {
                        'hangul': hangul,
                        'hanja': noun_data['hanja'],
                        'english': '',
                        'category': '',
                        'frequency': 0
                    }
                    master_nouns.append(new_noun)
                    existing_hanguls.add(hangul)
            if regex_nouns:
                print(f"  Regex found {len(regex_nouns)} hanja nouns.")
        
        # AI noun extraction with duplicate checking
        api_nouns = extraction.get_nouns_from_api_with_retries(client, chunk_text, i + 1, existing_hanguls)
        
        if api_nouns:
            for noun_data in api_nouns:
                # Create a new noun object (no duplicate check needed - already done in extraction.py)
                new_noun = {
                    'hangul': noun_data['hangul'],
                    'hanja': noun_data['hanja'],
                    'english': '',
                    'category': '',
                    'frequency': 0
                }
                master_nouns.append(new_noun)
                existing_hanguls.add(noun_data['hangul'])
            
            print(f"  AI discovered {len(api_nouns)} new nouns.")
        
        # Save progress after each chunk
        file_operations.save_nouns_json(master_nouns)

    if not master_nouns:
        print("No nouns found in the text files.")
        notification.send_notification("No Nouns Found", "No proper nouns were found in the text files.")
        return False
    
    # STEP 2: Calculate frequencies and filter out zero-frequency nouns
    print("\n--- STEP 2: Calculating frequencies and filtering ---")
    combined_all_text = "\n".join(all_text_content)
    master_nouns = frequency_calculation.calculate_frequencies(master_nouns, combined_all_text)
        
    # Filter out nouns with frequency 0 (including reference nouns) using the function
    master_nouns = frequency_calculation.filter_zero_frequency(master_nouns)
        
    # Sort the remaining nouns
    master_nouns = frequency_calculation.sort_nouns(master_nouns)
    file_operations.save_nouns_json(master_nouns)
    
    # STEP 3: Categorize nouns
    print("\n--- STEP 3: Categorizing nouns ---")
    master_nouns = categorization.categorize_nouns_with_ai(client, master_nouns)
    file_operations.save_nouns_json(master_nouns)
    
    # STEP 4: Add empty english keys
    print("\n--- STEP 4: Adding English keys ---")
    added_count = 0
    for noun in master_nouns:
        if 'english' not in noun:
            noun['english'] = ''
            added_count += 1
    print(f"  Added English keys to {added_count} nouns that didn't have them")
    file_operations.save_nouns_json(master_nouns)
    
    # STEP 5: Fill English translations
    print("\n--- STEP 5: Translating to English ---")
    master_nouns = translation.translate_nouns_with_ai(client, master_nouns)
    file_operations.save_nouns_json(master_nouns)
    
    # STEP 6: Guess missing hanja if GUESS_HANJA is True
    if config_loader.GUESS_HANJA:
        print("\n--- STEP 6: Guessing missing Hanja ---")
        master_nouns = hanja_guessing.guess_missing_hanja_with_ai(client, master_nouns)
        file_operations.save_nouns_json(master_nouns)
    
    # STEP 7: Convert to simplified Chinese if SIMPLIFIED_CHINESE_CONVERSION is True
    if config_loader.SIMPLIFIED_CHINESE_CONVERSION:
        print("\n--- STEP 7: Converting to Simplified Chinese ---")
        for noun in master_nouns:
            if noun['hanja']:
                noun['chinese'] = convert_hanja_to_simplified(noun['hanja'])
            else:
                noun['chinese'] = ''
        file_operations.save_nouns_json(master_nouns)
    
    # STEP 8: Convert to Excel
    print("\n--- STEP 8: Creating Excel file ---")
    
    # Prepare data for Excel
    excel_data = []
    for noun in master_nouns:
        row = {
            'hangul': noun['hangul'],
            'hanja': noun.get('hanja', ''),
            'english': noun.get('english', ''),
            'category': noun.get('category', ''),
            'frequency': noun.get('frequency', 0)
        }
        
        # Add chinese column if SIMPLIFIED_CHINESE_CONVERSION is True
        if config_loader.SIMPLIFIED_CHINESE_CONVERSION:
            row['chinese'] = noun.get('chinese', '')
        
        excel_data.append(row)
    
    # Export to Excel
    success = excel_export.export_to_excel(excel_data, config_loader.CATEGORIES)
    
    if success:
        print(f"\n📊 Final Statistics:")
        print(f"   Total nouns: {len(master_nouns)}")
        for category in config_loader.CATEGORIES:
            count = sum(1 for noun in master_nouns if noun.get('category') == category)
            if count > 0:
                print(f"   - {category}: {count}")
        
        notification.send_notification("Noun Processing Complete!", 
                                     f"Processed {len(master_nouns)} nouns into {config_loader.OUTPUT_EXCEL}")
        return True
    else:
        return False

# This allows running the pipeline directly from command line if needed
if __name__ == "__main__":
    success = run_noun_extraction_pipeline()
    
    if success:
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("PIPELINE FAILED!")
        print("=" * 60)
    
    notification.send_notification("Pipeline Complete!", 

                                 "Noun extraction pipeline has finished.")

