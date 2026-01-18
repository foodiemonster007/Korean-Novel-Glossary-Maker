# ===============================
# TEXT PROCESSING
# ===============================
"""
Handles text processing, regex extraction, and text manipulation
"""
import os
import re
import json
from system import file_operations, config_loader

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

def remove_duplicates_preserving_data(existing_nouns, new_nouns):
    """
    Remove duplicates, preserving data from existing nouns.
    
    Args:
        existing_nouns: List of existing noun dictionaries
        new_nouns: List of new noun dictionaries
        
    Returns:
        List of unique nouns with preserved data
    """
    unique_nouns = []
    seen_hanguls = set()
    
    # First, add all existing nouns with their data
    for noun in existing_nouns:
        hangul = noun['hangul']
        if hangul not in seen_hanguls:
            unique_nouns.append(noun)
            seen_hanguls.add(hangul)
    
    # Then add new nouns only if not already present
    for noun in new_nouns:
        hangul = noun['hangul']
        if hangul not in seen_hanguls:
            unique_nouns.append(noun)
            seen_hanguls.add(hangul)
    
    return unique_nouns

def extract_nouns_with_regex_all_files(text_files):
    """Extract hanja nouns from entire text corpus using regex and remove duplicates"""
    if not text_files:
        notification.send_notification("Script Failed", 
                                     f"Could not find any text files in '{config_loader.RAWS_FOLDER}'.")
        return False

    # Load existing nouns first to preserve their data
    existing_nouns = file_operations.load_nouns_json()
    if not existing_nouns:
        existing_nouns = []
    
    # Combine all files content for regex extraction
    entire_text = file_operations.combine_files_content(text_files)
    
    # Optional regex extraction based on HANJA_IDENTIFICATION flag
    if config_loader.HANJA_IDENTIFICATION:
        regex_nouns = extract_hanja_nouns_with_regex(entire_text)
        print(f"  Regex found {len(regex_nouns)} potential hanja nouns in entire novel.")
        
        # Prepare new nouns in the correct format with required fields
        new_nouns = []
        for noun_data in regex_nouns:
            new_noun = {
                'hangul': noun_data['hangul'],
                'hanja': noun_data['hanja'],
                'english': '',  # Empty initially
                'category': '',  # Empty initially
                'frequency': 0   # Start at 0
            }
            new_nouns.append(new_noun)
        
        # Use remove_duplicates_preserving_data to handle duplicates
        # This will prioritize existing nouns and only add NEW hanguls
        master_nouns = remove_duplicates_preserving_data(existing_nouns, new_nouns)
        
        # Save progress after regex extraction
        file_operations.save_nouns_json(master_nouns)
        print(f"  Preserved {len(existing_nouns)} existing, added {len(master_nouns) - len(existing_nouns)} new")
    
    return master_nouns, {noun['hangul'] for noun in master_nouns}

