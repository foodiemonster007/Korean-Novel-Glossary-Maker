# ===============================
# HANJA CONVERSION
# ===============================
"""
Converts Traditional Chinese to Simplified Chinese
"""
from opencc import OpenCC

def convert_hanja_to_simplified(hanja_text):
    """Convert Traditional Chinese to Simplified Chinese."""
    if not hanja_text or not hanja_text.strip():
        return ''
    
    try:
        converter = OpenCC('t2s')
        return converter.convert(hanja_text)
    except Exception as e:
        print(f"Error converting hanja '{hanja_text}': {e}")
        return hanja_text