# ===============================
# FILE OPERATIONS
# ===============================
"""
Handles file reading, writing, and file system operations
"""
import os
import re
import json
import time
from system import config_loader

def save_nouns_json(nouns_list, filename=None):
    """Save nouns list to JSON file."""
    if filename is None:
        filename = config_loader.NOUNS_JSON_FILE
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(nouns_list, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(nouns_list)} nouns to {filename}")
    except Exception as e:
        print(f"Error saving JSON: {e}")

def load_nouns_json(filename=None):
    """Load nouns list from JSON file."""
    if filename is None:
        filename = config_loader.NOUNS_JSON_FILE
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                nouns = json.load(f)
            print(f"Loaded {len(nouns)} nouns from {filename}")
            return nouns
        except Exception as e:
            print(f"Error loading JSON: {e}")
    return []

def load_reference_nouns():
    """Load reference nouns from Excel file and convert to noun objects."""
    reference_file = config_loader.REFERENCE_FILE
    
    if not reference_file or not os.path.exists(reference_file):
        print(f"No reference file found or specified. Skipping reference loading.")
        return []
    
    try:
        import pandas as pd
        df_ref = pd.read_excel(reference_file)
        reference_nouns = []
        
        # Try to find the correct column names
        hangul_col = None
        hanja_col = None
        english_col = None
        category_col = None
        
        for col in df_ref.columns:
            col_lower = str(col).lower()
            if 'hangul' in col_lower or '한글' in col_lower:
                hangul_col = col
            elif 'hanja' in col_lower or '한자' in col_lower or 'chinese' in col_lower:
                hanja_col = col
            elif 'english' in col_lower or '영어' in col_lower or 'translation' in col_lower:
                english_col = col
            elif 'category' in col_lower or '카테고리' in col_lower or 'type' in col_lower:
                category_col = col
        
        if not hangul_col:
            print(f"No hangul column found in reference file '{reference_file}'")
            return []
        
        # Create noun objects from each row
        for _, row in df_ref.iterrows():
            hangul = str(row[hangul_col]).strip()
            if hangul and hangul.lower() != 'nan' and len(hangul) > 1:
                noun_obj = {
                    'hangul': hangul,
                    'hanja': str(row[hanja_col]).strip() if hanja_col and pd.notna(row.get(hanja_col, '')) else '',
                    'english': str(row[english_col]).strip() if english_col and pd.notna(row.get(english_col, '')) else '',
                    'category': str(row[category_col]).strip() if category_col and pd.notna(row.get(category_col, '')) else '',
                    'frequency': 0  # Initialize with 0, will be calculated later
                }
                reference_nouns.append(noun_obj)
        
        print(f"Loaded {len(reference_nouns)} reference nouns from '{reference_file}'")
        return reference_nouns
        
    except Exception as e:
        print(f"Error loading reference file '{reference_file}': {e}")
        return []

def get_text_files_from_folder(folder_path=None):
    """Get all text files from the folder and sort them numerically."""
    if folder_path is None:
        folder_path = config_loader.RAWS_FOLDER
    
    text_files = []
    
    if not os.path.exists(folder_path):
        print(f"Error: The folder '{folder_path}' was not found.")
        return None
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt'):
            match = re.match(r'(\d+)\.txt$', filename)
            if match:
                num = int(match.group(1))
                text_files.append((num, filename))
    
    text_files.sort(key=lambda x: x[0])
    sorted_files = [os.path.join(folder_path, filename) for _, filename in text_files]
    
    print(f"Found {len(sorted_files)} text files in '{folder_path}'.")
    return sorted_files

def group_files_into_chunks(file_list, chunk_size=None):
    """Group files into chunks of specified size."""
    if chunk_size is None:
        chunk_size = config_loader.CHUNK_SIZE
    
    chunks = []
    for i in range(0, len(file_list), chunk_size):
        chunk = file_list[i:i + chunk_size]
        chunks.append(chunk)
    return chunks

def combine_files_content(file_paths):
    """Read and combine content from multiple files."""
    combined_content = []
    
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                combined_content.append(content)
        except Exception as e:
            print(f"  Warning: Could not read file {file_path}: {e}")
            continue
    
    return "\n".join(combined_content)

def get_filename(file_path):
    """Extract filename from full path."""
    return os.path.basename(file_path)

def log_error(chunk_index, error_message, error_log=None):
    """Log error to error log file."""
    if error_log is None:
        error_log = config_loader.ERROR_LOG
    
    with open(error_log, 'a', encoding='utf-8') as f:
        f.write(f"--- Chunk {chunk_index} Failed ---\n")
        f.write(f"Timestamp: {time.ctime()}\n")
        f.write(f"Error: {str(error_message)}\n\n")