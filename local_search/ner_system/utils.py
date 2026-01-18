"""
Utility functions for the NER system.
"""

import re
from typing import List

def natural_sort_key(s: str) -> List:
    """
    Generate key for natural sorting.
    
    Args:
        s: String to sort
        
    Returns:
        List of parts for sorting
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]