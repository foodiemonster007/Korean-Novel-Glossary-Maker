"""
Pipeline orchestration for the complete NER system.
"""

import json
import sys
import os
from typing import List, Dict, Any, Tuple, Optional

# Add the system directory to the path to import frequency_calculation
current_dir = os.path.dirname(os.path.abspath(__file__))
system_dir = os.path.join(current_dir, "..", "..", "system")
if system_dir not in sys.path:
    sys.path.append(system_dir)

try:
    from system import frequency_calculation
    FREQUENCY_CALC_AVAILABLE = True
except ImportError:
    print("Warning: frequency_calculation module not found. Skipping frequency calculation step.")
    FREQUENCY_CALC_AVAILABLE = False

from ner_processor import KoreanNERProcessor
from novel_processor import NovelProcessor
from glossary_merger import merge_glossary_with_master_nouns
from ambiguity_detector import AmbiguityDetector

def run_local_ner_pipeline(master_nouns: Optional[List[Dict[str, Any]]] = None, 
                           config: Optional[Dict[str, Any]] = None) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Run the local NER pipeline.
    
    Args:
        master_nouns: Optional list of existing nouns with translations
        config: Configuration dictionary (passed from main wrapper)
    
    Returns:
        Tuple of (updated_master_nouns, glossary_path) or (None, None) if failed.
    """
    try:
        if config is None:
            # Load default config if not provided (for standalone use)
            from .config import load_config
            config = load_config("config.json")
        
        print("\nRunning local NER pipeline...")
        
        # Ensure directories exist
        os.makedirs(config["paths"]["output_directory"], exist_ok=True)
        os.makedirs(config["paths"]["log_directory"], exist_ok=True)
        
        # Initialize NER processor (with master_nouns for translation cache if needed)
        ner_processor = KoreanNERProcessor(config, master_nouns)
        novel_processor = NovelProcessor(config)
        
        # Process novel
        glossary = novel_processor.process_novel(ner_processor)
        
        # Export simplified glossary
        full_glossary_path = novel_processor.export_simplified_glossary(glossary)
        
        # Load simplified glossary and merge
        simplified_glossary_path = os.path.join(config["paths"]["output_directory"], "glossary.json")
        if os.path.exists(simplified_glossary_path):
            with open(simplified_glossary_path, 'r', encoding='utf-8') as f:
                new_glossary = json.load(f)
            
            # Merge with master_nouns
            updated_master_nouns = merge_glossary_with_master_nouns(new_glossary, master_nouns)

            # Calculate frequencies if module is available
            if FREQUENCY_CALC_AVAILABLE and updated_master_nouns:
                print("\n--- STEP 2a: Calculating frequencies and filtering ---")
                
                # Get merged text from glossary for frequency calculation
                if 'merged_text' in glossary:
                    combined_all_text = glossary['merged_text']
                    print(f"  Using merged text from glossary (length: {len(combined_all_text)} chars)")
                    
                    # Calculate frequencies
                    print(f"  Calculating frequencies for {len(updated_master_nouns)} nouns...")
                    updated_master_nouns = frequency_calculation.calculate_frequencies(updated_master_nouns, combined_all_text)
                    
                    # Filter out nouns with frequency 0
                    before_filter = len(updated_master_nouns)
                    updated_master_nouns = frequency_calculation.filter_zero_frequency(updated_master_nouns)
                    after_filter = len(updated_master_nouns)
                    
                else:
                    print("  Warning: No merged text found in glossary, skipping frequency calculation")
            
            # Create a new ambiguity detector with the updated master_nouns
            print("\n--- STEP 2b: Running ambiguity detection ---")
            ambiguity_detector = AmbiguityDetector(config, updated_master_nouns)
            
            # Run ambiguity detection (removes 1-char entries, marks 2-char entries as ambiguous)
            ambi_master_nouns = ambiguity_detector.run_ambiguity_detection_on_list(updated_master_nouns)

            # Sort the remaining nouns
            final_master_nouns = frequency_calculation.sort_nouns(ambi_master_nouns)            
            
            return final_master_nouns, simplified_glossary_path
        else:
            print(f"Error: Simplified glossary not found at {simplified_glossary_path}")
            return final_master_nouns, full_glossary_path
        
    except Exception as e:
        print(f"Error in local NER pipeline: {e}")
        import traceback
        traceback.print_exc()
        return master_nouns, None