def fix_name_misidentification(glossary_entries):
    """
    Fix misidentified Korean names by checking for Korean surnames.
    Updated with complex conditions:
    1. Organization check is highest priority and not subject to dictionary cache
    2. Dictionary cache takes priority - if hangul found in cache, skip processing
    3. For compound surnames: change category on match regardless of original category
    4. For single char surnames: change category only when original category is "misc"
    
    Args:
        glossary_entries: List of glossary entries from local NER
        
    Returns:
        List of corrected glossary entries
    """
    # ===== LOAD DICTIONARY CACHE =====
    dictionary_cache = {}
    cache_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "local_search", "ambiguous", "dictionary_cache.json")
    
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                dictionary_cache = json.load(f)
        else:
            print(f"Warning: Dictionary cache not found at {cache_path}")
    except Exception as e:
        print(f"Warning: Could not load dictionary cache: {e}")
    
    # ===== COMPREHENSIVE SURNAME LIST =====
    all_surnames_raw = [
        '가', '간', '갈', '감', '강', '견', '경', '계', '고', '곡', '공', '곽', '관', '교',
        '구', '국', '궁', '궉', '권', '근', '금', '기', '길', '김', '나', '난', '남', '남궁',
        '낭', '내', '노', '뇌', '다', '단', '담', '당', '대', '도', '독', '독고', '돈', '동',
        '동방', '두', '등', '등정', '라', '란', '랑', '려', '로', '뢰', '류', '리', '림', '마',
        '만', '망절', '매', '맹', '명', '모', '목', '묵', '문', '미', '민', '박', '반', '방',
        '배', '백', '번', '범', '변', '보', '복', '봉', '부', '비', '빈', '빙', '사', '사공',
        '산', '삼', '상', '서', '서문', '석', '선', '선우', '설', '섭', '성', '소', '손', '송',
        '수', '순', '승', '시', '신', '심', '아', '안', '애', '야', '양', '어', '어금', '엄', '일',
        '여', '연', '염', '엽', '영', '예', '오', '옥', '온', '옹', '완', '왕', '요', '용',
        '우', '운', '원', '위', '유', '육', '윤', '은', '음', '이', '인', '임', '자', '장',
        '전', '점', '정', '제', '제갈', '조', '종', '좌', '주', '증', '지', '진', '차', '창',
        '채', '천', '초', '총', '최', '추', '탁', '탄', '탕', '태', '판', '팽', '편', '평',
        '포', '표', '풍', '피', '필', '하', '학', '한', '함', '해', '허', '현', '형', '호',
        '홍', '화', '황', '황목', '황보', '후', '강', '강전', '개', '군', '뇌', '누', '단',
        '돈', '두', '범', '빙', '소봉', '십', '양', '여', '영', '예', '장곡', '저', '준', '검',
        '즙', '초', '춘', '편', '환', '흥', '고이', '명림', '목', '목협', '백', '부여', '사마',
        '소실', '수미', '여', '연', '우', '을', '을지', '조미', '중실', '협', '흑치', '백리',
        '순우', '제오', '동방', '동각', '동곽', '동문', '단목', '공손', '공양', '공야', '공서',
        '관구', '곡량', '황보', '령호', '록리', '려구', '남궁', '구양', '상관', '신도', '사마',
        '사도', '사공', '사구', '태사', '담대', '문인', '우마', '하후', '선우', '서문', '헌원',
        '양자', '악정', '종리', '제갈', '축융', '자거', '좌인', '혁련',
    ]
    
    # Remove duplicates while preserving order
    all_surnames_clean = []
    seen = set()
    for surname in all_surnames_raw:
        if surname not in seen:
            seen.add(surname)
            all_surnames_clean.append(surname)
    
    # Separate into single-character and compound surnames
    single_char_surnames = [s for s in all_surnames_clean if len(s) == 1]
    compound_surnames = [s for s in all_surnames_clean if len(s) >= 2]
    
    # Sort compound surnames by length (longest first) for proper matching
    compound_surnames.sort(key=len, reverse=True)
    
    # Create a combined list for organization checking
    all_surnames_for_check = compound_surnames + single_char_surnames
    
    # ===== PROCESSING LOGIC =====
    corrected_entries = []
    
    for entry in glossary_entries:
        hangul = entry.get('hangul', '')
        current_category = entry.get('category', '')
        
        # ===== 1. HIGHEST PRIORITY: Check for organization suffix =====
        if hangul.endswith('가') or hangul.endswith('세가'):
            is_surname_org = False
            for surname in all_surnames_for_check:
                if hangul.startswith(surname):
                    remaining = hangul[len(surname):]
                    if remaining == '가' or remaining == '세가':
                        corrected_entry = entry.copy()
                        corrected_entry['category'] = 'locations and organizations'
                        corrected_entries.append(corrected_entry)
                        is_surname_org = True
                        break  # Found organization match, break out of surname loop
            
            if is_surname_org:
                continue  # Skip to next entry in glossary_entries loop
        
        # Then check for skills suffix
        skills_suffixes = ['무공', '신공', '마공', '검법', '도법', '창법', '보법', '대법', '진법', '술법', '절맥', '검형', '신장']
        found_skills_match = False
        
        for suffix in skills_suffixes:
            if hangul.endswith(suffix):
                corrected_entry = entry.copy()
                corrected_entry['category'] = 'skills and techniques'
                corrected_entries.append(corrected_entry)
                found_skills_match = True
                break  # Found skills match, break out of skills loop
        
        if found_skills_match:
            continue  # Skip to next entry in glossary_entries loop
        
        # ===== 3. Check dictionary cache - if found, skip processing =====
        if hangul in dictionary_cache:
            corrected_entries.append(entry)
            continue
        
        # ===== 4. Name identification logic (only if not in cache) =====
        corrected_entry = entry.copy()
        hangul_length = len(hangul)
        
        # Check compound surnames (only for length 3 or 4)
        # This applies REGARDLESS of original category
        compound_match = False
        if hangul_length in [3, 4]:
            for compound_surname in compound_surnames:
                if hangul.startswith(compound_surname):
                    corrected_entry['category'] = 'character names'
                    compound_match = True
                    break
        
        # Check single character surnames (only for length 2 or 3)
        # This applies ONLY when original category is "misc"
        # We check this even if we found a compound match (though they shouldn't overlap for same length)
        english_value = entry.get('english', '')
        if not compound_match and (current_category in ["misc", ""]) and hangul_length in [2, 3] and english_value == '':
            for single_surname in single_char_surnames:
                if hangul.startswith(single_surname):
                    corrected_entry['category'] = 'character names'
                    break
        
        corrected_entries.append(corrected_entry)
    
    return corrected_entries

