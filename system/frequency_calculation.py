# ===============================
# FREQUENCY CALCULATION
# ===============================
"""
Calculates noun frequencies and performs sorting operations
"""
import re

def calculate_frequencies(noun_list, combined_text):
    """Calculate frequencies across all text content, adding to existing frequencies."""
    print("\n--- Performing frequency count across all files ---")
    
    # Clean up the text
    combined_text = re.sub(r'\s+', ' ', combined_text)
    print(f"  Total text length: {len(combined_text):,} characters")
    
    # Count frequencies for each noun
    for noun in noun_list:
        hangul = noun['hangul']
        pattern = re.escape(hangul)
        count = len(re.findall(pattern, combined_text))
        
        # Add to existing frequency if present, otherwise set to new count
        if 'frequency' in noun:
            noun['frequency'] += count
        else:
            noun['frequency'] = count
            
        # Ensure ambiguous field exists (default to False if not)
        if 'ambiguous' not in noun:
            noun['ambiguous'] = False
    
    print("  Frequency count complete.")
    return noun_list

def filter_zero_frequency(noun_list):
    """Remove nouns with frequency 0."""
    filtered = [noun for noun in noun_list if noun.get('frequency', 0) > 0]
    removed = len(noun_list) - len(filtered)
    if removed > 0:
        print(f"  Removed {removed} nouns with frequency 0")
    return filtered

def sort_nouns(noun_list):
    """Sort nouns by ambiguity (False first), then by hangul length (descending), then by frequency (descending)."""
    print("\n--- Sorting nouns by ambiguity, length, and frequency ---")
    
    # Ensure ambiguous field exists for all nouns
    for noun in noun_list:
        if 'ambiguous' not in noun:
            noun['ambiguous'] = False
    
    # Sort by: 1. ambiguous (False first), 2. hangul length (descending), 3. frequency (descending)
    sorted_nouns = sorted(noun_list, 
                         key=lambda x: (x['ambiguous'], len(x['hangul']), x.get('frequency', 0)), 
                         reverse=False)  # False comes before True, so we don't reverse for ambiguity
    
    # For length and frequency within each ambiguity group, we want descending
    # We'll do a two-pass sort to get the exact order we want
    def sort_key(noun):
        # Return a tuple where:
        # 1. ambiguous: False (0) sorts before True (1)
        # 2. length: negative so longer sorts first (descending)
        # 3. frequency: negative so higher sorts first (descending)
        ambiguous_val = 1 if noun['ambiguous'] else 0
        return (ambiguous_val, -len(noun['hangul']), -noun.get('frequency', 0))
    
    sorted_nouns = sorted(noun_list, key=sort_key)
    
    print(f"  Sorted {len(sorted_nouns)} nouns")
    
    # Show some statistics
    ambiguous_count = sum(1 for noun in sorted_nouns if noun['ambiguous'])
    clear_count = len(sorted_nouns) - ambiguous_count
    print(f"  Clear entries: {clear_count}, Ambiguous entries: {ambiguous_count}")
    
    return sorted_nouns