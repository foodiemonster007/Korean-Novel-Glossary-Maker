"""
Ambiguity detection module - can be used independently.
"""

import json
import os
import pickle
import requests
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from collections import defaultdict
import hashlib

class AmbiguityDetector:
    def __init__(self, config: Dict[str, Any], master_nouns: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize ambiguity detector.
        Can be used independently by other code.
        """
        self.config = config
        
        # Korean particles
        self.korean_particles = {
            'topic': ['은', '는'],
            'subject': ['이', '가'],
            'object': ['을', '를'],
            'possessive': ['의'],
            'dative': ['에게', '한테'],
            'locative': ['에', '에서'],
            'instrumental': ['으로', '로'],
            'vocative': ['아', '야'],
            'additive': ['도'],
            'conjunction': ['과', '와', '랑']
        }
        
        self.all_particles = []
        for category in self.korean_particles.values():
            self.all_particles.extend(category)
        
        # Punctuation characters (English and Asian)
        self.punctuation_chars = set(
            # English punctuation
            '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~' +
            # Asian punctuation (Korean, Chinese, Japanese)
            '。，、；：「」『』（）［］｛｝【】《》〈〉！？～…・‧' +
            # Additional common punctuation
            '·•―–—′″‘’‚‛"„‟‹›«»¡¿¨´`ˆ˜¯˘˙˚¸˝˛ˇ'
        )
        
        # Dictionary API
        self.dictionary_api = "https://krdict.korean.go.kr/api/search"
        self.api_key = config["api_keys"]["krdict_api_key"]
        
        # Dictionary cache with persistence
        self.cache_dir = Path("local_search/ambiguous")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "dictionary_cache.json"
        self.dict_cache = self._load_dict_cache()
        
        # Ambiguity detection
        self._cohesion_scores: Optional[Dict[str, float]] = None
        
        # Translation lookup from master_nouns
        self.master_nouns = master_nouns or []
        self._translation_cache = self._build_translation_cache()
    
    def _load_dict_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load dictionary cache from JSON file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # Ensure all entries have required fields
                    for word, data in cache_data.items():
                        if 'found' not in data:
                            data['found'] = False
                        if 'is_common' not in data:
                            data['is_common'] = False
                        if 'meanings' not in data:
                            data['meanings'] = []
                        if 'word_type' not in data:
                            data['word_type'] = 'unknown'
                    return cache_data
            except Exception as e:
                print(f"Warning: Could not load dictionary cache: {e}")
                return {}
        return {}
    
    def _save_dict_cache(self):
        """Save dictionary cache to JSON file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.dict_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save dictionary cache: {e}")
    
    def _contains_punctuation(self, text: str) -> bool:
        """
        Check if text contains any punctuation characters.
        
        Args:
            text: The string to check
            
        Returns:
            True if the text contains any punctuation characters, False otherwise
        """
        return any(char in self.punctuation_chars for char in text)
    
    def _build_translation_cache(self) -> Dict[str, str]:
        """Build Korean->English translation cache."""
        cache = {}
        for noun in self.master_nouns:
            hangul = noun.get('hangul', '')
            english = noun.get('english', '')
            if hangul and english and english.strip():
                cache[hangul] = english.strip()
        return cache
    
    def _has_english_translation(self, korean_term: str) -> bool:
        """Check if term has English translation in master_nouns."""
        english = self._translation_cache.get(korean_term, '')
        return bool(english and english.strip())
    
    def _lookup_korean_word(self, word: str) -> Dict[str, Any]:
        """Look up Korean word in dictionary API with persistent caching."""
        # Clean the word for caching
        clean_word = word.strip()
        
        # Check in-memory cache first
        if clean_word in self.dict_cache:
            return self.dict_cache[clean_word]
        
        # Skip dictionary lookup for very short words or special markers
        if not clean_word or clean_word.startswith('##') or len(clean_word) <= 1:
            result = {'found': False, 'is_common': len(clean_word) <= 1, 'meanings': [], 'word_type': 'unknown'}
            self.dict_cache[clean_word] = result
            self._save_dict_cache()
            return result
        
        # Skip API call if no valid API key
        if not self.api_key or self.api_key == "YOUR_KRDICT_API_KEY_HERE":
            result = {'found': False, 'is_common': False, 'meanings': [], 'word_type': 'unknown'}
            self.dict_cache[clean_word] = result
            self._save_dict_cache()
            return result
        
        # Try krdict.py package first
        try:
            import krdict
            from krdict.models import WordResponse
            
            krdict.set_key(self.api_key)
            response = krdict.search(clean_word, raise_api_errors=False)
            
            if isinstance(response, WordResponse) and response.data and response.data.total_results > 0:
                first_result = response.data.results[0]
                meanings = []
                if hasattr(first_result, 'definitions') and first_result.definitions:
                    for definition in first_result.definitions[:3]:
                        meanings.append(definition.definition)
                
                word_type = first_result.pos if hasattr(first_result, 'pos') else 'unknown'
                is_common = word_type in ['명사', 'noun', '대명사', 'pronoun', '형용사', 'adjective', '동사', 'verb'] or len(clean_word) <= 3
                
                result = {'found': True, 'is_common': is_common, 'meanings': meanings, 
                         'word_type': word_type, 'response_type': 'krdict_package'}
                self.dict_cache[clean_word] = result
                self._save_dict_cache()
                return result
        except ImportError:
            pass  # krdict package not available
        except Exception as e:
            print(f"Note: krdict package lookup failed for '{clean_word}': {e}")
            pass
        
        # Fallback to direct API
        try:
            params = {
                'key': self.api_key, 
                'q': clean_word, 
                'translated': 'y', 
                'trans_lang': '1', 
                'part': 'word', 
                'sort': 'popular', 
                'number': 5
            }
            response = requests.get(self.dictionary_api, params=params, timeout=5)
            
            if response.status_code == 200:
                # Try XML
                try:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.content)
                    total_results_elem = root.find('.//total_results')
                    
                    if total_results_elem is not None and total_results_elem.text and int(total_results_elem.text) > 0:
                        meanings = [def_elem.text for def_elem in root.findall('.//definition')[:3] if def_elem.text]
                        pos_elem = root.find('.//pos')
                        word_type = pos_elem.text if pos_elem is not None else 'unknown'
                        is_common = len(clean_word) <= 3 or word_type in ['명사', '대명사', '형용사', '동사']
                        
                        result = {'found': True, 'is_common': is_common, 'meanings': meanings,
                                 'word_type': word_type, 'response_type': 'xml_api'}
                        self.dict_cache[clean_word] = result
                        self._save_dict_cache()
                        return result
                except:
                    # Try JSON
                    try:
                        data = response.json()
                        if 'data' in data and data['data']['total_results'] > 0:
                            first_result = data['data']['results'][0]
                            meanings = [d.get('definition', '') for d in first_result.get('definitions', [])[:3]]
                            word_type = first_result.get('pos', 'unknown')
                            is_common = len(clean_word) <= 3 or word_type in ['명사', '대명사', '형용사', '동사']
                            
                            result = {'found': True, 'is_common': is_common, 'meanings': meanings,
                                     'word_type': word_type, 'response_type': 'json_api'}
                            self.dict_cache[clean_word] = result
                            self._save_dict_cache()
                            return result
                    except:
                        pass
        except Exception as e:
            print(f"Note: API lookup failed for '{clean_word}': {e}")
            pass
        
        # If we get here, word was not found
        result = {'found': False, 'is_common': False, 'meanings': [], 'word_type': 'unknown'}
        self.dict_cache[clean_word] = result
        self._save_dict_cache()
        return result
    
    def _strip_particles_based_on_length(self, hangul: str) -> str:
        """
        Strip particles based on hangul length.
        
        Rules:
        - For 1-2 characters: Never strip particles
        - For 3 characters: Never strip particles
        - For 4+ characters: Strip particles
        """
        clean_hangul = hangul.strip()
        original_length = len(clean_hangul)
        
        # For 1-3 characters: never strip particles
        if original_length <= 3:
            return clean_hangul
        
        # For 4+ characters: strip particles
        for particle in self.all_particles:
            if clean_hangul.endswith(particle):
                stripped = clean_hangul[:-len(particle)]
                # Only strip if it leaves at least 2 characters
                if len(stripped) >= 2:
                    return stripped
        return clean_hangul
    
    def _get_stripped_version_for_comparison(self, hangul: str) -> str:
        """
        Get the stripped version for duplicate comparison.
        This is only used for length > 3 entries.
        """
        clean_hangul = hangul.strip()
        
        # Only strip particles for length > 3 entries
        if len(clean_hangul) > 3:
            for particle in self.all_particles:
                if clean_hangul.endswith(particle):
                    stripped = clean_hangul[:-len(particle)]
                    # Only strip if it leaves at least 2 characters
                    if len(stripped) >= 2:
                        return stripped
        return clean_hangul
    
    def _load_korean_corpus_stats(self):
        """Load pre-trained soynlp model from cache."""
        if self._cohesion_scores is not None:
            return
        
        model_cache_file = self.cache_dir / "soynlp_cohesion_model.pkl"
        
        if model_cache_file.exists():
            try:
                with open(model_cache_file, 'rb') as f:
                    self._cohesion_scores = pickle.load(f)
            except Exception:
                self._cohesion_scores = {}
        else:
            self._cohesion_scores = {}
    
    def _is_collocationally_ambiguous(self, text: str) -> bool:
        """Check if text is a weak collocation using pre-trained stats."""
        if len(text) < 3:
            return False
        
        self._load_korean_corpus_stats()
        
        if not self._cohesion_scores:
            return False
        
        whole_score = self._cohesion_scores.get(text, 0)
        if whole_score >= 0.3:
            return False
        
        for split_point in range(1, len(text)):
            left, right = text[:split_point], text[split_point:]
            left_score = self._cohesion_scores.get(left, 0)
            right_score = self._cohesion_scores.get(right, 0)
            
            if left_score > 0.25 and right_score > 0.25:
                return True
        
        return False
    
    def _ends_with_particle(self, text: str) -> bool:
        """Check if text ends with a Korean particle."""
        return any(text.endswith(particle) for particle in self.all_particles)
    
    def is_entry_ambiguous(self, noun: Dict[str, Any]) -> bool:
        """
        Determine if a single entry is ambiguous.
        
        Rules in order:
        1. If length == 1 → ambiguous (will be removed)
        2. If length >= 3 → NOT ambiguous
        3. If length == 2:
           - If ends with particle → AMBIGUOUS
           - If in blacklist → AMBIGUOUS (even if has English or Hanja)
           - If has English or Hanja → NOT ambiguous (except for blacklist)
           - Otherwise apply normal 2-char ambiguity detection
        """
        hangul = noun.get('hangul', '').strip()
        english = noun.get('english', '').strip()
        hanja = noun.get('hanja', '').strip()
        
        # Clean text for blacklist comparison
        clean_text = hangul.replace('##', '').strip()
        
        # Check length
        hangul_length = len(hangul)
        
        # Rule 1: 1-character entries are ambiguous (will be removed)
        if hangul_length == 1:
            return True
        
        # Rule 2: 3+ character entries are NEVER ambiguous
        if hangul_length >= 3:
            return False
        
        # Rule 3: Only 2-character entries go through ambiguity detection
        # Check blacklist FIRST (even if has English or Hanja)
        blacklist = ['신의', '마의', '개방', '정도', '기도', '화기', '전장', '보도']
        if clean_text in blacklist:
            return True
        
        # Sub-rule: If 2-char entry ends with particle → AMBIGUOUS
        if self._ends_with_particle(hangul):
            return True
        
        # If has English or Hanja, NOT ambiguous (except blacklist which was already handled)
        if english or hanja:
            return False
        
        # Apply existing 2-char ambiguity detection logic
        
        # Check if has English translation in cache
        if self._has_english_translation(clean_text):
            # Note: blacklist already checked above, so return False
            return False
        
        # Dictionary check (uses persistent cache)
        dict_info = self._lookup_korean_word(clean_text)
        if dict_info['found'] and dict_info['is_common']:
            return False
        
        # Corpus cohesion check
        corpus_ambiguous = self._is_collocationally_ambiguous(clean_text)
        
        # Default: ambiguous for 2-character entries (conservative approach)
        return True
    
    def run_ambiguity_detection_on_list(self, nouns_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run ambiguity detection on a list of nouns with duplicate removal.
        
        Steps:
        1. Remove entries with punctuation in hangul (any length)
        2. Remove 1-character entries entirely
        3. Remove duplicates for length > 3 after particle stripping
        4. Mark 2-char entries as ambiguous based on rules
        5. Mark 3+ char entries as NOT ambiguous
        """
        if not nouns_list:
            return nouns_list
        
        print(f"Running ambiguity detection on {len(nouns_list)} nouns...")
        print(f"Dictionary cache contains {len(self.dict_cache)} entries")
        
        # Step 1: Remove entries with punctuation in hangul (any length)
        filtered_nouns = []
        punctuation_count = 0
        for noun in nouns_list:
            hangul = noun.get('hangul', '').strip()
            if not hangul or self._contains_punctuation(hangul):
                punctuation_count += 1
                continue
            filtered_nouns.append(noun)
        
        # Step 2: Remove 1-character entries entirely
        no_punct_nouns = []
        one_char_count = 0
        for noun in filtered_nouns:
            hangul = noun.get('hangul', '').strip()
            if len(hangul) == 1:
                one_char_count += 1
                continue
            no_punct_nouns.append(noun)
        
        # Step 3: Remove duplicates for length > 3 after particle stripping
        # We need to process in order to keep the first occurrence
        seen_stripped = set()
        deduplicated_nouns = []
        duplicate_count = 0
        
        for noun in no_punct_nouns:
            hangul = noun.get('hangul', '').strip()
            
            if len(hangul) > 3:
                # For length > 3, use stripped version for comparison
                stripped_hangul = self._get_stripped_version_for_comparison(hangul)
                
                if stripped_hangul in seen_stripped:
                    duplicate_count += 1
                    continue
                seen_stripped.add(stripped_hangul)
            
            deduplicated_nouns.append(noun)
        
        # Step 4: Apply ambiguity detection
        final_nouns = []
        ambiguous_count = 0
        two_char_count = 0
        three_plus_char_count = 0
        
        for noun in deduplicated_nouns:
            hangul = noun.get('hangul', '').strip()
            hangul_length = len(hangul)
            
            # Create a copy to modify
            processed_noun = noun.copy()
            
            # Apply appropriate rules based on length
            if hangul_length == 2:
                two_char_count += 1
                is_ambiguous = self.is_entry_ambiguous(processed_noun)
                if is_ambiguous:
                    ambiguous_count += 1
            else:  # 3+ characters
                three_plus_char_count += 1
                is_ambiguous = False  # Never ambiguous for 3+ chars
            
            processed_noun['ambiguous'] = is_ambiguous
            
            # Ensure required fields exist
            if 'english' not in processed_noun:
                processed_noun['english'] = ''
            if 'hanja' not in processed_noun:
                processed_noun['hanja'] = ''
            
            final_nouns.append(processed_noun)
        
        # Save cache after processing (in case any new entries were added)
        self._save_dict_cache()
        
        # Statistics
        print(f"Ambiguity detection complete:")
        print(f"  - Total entries kept: {len(final_nouns)}")
        print(f"  - Ambiguous entries: {ambiguous_count}")
        print(f"  - Dictionary cache now contains {len(self.dict_cache)} entries")
        
        if len(final_nouns) > 0:
            print(f"  - Ambiguity rate: {ambiguous_count/len(final_nouns)*100:.1f}%")
        
        return final_nouns

# Public API for other code to use ambiguity detection independently
def detect_ambiguity_for_nouns(nouns_list: List[Dict[str, Any]], config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Public function for other code to use ambiguity detection.
    
    Args:
        nouns_list: List of dictionaries with 'hangul' and optionally 'category' keys
        config: Optional configuration dictionary. If not provided, loads from config.json
    
    Returns:
        List of nouns with added 'ambiguous' boolean field (1-character entries removed)
    """
    if config is None:
        # Load default config
        with open("config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    detector = AmbiguityDetector(config, nouns_list)
    return detector.run_ambiguity_detection_on_list(nouns_list)