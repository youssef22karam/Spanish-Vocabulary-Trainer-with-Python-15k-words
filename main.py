#!/usr/bin/env python3
"""
Spanish Vocabulary Trainer
A comprehensive tool for learning Spanish vocabulary with AI-powered example sentences,
text-to-speech, image search, and interactive exams.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from gtts import gTTS
import pygame
import time
import threading
import os
from PIL import Image, ImageTk
import requests
from io import BytesIO
import uuid
import atexit
import tempfile
from bs4 import BeautifulSoup
import webbrowser
import random
import json
import pyperclip
import re

# =============================================================================
# CONFIGURATION VARIABLES - Modify these to customize the application
# =============================================================================

# File and Directory Settings
WORDS_FOLDER = "words"  # Folder containing vocabulary files
DEFAULT_VOCAB_FILE = ".All in one_14996.txt"  # Default vocabulary file name
TEMP_AUDIO_PREFIX = "speech_"  # Prefix for temporary audio files

# UI Configuration
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 700
MAIN_WORD_FONT_SIZE = 48
TRANSLATION_FONT_SIZE = 36
SENTENCE_FONT_SIZE = 14
CONTROL_FONT_SIZE = 14

# Image Settings
IMAGE_WIDTH = 250
IMAGE_HEIGHT = 250

# Audio Settings
AUDIO_LANGUAGE = 'es'  # Language for text-to-speech (es = Spanish)
AUDIO_PLAYBACK_RATE = 10  # Pygame clock tick rate during audio playback

# Learning Configuration
TRANSLATION_DELAY = 5000  # Delay before showing translation (milliseconds)
EXAM_TRIGGER_INTERVAL = 10  # Show exam after this many words
EXAM_WORD_COUNT = 20  # Number of words to include in exam
EXAM_CHOICES_COUNT = 4  # Number of multiple choice options

# AI Sentence Generation
OLLAMA_MODEL = "llama3.2:3b-instruct-q4_K_M"  # Ollama model for sentence generation
SENTENCES_PER_WORD = 3  # Number of example sentences to generate
SENTENCE_WRAP_LENGTH = 600  # Maximum width for sentence text wrapping

# Google Images Search
GOOGLE_SEARCH_HEADERS = {"User-Agent": "Mozilla/5.0"}  # Headers for web requests
IMAGE_SEARCH_TIMEOUT = 5  # Timeout for image search requests (seconds)

# =============================================================================
# VOCABULARY PARSING AND LOADING
# =============================================================================

def parse_vocabulary(text):
    """Parse vocabulary from text file format: english,spanish"""
    vocabulary = []
    lines = text.strip().split("\n")
    
    for line in lines:
        parts = re.split(r',', line)
        if len(parts) < 2:
            continue  # Skip lines that don't have both English and Spanish
        english_words = parts[0].strip()
        spanish_words = parts[1].strip()
        
        vocabulary.append({
            "english": english_words,
            "spanish": spanish_words
        })
    
    return vocabulary

def load_vocabulary_file(file_path=None):
    """Load vocabulary from file with error handling"""
    if file_path is None:
        file_path = os.path.join(WORDS_FOLDER, DEFAULT_VOCAB_FILE)
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
        return parse_vocabulary(text)
    except FileNotFoundError:
        print(f"Vocabulary file not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error loading vocabulary file: {e}")
        return []

# =============================================================================
# AI INTEGRATION (OLLAMA)
# =============================================================================

# Check if Ollama is available
OLLAMA_AVAILABLE = False
try:
    import ollama
    # Try to ping ollama service to see if it's running
    try:
        ollama.list()  # This will fail if ollama service isn't running
        OLLAMA_AVAILABLE = True
        print("Ollama is available - AI sentence generation enabled")
    except Exception as e:
        print(f"Ollama is installed but service not running: {e}")
        print("Sentence generation will use fallback examples")
except ImportError:
    print("Ollama not installed - sentence generation will use fallback examples")

def get_example_sentences(word, cancel_event):
    """Generate example sentences using Ollama AI or fallback examples"""
    if OLLAMA_AVAILABLE:
        try:
            if cancel_event.is_set():
                return ["", "", ""]
                
            prompt = f"Escribe {SENTENCES_PER_WORD} oraciones diferentes de nivel intermedio usando la palabra en español '{word}'. Salida solo las {SENTENCES_PER_WORD} oraciones en {SENTENCES_PER_WORD} lines, nada más, sin explicaciones ni texto adicional. Solo las {SENTENCES_PER_WORD} oraciones."
            
            # Call Ollama API with the prompt
            response = ollama.generate(
                model=OLLAMA_MODEL,
                prompt=prompt,
                system="You are a helpful Spanish language assistant. Respond only with the requested sentences in Spanish.",
                stream=False
            )
            
            if cancel_event.is_set():
                return ["", "", ""]
                
            # Extract sentences from response
            sentences = response['response'].strip().split('\n')
            # Clean up sentences (remove numbers, extra spaces, etc.)
            sentences = [s.strip().replace('1. ', '').replace('2. ', '').replace('3. ', '') for s in sentences if s.strip()]
            
            # Ensure we have exactly the right number of sentences
            if len(sentences) > SENTENCES_PER_WORD:
                sentences = sentences[:SENTENCES_PER_WORD]
            while len(sentences) < SENTENCES_PER_WORD:
                sentences.append(f"Ejemplo con {word}.")
                
            return sentences
        except Exception as e:
            print(f"Error generating sentences with Ollama: {e}")
            # Fall through to fallback sentences
    
    # Fallback sentences when Ollama is not available or fails
    print(f"Using fallback sentences for: {word}")
    
    # Generate variety of fallback sentence patterns
    patterns = [
        f"Me gusta mucho {word}.",
        f"{word.capitalize()} es muy importante.",
        f"Necesito {word} para mi vida diaria.",
        f"Sin {word} no puedo vivir.",
        f"{word.capitalize()} me ayuda mucho.",
        f"Todos necesitamos {word}.",
        f"{word.capitalize()} está en mi casa.",
        f"Compré {word} ayer.",
        f"Busco {word} en la tienda.",
        f"Este es un ejemplo con la palabra {word}.",
        f"Podemos usar {word} en diferentes contextos.",
        f"La palabra {word} es útil en español."
    ]
    
    # Randomly select the required number of different patterns
    selected_patterns = random.sample(patterns, min(SENTENCES_PER_WORD, len(patterns)))
    return selected_patterns

# =============================================================================
# IMAGE SEARCH FUNCTIONALITY
# =============================================================================

def google_image_search(query):
    """Fetch the first image from Google Images."""
    try:
        search_url = f"https://www.google.com/search?tbm=isch&q={query}"
        response = requests.get(search_url, headers=GOOGLE_SEARCH_HEADERS, timeout=IMAGE_SEARCH_TIMEOUT)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            img_tags = soup.find_all("img")
            if len(img_tags) > 1:
                img_url = img_tags[1]["src"]  # First image result
                return img_url
    except Exception as e:
        print(f"Error searching for image: {e}")
    return None

# =============================================================================
# MAIN APPLICATION CLASS
# =============================================================================

class VocabularyTrainer:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.initialize_pygame()
        self.setup_temp_directory()
        self.initialize_variables()
        self.setup_ui()
        self.load_vocabulary()
        
    def setup_window(self):
        """Configure the main window"""
        self.root.title("Spanish Vocabulary Trainer")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        
        # Show Ollama status in title
        status = "with AI sentences" if OLLAMA_AVAILABLE else "with basic sentences"
        self.root.title(f"Spanish Vocabulary Trainer ({status})")
        
    def initialize_pygame(self):
        """Initialize pygame mixer for audio"""
        pygame.mixer.init()
        
    def setup_temp_directory(self):
        """Create temporary directory for audio files"""
        self.temp_dir = tempfile.mkdtemp()
        atexit.register(self.cleanup_temp_files)
        
    def initialize_variables(self):
        """Initialize application state variables"""
        self.vocabulary = []
        self.current_index = 0
        self.audio_lock = threading.Lock()
        self.translation_timer = None
        self.current_audio_file = None
        self.recent_words = []  # Track words for exams
        self.words_since_last_exam = 0  # Counter for exam triggering
        self.current_sentences = []  # Store current word's sentences
        self.sentence_thread = None  # Track the sentence generation thread
        self.cancel_event = threading.Event()  # Event to signal cancellation
        
    def setup_ui(self):
        """Create the user interface"""
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Status label
        status_text = "🤖 AI-powered sentences" if OLLAMA_AVAILABLE else "📝 Basic example sentences"
        self.status_label = tk.Label(self.main_frame, text=status_text, font=("Arial", 10), fg="gray")
        self.status_label.pack(pady=5)
        
        # Main word display
        self.word_label = tk.Label(self.main_frame, text="", font=("Arial", MAIN_WORD_FONT_SIZE, "bold"))
        self.word_label.pack(pady=10)
        
        # Translation display
        self.translation_label = tk.Label(self.main_frame, text="", font=("Arial", TRANSLATION_FONT_SIZE, "italic"), fg="green")
        self.translation_label.pack(pady=10)
        
        # Image display
        self.image_label = tk.Label(self.main_frame)
        self.image_label.pack(pady=10)
        
        # Example sentences frame
        self.setup_sentences_ui()
        
        # Control buttons
        self.setup_control_buttons()
        
        # Event bindings
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Return>", lambda event: self.show_next_word())
        
    def setup_sentences_ui(self):
        """Create the example sentences section"""
        self.sentences_frame = tk.Frame(self.main_frame)
        self.sentences_frame.pack(pady=10, fill='x')
        
        self.sentence_labels = []
        for i in range(SENTENCES_PER_WORD):
            sentence_frame = tk.Frame(self.sentences_frame)
            sentence_frame.pack(fill='x', pady=5)
            
            play_btn = tk.Button(sentence_frame, text="🔊", font=("Arial", 12))
            play_btn.pack(side='left', padx=5)
            
            sentence_label = tk.Label(sentence_frame, text="", font=("Arial", SENTENCE_FONT_SIZE), 
                                     wraplength=SENTENCE_WRAP_LENGTH, justify='left')
            sentence_label.pack(side='left', fill='x', expand=True)
            
            copy_btn = tk.Button(sentence_frame, text="📋", font=("Arial", 12))
            copy_btn.pack(side='right', padx=5)
            
            self.sentence_labels.append((sentence_label, play_btn, copy_btn))
            
    def setup_control_buttons(self):
        """Create control buttons"""
        self.control_frame = tk.Frame(self.main_frame)
        self.control_frame.pack(side='bottom', pady=20)
        
        self.load_file_button = tk.Button(self.control_frame, text="Load File", 
                                         font=("Arial", CONTROL_FONT_SIZE), 
                                         command=self.load_vocabulary_file_dialog)
        self.load_file_button.pack(side='left', padx=10)
        
        self.add_word_button = tk.Button(self.control_frame, text="Add New Word", 
                                        font=("Arial", CONTROL_FONT_SIZE), 
                                        command=self.show_add_word_dialog)
        self.add_word_button.pack(side='left', padx=10)
        
        self.next_button = tk.Button(self.control_frame, text="Start/Next", 
                                    font=("Arial", CONTROL_FONT_SIZE), 
                                    command=self.show_next_word)
        self.next_button.pack(side='left', padx=10)
        
    def load_vocabulary(self):
        """Load the default vocabulary file"""
        self.vocabulary = load_vocabulary_file()
        if self.vocabulary:
            random.shuffle(self.vocabulary)
            print(f"Loaded {len(self.vocabulary)} words from vocabulary file")
        else:
            print("No vocabulary loaded. Use 'Load File' button to select a vocabulary file.")
            
    def load_vocabulary_file_dialog(self):
        """Open file dialog to select vocabulary file"""
        file_path = filedialog.askopenfilename(
            title="Select Vocabulary File",
            initialdir=WORDS_FOLDER,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            self.vocabulary = load_vocabulary_file(file_path)
            if self.vocabulary:
                random.shuffle(self.vocabulary)
                self.current_index = 0
                messagebox.showinfo("Success", f"Loaded {len(self.vocabulary)} words from {os.path.basename(file_path)}")
            else:
                messagebox.showerror("Error", "Failed to load vocabulary file")
                
    def show_add_word_dialog(self):
        """Show dialog to add new vocabulary word"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Word")
        dialog.geometry("300x200")
        dialog.grab_set()
        
        tk.Label(dialog, text="Spanish Word:", font=("Arial", 14)).pack(pady=5)
        spanish_entry = tk.Entry(dialog, font=("Arial", 14))
        spanish_entry.pack(pady=5)
        spanish_entry.focus()
        
        tk.Label(dialog, text="English Translation:", font=("Arial", 14)).pack(pady=5)
        english_entry = tk.Entry(dialog, font=("Arial", 14))
        english_entry.pack(pady=5)
        
        def save_word():
            spanish = spanish_entry.get().strip()
            english = english_entry.get().strip()
            if spanish and english:
                self.vocabulary.append({"spanish": spanish, "english": english})
                messagebox.showinfo("Success", f"Added: {spanish} = {english}")
                dialog.destroy()
            else:
                messagebox.showwarning("Warning", "Please fill in both fields")
        
        tk.Button(dialog, text="Save", font=("Arial", 14), command=save_word).pack(pady=20)
        
        # Bind Enter key to save
        dialog.bind("<Return>", lambda event: save_word())
        
    def start_exam(self, exam_words):
        """Start a multiple choice exam with recent words"""
        exam_window = tk.Toplevel(self.root)
        exam_window.title("Word Matching Exam")
        exam_window.geometry("800x600")
        exam_window.grab_set()  # Make window modal
        
        exam_frame = tk.Frame(exam_window)
        exam_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        tk.Label(exam_frame, text=f"Match the Spanish words with their English translations", 
                font=("Arial", 16, "bold")).pack(pady=10)
        
        self.exam_answers = {}
        
        for idx, word in enumerate(exam_words):
            question_frame = tk.Frame(exam_frame)
            question_frame.pack(fill='x', pady=5)
            
            tk.Label(question_frame, text=word['spanish'], font=('Arial', 14), width=20, anchor='w').pack(side='left', padx=10)
            
            correct = word['english']
            other_answers = [w['english'] for w in exam_words if w != word]
            random.shuffle(other_answers)
            options = other_answers[:EXAM_CHOICES_COUNT-1] + [correct]
            random.shuffle(options)
            
            selected = tk.StringVar()
            cb = ttk.Combobox(question_frame, textvariable=selected, values=options, 
                             state='readonly', font=('Arial', 12), width=30)
            cb.pack(side='right', padx=10)
            self.exam_answers[idx] = {
                'correct': correct,
                'selected': selected,
                'combobox': cb,
                'frame': question_frame
            }
        
        tk.Button(exam_window, text="Submit Exam", font=('Arial', 14),
                 command=lambda: self.evaluate_exam(exam_window)).pack(pady=20)
                 
    def evaluate_exam(self, exam_window):
        """Evaluate exam results and show score"""
        score = 0
        total = len(self.exam_answers)
        
        for idx in self.exam_answers:
            data = self.exam_answers[idx]
            selected = data['selected'].get()
            correct = data['correct']
            
            result_label = tk.Label(data['frame'], font=('Arial', 12))
            if selected == correct:
                score += 1
                result_label.config(text="✓ Correct", fg='green')
            else:
                result_label.config(text=f"✗ Correct: {correct}", fg='red')
            result_label.pack(side='right', padx=10)
            data['combobox'].config(state='disabled')
        
        percentage = (score / total) * 100 if total > 0 else 0
        score_text = f"Score: {score}/{total} ({percentage:.1f}%)"
        score_label = tk.Label(exam_window, text=score_text, font=('Arial', 16, 'bold'))
        score_label.pack(pady=10)
        
        tk.Button(exam_window, text="Close", command=exam_window.destroy).pack(pady=10)
        
    def text_to_speech(self, text, lang=AUDIO_LANGUAGE):
        """Generate and play text-to-speech audio"""
        try:
            temp_filename = os.path.join(self.temp_dir, f"{TEMP_AUDIO_PREFIX}{uuid.uuid4()}.mp3")
            
            with self.audio_lock:
                tts = gTTS(text=text, lang=lang)
                tts.save(temp_filename)
                pygame.mixer.music.load(temp_filename)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(AUDIO_PLAYBACK_RATE)
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                
                return temp_filename
        except Exception as e:
            print(f"Error in text-to-speech: {e}")
            return None
            
    def play_sentence(self, index):
        """Play audio for a specific sentence"""
        if index < len(self.current_sentences):
            sentence = self.current_sentences[index]
            threading.Thread(target=self.text_to_speech, args=(sentence,), daemon=True).start()
            
    def copy_to_clipboard(self, text):
        """Copy text to clipboard with visual feedback"""
        def reset_button_text(btn, original_text):
            btn.config(text=original_text)
            
        pyperclip.copy(text)
        # Visual feedback that text was copied
        for label, play_btn, copy_btn in self.sentence_labels:
            if label.cget("text") == text:
                copy_btn.config(text="✓")
                self.root.after(1000, lambda btn=copy_btn: reset_button_text(btn, "📋"))
                break
                
    def update_example_sentences(self):
        """Update the UI with current example sentences"""
        for i, (label, play_btn, copy_btn) in enumerate(self.sentence_labels):
            if i < len(self.current_sentences):
                sentence = self.current_sentences[i]
                label.config(text=sentence)
                
                # Set the button command (using a function factory to avoid closure issues)
                def make_play_cmd(idx):
                    return lambda: self.play_sentence(idx)
                
                def make_copy_cmd(sentence_text):
                    return lambda: self.copy_to_clipboard(sentence_text)
                
                play_btn.config(command=make_play_cmd(i))
                copy_btn.config(command=make_copy_cmd(sentence))
            else:
                label.config(text="")
                play_btn.config(command=lambda: None)
                copy_btn.config(command=lambda: None)
                
    def fetch_sentences_thread(self, word):
        """Generate sentences in a separate thread"""
        # Reset cancel event for new request
        self.cancel_event.clear()
        
        # Generate sentences
        sentences = get_example_sentences(word, self.cancel_event)
        
        # Only update if not cancelled
        if not self.cancel_event.is_set():
            self.current_sentences = sentences
            # Update UI on main thread
            self.root.after(0, self.update_example_sentences)
            
    def load_image(self, word_english):
        """Load and display image for the current word"""
        img_url = google_image_search(word_english)
        if img_url and not self.cancel_event.is_set():
            try:
                response = requests.get(img_url, timeout=IMAGE_SEARCH_TIMEOUT)
                if response.status_code == 200:
                    img_data = BytesIO(response.content)
                    img = Image.open(img_data)
                    img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    # Update UI on main thread if not cancelled
                    if not self.cancel_event.is_set():
                        self.root.after(0, lambda: self.image_label.config(image=photo))
                        self.image_label.image = photo
            except Exception as e:
                print(f"Error loading image: {e}")
                
    def show_next_word(self):
        """Display the next vocabulary word with all features"""
        if not self.vocabulary:
            messagebox.showwarning("No Vocabulary", "Please load a vocabulary file first.")
            return
            
        # Cancel any ongoing operations
        self.cancel_event.set()
        
        if self.translation_timer is not None:
            self.root.after_cancel(self.translation_timer)
        
        if self.current_index >= len(self.vocabulary):
            self.current_index = 0
            random.shuffle(self.vocabulary)  # Reshuffle when starting over
        
        word = self.vocabulary[self.current_index]
        self.word_label.config(text=word["spanish"], fg="black")
        self.translation_label.config(text="")
        
        # Clear image
        self.image_label.config(image="")
        self.image_label.image = None
        
        # Clear previous sentences while loading
        loading_text = "Generating AI sentences..." if OLLAMA_AVAILABLE else "Loading example sentences..."
        for label, _, _ in self.sentence_labels:
            label.config(text=loading_text)
        
        # Create a new cancel event for this word
        self.cancel_event = threading.Event()
        
        # Text to speech for the word
        threading.Thread(target=self.text_to_speech, args=(word["spanish"],), daemon=True).start()
        
        # Start image loading first to display it immediately
        image_thread = threading.Thread(target=self.load_image, args=(word["english"],), daemon=True)
        image_thread.start()
        
        # Then start sentence generation in a separate thread
        self.sentence_thread = threading.Thread(
            target=self.fetch_sentences_thread,
            args=(word["spanish"],),
            daemon=True
        )
        self.sentence_thread.start()
        
        # Show translation after delay
        self.translation_timer = self.root.after(TRANSLATION_DELAY, 
                                               lambda: self.translation_label.config(text=word["english"]))
        
        # Track words for exams
        self.recent_words.append(word)
        self.words_since_last_exam += 1
        self.current_index += 1
        
        # Start exam after specified interval using previous words
        if self.words_since_last_exam >= EXAM_TRIGGER_INTERVAL and len(self.recent_words) >= EXAM_TRIGGER_INTERVAL:
            exam_words = self.recent_words[-EXAM_WORD_COUNT:] if len(self.recent_words) >= EXAM_WORD_COUNT else self.recent_words
            self.start_exam(exam_words)
            self.words_since_last_exam = 0
            # Keep some words for next exam
            self.recent_words = self.recent_words[-(EXAM_WORD_COUNT//2):]
            
    def cleanup_temp_files(self):
        """Clean up temporary audio files"""
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            os.rmdir(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp directory: {e}")
            
    def on_closing(self):
        """Handle application closing"""
        if self.translation_timer:
            self.root.after_cancel(self.translation_timer)
        # Cancel any ongoing operations
        self.cancel_event.set()
        pygame.mixer.quit()
        self.cleanup_temp_files()
        self.root.destroy()

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = VocabularyTrainer(root)
    root.mainloop()