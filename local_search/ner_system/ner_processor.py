"""
Korean NER Processor with model loading and basic entity processing.
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from typing import Dict, Any, Optional, List
from ambiguity_detector import AmbiguityDetector

os.environ["TOKENIZERS_PARALLELISM"] = "false"

class KoreanNERProcessor:
    def __init__(self, config: Dict[str, Any], master_nouns: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize the Korean NER processor from configuration.
        """
        self.config = config
        print("Initializing Korean NER Processor")
        
        # Load model - convert to absolute path
        model_path = config["paths"]["model_path"]
        
        # Convert relative path to absolute path
        if not os.path.isabs(model_path):
            # Get the absolute path
            if model_path.startswith('./'):
                model_path = model_path[2:]  # Remove './'
            # If it's still a relative path, join with current directory
            if not os.path.isabs(model_path):
                # Try to find the model path relative to the current file
                import sys
                current_dir = os.path.dirname(os.path.abspath(__file__))
                model_path = os.path.join(current_dir, model_path)
        
        print(f"Loading model from: {model_path}")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path does not exist: {model_path}")
        
        # Try loading with local_files_only=True first
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
            self.model = AutoModelForTokenClassification.from_pretrained(model_path, local_files_only=True)
        except:
            # If that fails, try without local_files_only
            print("Loading model without local_files_only flag...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForTokenClassification.from_pretrained(model_path)
        
        # Set device
        use_gpu = config["processing"]["use_gpu"]
        self.device = 0 if use_gpu and torch.cuda.is_available() else -1
        
        # Initialize NER pipeline
        self.ner_pipeline = pipeline(
            "ner",
            model=self.model,
            tokenizer=self.tokenizer,
            aggregation_strategy="simple",
            device=self.device
        )
        self.ner_pipeline.model.config.return_dict = False
        
        # Initialize ambiguity detector
        self.ambiguity_detector = AmbiguityDetector(config, master_nouns)
        
        print("Korean NER Processor initialized")
    
    def process_batch(self, texts: List[str], batch_size: int = 32):
        """Process a batch of texts through NER pipeline."""
        return self.ner_pipeline(
            texts,
            batch_size=min(batch_size, len(texts)),
            num_workers=0
        )