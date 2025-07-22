# Spanish Vocabulary Trainer 🇪🇸

A comprehensive desktop application for learning Spanish vocabulary with AI-powered example sentences, text-to-speech, image search, and interactive exams.

## Features ✨

- **Interactive Vocabulary Learning**: Display Spanish words with English translations
- **AI-Powered Example Sentences**: Generate contextual example sentences using Ollama AI (optional)
- **Text-to-Speech**: Hear correct pronunciation of Spanish words and sentences
- **Visual Learning**: Automatic image search to reinforce vocabulary with visual context
- **Interactive Exams**: Regular multiple-choice quizzes to test your progress
- **Customizable Interface**: Easy-to-modify configuration variables
- **Clipboard Integration**: Copy sentences for further study
- **Custom Vocabulary**: Add your own words and load custom vocabulary files

## Screenshots 📸

The application provides a clean, intuitive interface with:
- Large, clear display of Spanish vocabulary words
- Delayed translation reveal to encourage active recall
- Three example sentences per word with audio playback
- Visual context through Google Images integration
- Regular progress testing through interactive exams

## Installation 🚀

### Prerequisites

- Python 3.7 or higher
- Internet connection (for image search and AI features)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/spanish-vocabulary-trainer.git
cd spanish-vocabulary-trainer
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Individual package installation:**
```bash
pip install gtts pygame Pillow requests beautifulsoup4 pyperclip
```

**Optional AI Enhancement:**
```bash
pip install ollama
```

### Step 3: Set Up Vocabulary Files

Create a `words` folder in the project directory and add your vocabulary files:

```bash
mkdir words
```

Place your vocabulary text files in this folder (see [Vocabulary File Format](#vocabulary-file-format) below).

### Step 4: Optional - Install Ollama for AI Sentences

For enhanced AI-generated example sentences:

1. Install [Ollama](https://ollama.ai/)
2. Download the required model:
   ```bash
   ollama pull llama3.2:3b-instruct-q4_K_M