def merge_localglossary_with_masternoun(glossary_path, master_nouns, existing_hanguls):
    """
    Merge local NER glossary with existing master nouns, removing duplicates where
    nouns.json entries take priority.
    
    Args:
        glossary_path: Path to glossary.json from local NER
        master_nouns: Current list of master nouns
        existing_hanguls: Set of existing hangul strings in master_nouns
        
    Returns:
        Updated (master_nouns, existing_hanguls) tuple
    """
    try:
        # Load generated glossary.json
        with open(glossary_path, 'r', encoding='utf-8') as f:
            glossary_entries = json.load(f)
        
        print(f"  Loaded {len(glossary_entries)} entries from local NER model")
        
        # STEP 1: Fix name misidentification before mapping
        print("  Applying name correction...")
        glossary_entries = fix_name_misidentification(glossary_entries)
        
        # STEP 2: Map categories to match master_nouns
        category_map = {
            'NAME': 'character names',
            'TITLE': 'character titles',
            'ORGANIZATION': 'locations and organizations',
            'SKILL': 'skills and techniques',
            'ITEM': 'item names',
            'MISC': 'misc'
        }
        
        # STEP 3: Process glossary entries with master list priority
        new_entries_added = 0
        skipped_duplicates = 0
        merged_entries = []
        
        # Create a dictionary for quick lookup of existing entries
        existing_entries = {noun['hangul']: noun for noun in master_nouns}
        
        # First, preserve all existing master nouns (highest priority)
        merged_entries.extend(master_nouns.copy())
        merged_hanguls = existing_hanguls.copy()
        
        # Process glossary entries
        for entry in glossary_entries:
            hangul = entry['hangul']
            mapped_category = category_map.get(entry['category'], 'misc')
            
            # Create noun entry with ambiguous flag
            noun_entry = {
                'hangul': hangul,
                'hanja': entry.get('hanja', ''),
                'english': entry.get('english', ''),
                'category': mapped_category,
                'frequency': entry.get('frequency', 0),
                'ambiguous': entry.get('ambiguous', False)
            }
            
            # Check if this hangul already exists in master_nouns
            if hangul not in merged_hanguls:
                merged_entries.append(noun_entry)
                merged_hanguls.add(hangul)
                new_entries_added += 1
            else:
                # Entry exists - update ONLY if missing information
                # but preserve existing data
                skipped_duplicates += 1
                
                # Find existing entry and update only ambiguous flag if not present
                for i, existing_noun in enumerate(merged_entries):
                    if existing_noun['hangul'] == hangul:
                        # Only update ambiguous flag if not present in existing entry
                        if 'ambiguous' not in existing_noun:
                            merged_entries[i]['ambiguous'] = noun_entry['ambiguous']
                        
                        # Preserve existing translations, categories, etc.
                        # DO NOT overwrite existing data with glossary data
                        break
        
        print(f"  Added {new_entries_added} new entries from local model")
        print(f"  Skipped {skipped_duplicates} duplicate entries (nouns.json has priority)")
        
        return merged_entries, merged_hanguls
        
    except Exception as e:
        print(f"  Error merging glossary: {e}")
        import traceback
        traceback.print_exc()
        return master_nouns, existing_hanguls