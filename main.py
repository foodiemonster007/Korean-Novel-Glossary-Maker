#!/usr/bin/env python3
"""
MAIN ENTRY POINT FOR NOUN PROCESSING PIPELINE - GUI VERSION
This script orchestrates the entire noun extraction and processing pipeline
"""
import sys
import os
from google import genai

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from system import config_loader, notification, file_operations, text_processing, frequency_calculation, excel_export
from ai_codes import extraction, categorization, translation, hanja_guessing
from system.hanja_conversion import convert_hanja_to_simplified
from local_search.korean_ner_inference import run_local_ner_pipeline
from local_search.ner_system.ambiguity_detector import detect_ambiguity_for_nouns

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

    # STEP 1: Load existing nouns.json (if exists) and optionally merge with reference nouns
    print("\n--- STEP 1: Loading and merging nouns ---")
    
    # Store a copy of the original glossary for SAVE_NEW_ONLY comparison
    original_glossary = []
    
    # Try to load existing nouns.json
    master_nouns = []
    existing_hanguls = set()
    
    try:
        # Load existing nouns.json if it exists
        master_nouns = file_operations.load_nouns_json()
        existing_hanguls = {noun['hangul'] for noun in master_nouns}
        print(f"  Loaded {len(master_nouns)} existing nouns.")
        
        # Store a copy of the original glossary if SAVE_NEW_ONLY is enabled
        if config_loader.SAVE_NEW_ONLY:
            original_glossary = master_nouns.copy()
            print(f"  Stored copy of original glossary ({len(original_glossary)} terms) for reference.")
            
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        # If file doesn't exist or is empty/corrupt, start fresh
        print(f"  No existing json found or error loading: {e}")
        master_nouns = []
        existing_hanguls = set()
    
    # Load reference nouns (optional)
    reference_nouns = file_operations.load_reference_nouns()
    
    if reference_nouns and len(reference_nouns) > 0:        
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
    
    # Get text files
    text_files = file_operations.get_text_files_from_folder(config_loader.RAWS_FOLDER)
    if not text_files:
        notification.send_notification("Script Failed", 
                                     f"Could not find any text files in '{config_loader.RAWS_FOLDER}'.")
        return False

    # Create the Gemini AI client ONCE
    client = genai.Client(api_key=config_loader.API_KEY)

    # STEP 1: Regex extraction on entire text corpus (only if HANJA_IDENTIFICATION is enabled)
    if config_loader.HANJA_IDENTIFICATION:
        print(" - Option: Regex extraction on entire novel text")
        master_nouns, existing_hanguls = text_processing.extract_nouns_with_regex_all_files(text_files)
        
        if master_nouns is False:  # Error occurred
            return False
        
    else:
        print("--- Skipping Step 1: There are no hanja in brackets in the novel text. ---")
        master_nouns = []
        existing_hanguls = set()

    # STEP 2a: Noun extraction based on chosen method
    if config_loader.LOCAL_MODEL:
        print("\n--- STEP 2: Using Local NER Model for entity extraction ---")
        
        # Run local NER model
        print("Running local NER model...")
        updated_master_nouns, glossary_path = run_local_ner_pipeline(master_nouns)
        fixed_master_nouns = text_processing.fix_name_misidentification(updated_master_nouns)
        
        if glossary_path:
            master_nouns = fixed_master_nouns
            file_operations.save_nouns_json(master_nouns)
        else:
            print("WARNING: Local model failed. No nouns found in the text files.")      
            return False
    else:
        # Original Gemini extraction
        print("\n--- STEP 2: AI extraction by chunks (Gemini) ---")
        success, master_nouns, existing_hanguls = extraction.extract_nouns_with_ai_by_chunks(client, text_files, master_nouns, existing_hanguls)

        # STEP 2c: Calculate frequencies and filter out zero-frequency nouns
        print("\n--- STEP 2b: Calculating frequencies and filtering ---")
        # Get combined text for frequency calculation
        all_text_content = []
        for text_file in text_files:
            with open(text_file, 'r', encoding='utf-8') as f:
                all_text_content.append(f.read())
        
        combined_all_text = "\n".join(all_text_content)
        master_nouns = frequency_calculation.calculate_frequencies(master_nouns, combined_all_text)
        
        # Filter out nouns with frequency 0
        master_nouns = frequency_calculation.filter_zero_frequency(master_nouns)

        # STEP 2d: Run ambiguity detection
        print("\n--- STEP 2c: Running ambiguity detection ---")
        
        # Get config for ambiguity detector
        config_for_ambiguity = {"api_keys": {"krdict_api_key": config_loader.DICT_API_KEY or "YOUR_KRDICT_API_KEY_HERE"}        }
        
        # Run ambiguity detection
        master_nouns = detect_ambiguity_for_nouns(master_nouns, config_for_ambiguity)

        # Sort the remaining nouns
        master_nouns = frequency_calculation.sort_nouns(master_nouns)
        file_operations.save_nouns_json(master_nouns)        
        
        if not success:
            print("No nouns found in the text files.")
            notification.send_notification("No Nouns Found", 
                                         "No proper nouns were found in the text files.")
            return False    
    
    # STEP 3: Categorize nouns
    print("\n--- STEP 3: Categorizing nouns with AI ---")
    if config_loader.DO_CATEGORIZATION:
        master_nouns = categorization.categorize_nouns_with_ai(client, master_nouns)
    else:
        print("You chose not to categorize nouns with AI.")
        master_nouns = categorization.fill_blank_category_as_misc(master_nouns)
    file_operations.save_nouns_json(master_nouns)
    
    # STEP 4: Fill English translations
    print("\n--- STEP 4: Translating to English with AI ---")
    if config_loader.DO_TRANSLATION:
        master_nouns = translation.translate_nouns_with_ai(client, master_nouns)
    else:
        print("You chose not to translate to English with AI.")
    file_operations.save_nouns_json(master_nouns)
    
    # STEP 5: Guess missing hanja if GUESS_HANJA is True
    print("\n--- STEP 5: Guessing missing Hanja with AI ---")
    if config_loader.GUESS_HANJA:
        master_nouns = hanja_guessing.guess_missing_hanja_with_ai(client, master_nouns)
        file_operations.save_nouns_json(master_nouns)
    else:
        print("You chose not to guess missing Hanja with AI.")
    
    # STEP 6: Convert to simplified Chinese if SIMPLIFIED_CHINESE_CONVERSION is True
    print("\n--- STEP 6: Converting to Simplified Chinese ---")
    if config_loader.SIMPLIFIED_CHINESE_CONVERSION:
        for noun in master_nouns:
            if noun['hanja']:
                noun['chinese'] = convert_hanja_to_simplified(noun['hanja'])
            else:
                noun['chinese'] = ''
        file_operations.save_nouns_json(master_nouns)
    else:
        print("You chose not to convert to Simplified Chinese.")
    
    # STEP 7: Convert to Excel
    print("\n--- STEP 7: Creating Excel file ---")
    
    # Check if we need to filter out original glossary terms
    if config_loader.SAVE_NEW_ONLY and original_glossary:
        print("  Filtering out terms from original glossary.")
        master_nouns = excel_export.filter_out_original_terms(master_nouns, original_glossary)
        print(f"  After filtering: {len(master_nouns)} new terms remaining")
    
    # Prepare data for Excel
    excel_data = []
    for noun in master_nouns:
        row = {
            'hangul': noun['hangul'],
            'hanja': noun.get('hanja', ''),
            'english': noun.get('english', ''),
            'category': noun.get('category', ''),
            'frequency': noun.get('frequency', 0),
            'ambiguous': noun.get('ambiguous', False)
        }
        
        # Add chinese column if SIMPLIFIED_CHINESE_CONVERSION is True
        if config_loader.SIMPLIFIED_CHINESE_CONVERSION:
            row['chinese'] = noun.get('chinese', '')
        
        excel_data.append(row)
    
    # Export to Excel
    success = excel_export.export_to_excel(excel_data, config_loader.CATEGORIES)
    
    if success:        
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
        print("NOVEL GLOSSARY MAKER COMPLETED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("NOVEL GLOSSARY MAKER HAS FAILED.")
        print("=" * 60)
    
    notification.send_notification("Pipeline Complete!", 
                                 "Noun extraction pipeline has finished.")