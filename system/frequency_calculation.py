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
    """Sort nouns first by length of hangul (descending), then by frequency (descending)."""
    print("\n--- Sorting nouns by length and frequency ---")
    
    # Sort by hangul length (descending) then frequency (descending)
    sorted_nouns = sorted(noun_list, 
                         key=lambda x: (len(x['hangul']), x.get('frequency', 0)), 
                         reverse=True)
    
    print(f"  Sorted {len(sorted_nouns)} nouns")
    return sorted_nouns

