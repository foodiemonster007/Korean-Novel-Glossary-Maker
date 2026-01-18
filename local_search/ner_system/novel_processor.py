"""
Novel file processing and chunk management.
"""

import os
import re
import time
import json
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime
from ner_processor import KoreanNERProcessor

os.environ["TOKENIZERS_PARALLELISM"] = "false"

class NovelProcessor:
    """Handles novel chapter file merging and processing."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.novel_dir = config["paths"]["novel_directory"]
        self.output_dir = config["paths"]["output_directory"]
        self.batch_size = config["processing"].get("batch_size", 32)
        
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(config["paths"]["log_directory"], exist_ok=True)
        
        self.start_time = time.time()
        self.entities_found = 0
        self.chunks_processed = 0
        self.total_chunks = 0
    
    def find_chapter_files(self) -> List[Tuple[int, str]]:
        """Find and sort chapter files."""
        all_files = []
        for root, dirs, files in os.walk(self.novel_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.novel_dir)
                all_files.append((file, file_path, rel_path))
        
        if not all_files:
            raise FileNotFoundError(f"No files found in {self.novel_dir}")
        
        def natural_sort_key(s):
            import re
            return [int(text) if text.isdigit() else text.lower()
                   for text in re.split(r'(\d+)', s)]
        
        all_files.sort(key=lambda x: natural_sort_key(x[0]))
        return [(i+1, file_path) for i, (_, file_path, _) in enumerate(all_files)]
    
    def merge_chapters(self) -> Tuple[str, List[Dict[str, Any]]]:
        """Merge all chapter files into a single text."""
        chapter_files = self.find_chapter_files()
        
        if not chapter_files:
            raise FileNotFoundError(f"No files found in {self.novel_dir}")
        
        print(f"Found {len(chapter_files)} files in novel directory")
        
        merged_text = ""
        chapter_metadata = []
        encoding = self.config["processing"]["encoding"]
        remove_blanks = self.config["processing"]["remove_blank_lines"]
        
        for chapter_num, file_path in chapter_files:
            filename = os.path.basename(file_path)
            
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    chapter_text = f.read()
                
                if remove_blanks:
                    lines = chapter_text.split('\n')
                    lines = [line for line in lines if line.strip()]
                    chapter_text = '\n'.join(lines)
                
                chapter_info = {
                    'number': chapter_num,
                    'filename': filename,
                    'filepath': file_path,
                    'start_pos': len(merged_text),
                    'end_pos': len(merged_text) + len(chapter_text),
                    'length': len(chapter_text)
                }
                chapter_metadata.append(chapter_info)
                merged_text += chapter_text
            except Exception as e:
                print(f"Error reading file {chapter_num} ({filename}): {e}")
                continue
        
        print(f"Read all files. Merged text length: {len(merged_text)} characters")
        return merged_text, chapter_metadata
    
    def create_chunks_with_metadata(self, text: str, chapter_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split text into chunks for batched processing."""
        chunk_size = self.config["processing"]["chunk_size"]
        chunks = []
        
        if len(text) > chunk_size * 4:
            sentences = re.split(r'([。\.\?\!])\s*', text)
            reconstructed_sentences = []
            for i in range(0, len(sentences) - 1, 2):
                if i + 1 < len(sentences):
                    reconstructed_sentences.append(sentences[i] + sentences[i+1])
                else:
                    reconstructed_sentences.append(sentences[i])
            
            if len(sentences) % 2 == 1:
                reconstructed_sentences.append(sentences[-1])
            
            current_chunk = ""
            chunk_start_pos = 0
            chunk_index = 0
            
            for sentence in reconstructed_sentences:
                if not sentence.strip():
                    continue
                    
                if len(current_chunk) + len(sentence) < chunk_size:
                    current_chunk += sentence
                else:
                    if current_chunk.strip():
                        chunk_text = current_chunk.strip()
                        chunks.append({
                            'text': chunk_text,
                            'start_pos': chunk_start_pos,
                            'chunk_index': chunk_index,
                            'length': len(chunk_text)
                        })
                        chunk_start_pos += len(chunk_text)
                        chunk_index += 1
                    current_chunk = sentence
            
            if current_chunk.strip():
                chunk_text = current_chunk.strip()
                chunks.append({
                    'text': chunk_text,
                    'start_pos': chunk_start_pos,
                    'chunk_index': chunk_index,
                    'length': len(chunk_text)
                })
        else:
            if text.strip():
                chunks.append({
                    'text': text,
                    'start_pos': 0,
                    'chunk_index': 0,
                    'length': len(text)
                })
        
        self.total_chunks = len(chunks)
        print(f"Split into {self.total_chunks} chunk(s) for processing")
        return chunks
    
    def process_text_with_progress(self, ner_processor: KoreanNERProcessor, text: str, 
                                   chapter_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process text with batched inference and progress tracking."""    
        chunks = self.create_chunks_with_metadata(text, chapter_metadata)
        all_entities = []
        
        batch_size = self.batch_size
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        print("Starting keyword analysis...")
        print(f"Processing in {total_batches} batches (batch size: {batch_size})")
        
        for batch_idx, batch_start in enumerate(range(0, len(chunks), batch_size)):
            batch_end = min(batch_start + batch_size, len(chunks))
            batch_chunks = chunks[batch_start:batch_end]
            
            if not batch_chunks:
                continue
            
            try:
                batch_predictions = self._process_batch(ner_processor, batch_chunks, batch_size)
                
                for chunk_idx_in_batch, (chunk, chunk_predictions) in enumerate(zip(batch_chunks, batch_predictions)):
                    actual_chunk_idx = batch_start + chunk_idx_in_batch
                    self.chunks_processed = actual_chunk_idx + 1
                    
                    for pred in chunk_predictions:
                        entity_text = pred.get('word', '')
                        entity_type = pred.get('entity_group', 'O')
                        confidence = pred.get('score', 0.0)
                        start = pred.get('start', 0)
                        end = pred.get('end', 0)
                        
                        if entity_type == 'O' or not entity_text:
                            continue
                        
                        if confidence < self.config["output"]["confidence_threshold"]:
                            continue
                        
                        # REMOVED: Particle stripping - will be done later in pipeline
                        cleaned_text = entity_text.strip()
                        cleaned_text = cleaned_text.replace('##', '').strip()
                        
                        # Skip if too short (will be handled in glossary merger)
                        if len(cleaned_text.replace(" ", "")) <= 1:
                            continue
                        
                        chunk_start_pos = chunk['start_pos']
                        absolute_start = chunk_start_pos + start
                        absolute_end = chunk_start_pos + end
                        
                        entity_dict = {
                            'text': cleaned_text,
                            'original_text': entity_text if self.config["output"]["include_original_text"] else None,
                            'type': entity_type,
                            'confidence': float(confidence),
                            'start_pos': absolute_start,
                            'end_pos': absolute_end,
                            'chunk_index': chunk['chunk_index'],
                            'chapter': None,  # Will be set below
                            'chapter_filename': None  # Will be set below
                        }
                        
                        for chapter in chapter_metadata:
                            if chapter['start_pos'] <= absolute_start < chapter['end_pos']:
                                entity_dict['chapter'] = chapter['number']
                                entity_dict['chapter_filename'] = chapter['filename']
                                break
                        
                        all_entities.append(entity_dict)
                        self.entities_found += 1
            
            except Exception as e:
                print(f"\nError processing batch {batch_idx+1}/{total_batches}: {e}")
                print("Processing chunks sequentially for this batch...")
                for chunk in batch_chunks:
                    try:
                        raw_predictions = ner_processor.ner_pipeline(chunk['text'])
                        for pred in raw_predictions:
                            entity_text = pred.get('word', '')
                            entity_type = pred.get('entity_group', 'O')
                            confidence = pred.get('score', 0.0)
                            start = pred.get('start', 0)
                            end = pred.get('end', 0)
                            
                            if entity_type == 'O' or not entity_text:
                                continue
                            
                            if confidence < self.config["output"]["confidence_threshold"]:
                                continue
                            
                            # REMOVED: Particle stripping - will be done later in pipeline
                            cleaned_text = entity_text.strip()
                            cleaned_text = cleaned_text.replace('##', '').strip()
                            
                            # Skip if too short (will be handled in glossary merger)
                            if len(cleaned_text.replace(" ", "")) <= 1:
                                continue
                            
                            chunk_start_pos = chunk['start_pos']
                            absolute_start = chunk_start_pos + start
                            absolute_end = chunk_start_pos + end
                            
                            entity_dict = {
                                'text': cleaned_text,
                                'original_text': entity_text if self.config["output"]["include_original_text"] else None,
                                'type': entity_type,
                                'confidence': float(confidence),
                                'start_pos': absolute_start,
                                'end_pos': absolute_end,
                                'chunk_index': chunk['chunk_index'],
                                'chapter': None,  # Will be set below
                                'chapter_filename': None  # Will be set below
                            }
                            
                            for chapter in chapter_metadata:
                                if chapter['start_pos'] <= absolute_start < chapter['end_pos']:
                                    entity_dict['chapter'] = chapter['number']
                                    entity_dict['chapter_filename'] = chapter['filename']
                                    break
                            
                            all_entities.append(entity_dict)
                            self.entities_found += 1
                    except Exception as chunk_error:
                        print(f"Error processing chunk {chunk['chunk_index']}: {chunk_error}")
                continue
        
        print(f"Keyword analysis completed. Found {self.entities_found} entities total")
        return all_entities
    
    def _process_batch(self, ner_processor: KoreanNERProcessor, batch_chunks: List[Dict[str, Any]], 
                       batch_size: int = 32) -> List[List[Dict[str, Any]]]:
        """Process multiple chunks in batches."""
        if not batch_chunks:
            return []
        
        texts = [chunk['text'] for chunk in batch_chunks]
        valid_texts = []
        valid_indices = []
        
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)
        
        if not valid_texts:
            return [[] for _ in range(len(batch_chunks))]
        
        try:
            predictions = ner_processor.process_batch(
                valid_texts,
                batch_size=min(batch_size, len(valid_texts))
            )
            
            all_predictions = [[] for _ in range(len(batch_chunks))]
            for idx, pred in zip(valid_indices, predictions):
                if isinstance(pred, list):
                    for p in pred:
                        p['chunk_start_pos'] = batch_chunks[idx]['start_pos']
                        p['chunk_index'] = batch_chunks[idx]['chunk_index']
                    all_predictions[idx] = pred
                else:
                    pred['chunk_start_pos'] = batch_chunks[idx]['start_pos']
                    pred['chunk_index'] = batch_chunks[idx]['chunk_index']
                    all_predictions[idx] = [pred]
            
            return all_predictions
            
        except Exception as e:
            print(f"Error in batch processing: {e}")
            print("Falling back to sequential processing for this batch...")
            all_predictions = []
            for chunk in batch_chunks:
                try:
                    pred = ner_processor.ner_pipeline(chunk['text'])
                    if isinstance(pred, list):
                        for p in pred:
                            p['chunk_start_pos'] = chunk['start_pos']
                            p['chunk_index'] = chunk['chunk_index']
                    else:
                        pred['chunk_start_pos'] = chunk['start_pos']
                        pred['chunk_index'] = chunk['chunk_index']
                        pred = [pred]
                    all_predictions.append(pred)
                except Exception as chunk_error:
                    print(f"Error processing chunk {chunk['chunk_index']}: {chunk_error}")
                    all_predictions.append([])
            return all_predictions
    
    def process_novel(self, ner_processor: KoreanNERProcessor) -> Dict[str, Any]:
        """Process the entire novel through NER pipeline."""
        print("\n" + "="*60)
        print("STARTING NOVEL PROCESSING")
        print("="*60)
        
        # Merge chapters
        merged_text, chapter_metadata = self.merge_chapters()
        
        # Process with NER
        all_entities = self.process_text_with_progress(ner_processor, merged_text, chapter_metadata)
        
        # Group entities by chapter if configured
        grouped_by_chapter = None
        if self.config["output"]["group_by_chapter"]:
            grouped_by_chapter = defaultdict(list)
            for entity in all_entities:
                chapter_num = entity.get('chapter', 0)
                grouped_by_chapter[chapter_num].append(entity)
        
        # Create glossary
        glossary = {
            'metadata': {
                'generated_date': datetime.now().isoformat(),
                'total_entities': len(all_entities),
                'total_chapters': len(chapter_metadata),
                'total_text_length': len(merged_text),
                'language': 'Korean',
                'model_used': ner_processor.model.config._name_or_path,
                'processing_time': time.time() - self.start_time,
                'processing_mode': 'batched',
                'batch_size': self.batch_size
            },
            'chapters': chapter_metadata,
            'entities': all_entities,
            'entities_by_chapter': dict(grouped_by_chapter) if grouped_by_chapter else None,
            'merged_text': merged_text
        }
        
        # Statistics
        glossary['statistics'] = {
            'total_count': len(all_entities),
            'average_confidence': sum(e['confidence'] for e in all_entities) / len(all_entities) if all_entities else 0,
            'entities_per_chapter': len(all_entities) / len(chapter_metadata) if chapter_metadata else 0
        }
        
        return glossary
    
    def export_glossary(self, glossary: Dict[str, Any], filename: str = None) -> str:
        """Export glossary to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"novel_glossary_{timestamp}.json"
        
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(glossary, f, ensure_ascii=False, indent=2)
        
        print(f"\nDetailed glossary exported to: {output_path}")
        print(f"  - Total entities: {glossary['metadata']['total_entities']}")
        
        # Export simplified glossary
        self.export_simplified_glossary(glossary)
        
        return output_path
    
    def export_simplified_glossary(self, glossary: Dict[str, Any]) -> str:
        """Export simplified glossary in requested format."""
        simplified_glossary = []
        entity_dict = {}
        
        for entity in glossary['entities']:
            hangul = entity['text']
            category = entity['type']
            
            if not hangul:
                continue
            
            # Basic cleaning
            hangul = hangul.strip()
            
            # Skip 1-character entries (will be filtered later in ambiguity detection)
            if len(hangul.replace(" ", "")) <= 1:
                continue
            
            key = (hangul, category)
            
            if key not in entity_dict:
                entity_dict[key] = {'frequency': 0}
            
            entity_dict[key]['frequency'] += 1
        
        for (hangul, category), data in entity_dict.items():
            entry = {
                'hangul': hangul,
                'hanja': '',
                'english': '',
                'category': category,
                'frequency': data['frequency'],
                'ambiguous': False  # Will be set later by ambiguity detector
            }
            simplified_glossary.append(entry)
        
        simplified_glossary.sort(key=lambda x: (-len(x['hangul']), -x['frequency']))
        
        output_path = os.path.join(self.output_dir, "glossary.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(simplified_glossary, f, ensure_ascii=False, indent=2)
        
        print(f"\nSimplified glossary exported to: {output_path}")
        print(f"  - Unique entries: {len(simplified_glossary)}")
        
        return output_path