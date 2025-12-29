# ===============================
# TEXT PROCESSING
# ===============================
"""
Handles text processing, regex extraction, and text manipulation
"""
import re

def extract_hanja_nouns_with_regex(text):
    """Extract nouns with Hangul and Hanja using regex."""
    pattern = r'([가-힣]+)\s*\(([一-龯\u4e00-\u9fff豈舘]+)\)'
    found_nouns = {}

    for hangul, hanja in re.findall(pattern, text):
        if len(hangul) == 1:
            continue
            
        if len(hangul) == len(hanja):
            if hangul not in found_nouns:
                found_nouns[hangul] = {
                    'hangul': hangul,
                    'hanja': hanja,
                    'english': ''
                }
    return list(found_nouns.values())