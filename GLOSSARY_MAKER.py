#!/usr/bin/env python3
"""
GUI for Korean Novel Glossary Maker
Provides interface to configure and run the noun extraction pipeline
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import threading
import sys
import os
import io
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our pipeline
from main import run_noun_extraction_pipeline
from system import config_loader

class NounProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Korean Novel Glossary Maker")
        self.root.geometry("900x700")
        
        # Create a notebook (tab control)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.tab_main = ttk.Frame(self.notebook)
        self.tab_ai = ttk.Frame(self.notebook)
        self.tab_log = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_main, text='Main Settings')
        self.notebook.add(self.tab_ai, text='AI Settings')
        self.notebook.add(self.tab_log, text='Log Output')
        
        # Load current configuration
        self.config = self.load_config()
        
        # Create tab contents
        self.create_main_tab()
        self.create_ai_tab()
        self.create_log_tab()
        
        # Create control buttons frame
        self.create_control_buttons()
        
        # Redirect stdout to log
        self.redirect_stdout()
        
        # Set up closing handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def redirect_stdout(self):
        """Redirect stdout to the log text widget"""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
    
    def write(self, text):
        """Write text to log widget"""
        self.log_text.configure(state='normal')
        self.log_text.insert('end', text)
        self.log_text.see('end')
        self.log_text.configure(state='disabled')
        
    def flush(self):
        """Required for stdout redirection"""
        pass
    
    def load_config(self):
        """Load configuration from config.json"""
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"Loaded configuration from {config_path}")
                return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.get_default_config()
        else:
            print("config.json not found, using default configuration")
            return self.get_default_config()
    
    def get_default_config(self):
        """Return default configuration"""
        return {
            "API_KEY": "",
            "MODEL_NAME": "gemini-2.5-pro",
            "RAWS_FOLDER": "raws",
            "REFERENCE_FILE": "",
            "OUTPUT_EXCEL": "nouns_replace.xlsx",
            "CHAPTERS_ANALYZED": 5,
            "CATEGORIZATION_BATCH_SIZE": 20,
            "TRANSLATION_BATCH_SIZE": 15,
            "HANJA_GUESSING_BATCH_SIZE": 15,
            "MAX_RETRIES": 10,
            "RETRY_DELAY": 30,
            "HANJA_IDENTIFICATION": True,
            "GUESS_HANJA": True,
            "SIMPLIFIED_CHINESE_CONVERSION": True,
            "GENRE": "murim"
        }
    
    def create_main_tab(self):
        """Create main settings tab"""
        # Create frame with scrollbar
        main_frame = ttk.Frame(self.tab_main)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # API Key
        row = 0
        ttk.Label(scrollable_frame, text="API Key:").grid(row=row, column=0, sticky='w', pady=5)
        self.api_key_var = tk.StringVar(value=self.config.get("API_KEY", ""))
        api_key_entry = ttk.Entry(scrollable_frame, textvariable=self.api_key_var, width=50, show="*")
        api_key_entry.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # Model Name
        ttk.Label(scrollable_frame, text="Model Name:").grid(row=row, column=0, sticky='w', pady=5)
        self.model_var = tk.StringVar(value=self.config.get("MODEL_NAME", "gemini-2.5-pro"))
        model_entry = ttk.Entry(scrollable_frame, textvariable=self.model_var, width=50)
        model_entry.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # RAWS Folder
        ttk.Label(scrollable_frame, text="RAWS Folder:").grid(row=row, column=0, sticky='w', pady=5)
        self.raws_folder_var = tk.StringVar(value=self.config.get("RAWS_FOLDER", "raws"))
        raws_entry = ttk.Entry(scrollable_frame, textvariable=self.raws_folder_var, width=40)
        raws_entry.grid(row=row, column=1, sticky='w', pady=5)
        ttk.Button(scrollable_frame, text="Browse", command=self.browse_raws_folder).grid(row=row, column=2, padx=5)
        row += 1
        
        # Reference File
        ttk.Label(scrollable_frame, text="Reference File (optional):").grid(row=row, column=0, sticky='w', pady=5)
        self.reference_var = tk.StringVar(value=self.config.get("REFERENCE_FILE", ""))
        reference_entry = ttk.Entry(scrollable_frame, textvariable=self.reference_var, width=40)
        reference_entry.grid(row=row, column=1, sticky='w', pady=5)
        ttk.Button(scrollable_frame, text="Browse", command=self.browse_reference_file).grid(row=row, column=2, padx=5)
        row += 1
        
        # Output Excel
        ttk.Label(scrollable_frame, text="Output Excel:").grid(row=row, column=0, sticky='w', pady=5)
        self.output_var = tk.StringVar(value=self.config.get("OUTPUT_EXCEL", "nouns_replace.xlsx"))
        output_entry = ttk.Entry(scrollable_frame, textvariable=self.output_var, width=40)
        output_entry.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # Genre
        ttk.Label(scrollable_frame, text="Genre:").grid(row=row, column=0, sticky='w', pady=5)
        self.genre_var = tk.StringVar(value=self.config.get("GENRE", "murim"))
        genre_combo = ttk.Combobox(scrollable_frame, textvariable=self.genre_var, width=20, state="readonly")
        genre_combo['values'] = ("murim", "rofan", "modern", "game", "westfan", "dungeon")
        genre_combo.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # Checkboxes frame
        checkbox_frame = ttk.LabelFrame(scrollable_frame, text="Processing Options")
        checkbox_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=10, padx=5)
        checkbox_frame.grid_columnconfigure(0, weight=1)
        
        # HANJA_IDENTIFICATION
        self.hanja_id_var = tk.BooleanVar(value=self.config.get("HANJA_IDENTIFICATION", True))
        ttk.Checkbutton(checkbox_frame, text="Check this if the text has hanja in the format 천마(天魔)", variable=self.hanja_id_var).pack(anchor='w', pady=2)
        
        # GUESS_HANJA
        self.guess_hanja_var = tk.BooleanVar(value=self.config.get("GUESS_HANJA", True))
        ttk.Checkbutton(checkbox_frame, text="Check if you want AI to guess what the missing hanja is", variable=self.guess_hanja_var).pack(anchor='w', pady=2)
        
        # SIMPLIFIED_CHINESE_CONVERSION
        self.simplified_var = tk.BooleanVar(value=self.config.get("SIMPLIFIED_CHINESE_CONVERSION", True))
        ttk.Checkbutton(checkbox_frame, text="Check if you want to convert hanja to simplified chinese", variable=self.simplified_var).pack(anchor='w', pady=2)
        
        # Add some padding at the bottom
        ttk.Label(scrollable_frame, text="").grid(row=row+1, column=0, pady=20)
    
    def create_ai_tab(self):
        """Create AI settings tab"""
        # Create frame with scrollbar
        ai_frame = ttk.Frame(self.tab_ai)
        ai_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(ai_frame)
        scrollbar = ttk.Scrollbar(ai_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # CHAPTERS_ANALYZED
        row = 0
        ttk.Label(scrollable_frame, text="Number of Chapters Analyzed Simultaneously:").grid(row=row, column=0, sticky='w', pady=5)
        self.chapters_analyzed_var = tk.IntVar(value=self.config.get("CHAPTERS_ANALYZED", 5))
        chapters_analyzed_spin = ttk.Spinbox(scrollable_frame, from_=1, to=50, textvariable=self.chapters_analyzed_var, width=10)
        chapters_analyzed_spin.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # CATEGORIZATION_BATCH_SIZE
        ttk.Label(scrollable_frame, text="Categorization Batch Size:").grid(row=row, column=0, sticky='w', pady=5)
        self.categorization_batch_var = tk.IntVar(value=self.config.get("CATEGORIZATION_BATCH_SIZE", 20))
        extraction_spin = ttk.Spinbox(scrollable_frame, from_=1, to=100, textvariable=self.categorization_batch_var, width=10)
        extraction_spin.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # TRANSLATION_BATCH_SIZE
        ttk.Label(scrollable_frame, text="Translation Batch Size:").grid(row=row, column=0, sticky='w', pady=5)
        self.translation_batch_var = tk.IntVar(value=self.config.get("TRANSLATION_BATCH_SIZE", 15))
        translation_spin = ttk.Spinbox(scrollable_frame, from_=1, to=100, textvariable=self.translation_batch_var, width=10)
        translation_spin.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # HANJA_GUESSING_BATCH_SIZE
        ttk.Label(scrollable_frame, text="Hanja Guessing Batch Size:").grid(row=row, column=0, sticky='w', pady=5)
        self.hanja_batch_var = tk.IntVar(value=self.config.get("HANJA_GUESSING_BATCH_SIZE", 15))
        hanja_spin = ttk.Spinbox(scrollable_frame, from_=1, to=100, textvariable=self.hanja_batch_var, width=10)
        hanja_spin.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # MAX_RETRIES
        ttk.Label(scrollable_frame, text="Max Retries:").grid(row=row, column=0, sticky='w', pady=5)
        self.max_retries_var = tk.IntVar(value=self.config.get("MAX_RETRIES", 10))
        retries_spin = ttk.Spinbox(scrollable_frame, from_=1, to=50, textvariable=self.max_retries_var, width=10)
        retries_spin.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # RETRY_DELAY
        ttk.Label(scrollable_frame, text="Retry Delay (seconds):").grid(row=row, column=0, sticky='w', pady=5)
        self.retry_delay_var = tk.IntVar(value=self.config.get("RETRY_DELAY", 30))
        delay_spin = ttk.Spinbox(scrollable_frame, from_=1, to=300, textvariable=self.retry_delay_var, width=10)
        delay_spin.grid(row=row, column=1, sticky='w', pady=5)
        row += 1
        
        # Add some padding at the bottom
        ttk.Label(scrollable_frame, text="").grid(row=row, column=0, pady=20)
    
    def create_log_tab(self):
        """Create log output tab"""
        log_frame = ttk.Frame(self.tab_log)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create scrolled text widget for log output
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=100, height=30)
        self.log_text.pack(fill='both', expand=True)
        self.log_text.configure(state='disabled')
        
        # Add clear button
        clear_button = ttk.Button(log_frame, text="Clear Log", command=self.clear_log)
        clear_button.pack(pady=5)
    
    def create_control_buttons(self):
        """Create control buttons at the bottom"""
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        # Left side buttons
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side='left')
        
        ttk.Button(left_frame, text="Save as Default", command=self.save_as_default).pack(side='left', padx=5)
        ttk.Button(left_frame, text="Load Custom Config", command=self.load_custom_config).pack(side='left', padx=5)
        ttk.Button(left_frame, text="Save Custom Config", command=self.save_custom_config).pack(side='left', padx=5)
        
        # Right side buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side='right')
        
        # Create a tk.Button (not ttk.Button) for better styling control:
        self.run_button = tk.Button(
            right_frame, 
            text="RUN NOVEL GLOSSARY MAKER", 
            command=self.run_pipeline,
            font=('Helvetica', 12, 'bold'),  # Bigger font
            bg='#0078d4',                     # Background color (blue)
            fg='white',                       # Text color (white)
            padx=20,                          # Horizontal padding
            pady=10,                          # Vertical padding
            relief='raised',                  # 3D effect
            cursor='hand2'                    # Hand cursor on hover
        )
        self.run_button.pack(side='right', padx=5)
    
    def browse_raws_folder(self):
        """Browse for RAWS folder"""
        folder = filedialog.askdirectory(title="Select RAWS Folder")
        if folder:
            self.raws_folder_var.set(folder)
    
    def browse_reference_file(self):
        """Browse for reference file"""
        filetypes = [("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        file = filedialog.askopenfilename(title="Select Reference File", filetypes=filetypes)
        if file:
            self.reference_var.set(file)
    
    def clear_log(self):
        """Clear the log text widget"""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
    
    def get_current_config(self):
        """Get current configuration from GUI widgets"""
        config = {
            "API_KEY": self.api_key_var.get(),
            "MODEL_NAME": self.model_var.get(),
            "RAWS_FOLDER": self.raws_folder_var.get(),
            "REFERENCE_FILE": self.reference_var.get(),
            "OUTPUT_EXCEL": self.output_var.get(),
            "CHAPTERS_ANALYZED": self.chapters_analyzed_var.get(),
            "CATEGORIZATION_BATCH_SIZE": self.categorization_batch_var.get(),
            "TRANSLATION_BATCH_SIZE": self.translation_batch_var.get(),
            "HANJA_GUESSING_BATCH_SIZE": self.hanja_batch_var.get(),
            "MAX_RETRIES": self.max_retries_var.get(),
            "RETRY_DELAY": self.retry_delay_var.get(),
            "HANJA_IDENTIFICATION": self.hanja_id_var.get(),
            "GUESS_HANJA": self.guess_hanja_var.get(),
            "SIMPLIFIED_CHINESE_CONVERSION": self.simplified_var.get(),
            "GENRE": self.genre_var.get(),
            "NOUNS_JSON_FILE": "nouns.json",  # Fixed
            "ERROR_LOG": "error.txt",  # Fixed
            "GENRE_DESCRIPTIONS": config_loader.GENRE_DESCRIPTIONS,  # From config_loader
            "CATEGORIES": config_loader.CATEGORIES  # From config_loader
        }
        return config
    
    def save_as_default(self):
        """Save current configuration as default config.json"""
        config = self.get_current_config()
        try:
            with open("config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"Configuration saved to config.json")
            messagebox.showinfo("Success", "Configuration saved as default!")
        except Exception as e:
            print(f"Error saving configuration: {e}")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def load_custom_config(self):
        """Load configuration from custom file"""
        filetypes = [("JSON files", "*.json"), ("All files", "*.*")]
        file = filedialog.askopenfilename(title="Load Configuration File", filetypes=filetypes)
        if file:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Update GUI widgets with loaded config
                self.api_key_var.set(config.get("API_KEY", ""))
                self.model_var.set(config.get("MODEL_NAME", "gemini-2.5-pro"))
                self.raws_folder_var.set(config.get("RAWS_FOLDER", "raws"))
                self.reference_var.set(config.get("REFERENCE_FILE", ""))
                self.output_var.set(config.get("OUTPUT_EXCEL", "nouns_replace.xlsx"))
                self.chapters_analyzed_var.set(config.get("CHAPTERS_ANALYZED", 5))
                self.categorization_batch_var.set(config.get("CATEGORIZATION_BATCH_SIZE", 20))
                self.translation_batch_var.set(config.get("TRANSLATION_BATCH_SIZE", 15))
                self.hanja_batch_var.set(config.get("HANJA_GUESSING_BATCH_SIZE", 15))
                self.max_retries_var.set(config.get("MAX_RETRIES", 10))
                self.retry_delay_var.set(config.get("RETRY_DELAY", 30))
                self.hanja_id_var.set(config.get("HANJA_IDENTIFICATION", True))
                self.guess_hanja_var.set(config.get("GUESS_HANJA", True))
                self.simplified_var.set(config.get("SIMPLIFIED_CHINESE_CONVERSION", True))
                self.genre_var.set(config.get("GENRE", "murim"))
                
                print(f"Configuration loaded from {file}")
                messagebox.showinfo("Success", f"Configuration loaded from {file}")
            except Exception as e:
                print(f"Error loading configuration: {e}")
                messagebox.showerror("Error", f"Failed to load configuration: {e}")
    
    def save_custom_config(self):
        """Save current configuration to custom file"""
        config = self.get_current_config()
        
        filetypes = [("JSON files", "*.json"), ("All files", "*.*")]
        file = filedialog.asksaveasfilename(
            title="Save Configuration As",
            defaultextension=".json",
            filetypes=filetypes,
            initialfile="seriesconfig.json"
        )
        
        if file:
            try:
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                print(f"Configuration saved to {file}")
                messagebox.showinfo("Success", f"Configuration saved to {file}")
            except Exception as e:
                print(f"Error saving configuration: {e}")
                messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def run_pipeline(self):
        """Run the noun extraction pipeline in a separate thread"""
        # Disable run button during processing
        self.run_button.configure(state='disabled')
        self.run_button.configure(text="Running...")
        
        # Save current configuration to config.json for the pipeline to use
        self.save_as_default()
        
        # Switch to log tab
        self.notebook.select(self.tab_log)
        
        # Run pipeline in separate thread
        thread = threading.Thread(target=self.run_pipeline_thread, daemon=True)
        thread.start()
    
    def run_pipeline_thread(self):
        """Thread function to run the pipeline"""
        try:
            # Update config_loader with current config
            config = self.get_current_config()
            self.update_config_loader(config)
            
            # Run the pipeline
            success = run_noun_extraction_pipeline()
            
            if success:
                print("\n" + "=" * 60)
                print("PIPELINE COMPLETED SUCCESSFULLY!")
                print("=" * 60)
            else:
                print("\n" + "=" * 60)
                print("PIPELINE FAILED!")
                print("=" * 60)
                
        except Exception as e:
            print(f"\nERROR in pipeline: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Re-enable run button
            self.root.after(0, self.enable_run_button)
    
    def update_config_loader(self, config):
        """Update config_loader module with new configuration"""
        for key, value in config.items():
            if hasattr(config_loader, key):
                setattr(config_loader, key, value)
    
    def enable_run_button(self):
        """Re-enable the run button after pipeline completes"""
        self.run_button.configure(state='normal')
        self.run_button.configure(text="RUN NOVEL GLOSSARY MAKER")  # Updated text
    
    def on_closing(self):
        """Handle window closing"""
        # Restore stdout and stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.root.destroy()

def main():
    """Main function to run the GUI"""
    root = tk.Tk()
    app = NounProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()