"""
Glossary merging utilities.
"""

from typing import List, Dict, Any, Optional

# Category mapping from NER system to master_nouns format
CATEGORY_MAPPING = {
    "NAME": "character names",
    "SKILL": "skills and techniques", 
    "TITLE": "character titles",
    "ORGANIZATION": "locations and organizations",
    "ITEM": "item names",
    "MISC": "misc"
}

def merge_glossary_with_master_nouns(new_glossary: List[Dict[str, Any]], 
                                     master_nouns: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Merge new glossary entries with existing master_nouns.
    Merging rules:
    1. Merging is based on 'hangul' key only (category doesn't affect merging)
    2. Master_nouns entries have priority (keep their translations and categories)
    3. If same hangul exists in both, keep the master_nouns entry
    4. For NEW entries, map categories from NER format to master_nouns format
    """
    if not master_nouns:
        # If no master_nouns, map all categories in new_glossary
        result = []
        for noun in new_glossary:
            mapped_noun = noun.copy()
            original_category = mapped_noun.get('category', 'MISC')
            mapped_noun['category'] = CATEGORY_MAPPING.get(original_category, 'misc')
            result.append(mapped_noun)
        print(f"No master_nouns provided, returning {len(result)} mapped entries")
        return result
    
    if not new_glossary:
        return master_nouns
    
    # Create lookup dictionary using ONLY hangul as key
    master_lookup = {}
    for noun in master_nouns:
        hangul = noun.get('hangul', '')
        master_lookup[hangul] = noun
    
    merged = []
    
    # Add all master_nouns first (priority - keep their original categories)
    for noun in master_nouns:
        merged.append(noun.copy())
    
    # Process new entries
    new_entries_added = 0
    for new_noun in new_glossary:
        hangul = new_noun.get('hangul', '')
        
        # Check if this hangul already exists in master_nouns (regardless of category)
        if hangul not in master_lookup:
            # Create a copy of the new noun
            mapped_noun = new_noun.copy()
            
            # Map the category from NER format to master_nouns format
            original_category = mapped_noun.get('category', 'MISC')
            mapped_noun['category'] = CATEGORY_MAPPING.get(original_category, 'misc')
            
            merged.append(mapped_noun)
            new_entries_added += 1
    
    print(f"Merged glossary: {len(master_nouns)} master + {new_entries_added} new = {len(merged)} total")
    print(f"  (Skipped {len(new_glossary) - new_entries_added} duplicate hanguls)")
    print(f"  (Category mapping applied to {new_entries_added} new entries)")
    
    return merged