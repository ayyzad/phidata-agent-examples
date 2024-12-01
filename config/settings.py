import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# YouTube URLs to process
YOUTUBE_URLS = [
    "https://www.youtube.com/shorts/-Lzr4z74NpQ",
    "https://www.youtube.com/shorts/Vy5PuNjUFYo",
    # Add more URLs as needed
]

# Research settings
MAX_THEMES_TO_RESEARCH = 1  # Limit number of themes
ARTICLES_PER_THEME = 1      # Limit articles per theme
SEARCH_DELAY = 5            # Delay between searches in seconds

# File paths
AUDIO_DIR = "audio"
TRANSCRIPTION_SUMMARY_DIR = "transcription_summary"
TRANSCRIPTION_OUTPUT_DIR = "transcriptions"
OUTPUT_DIR = "agent-output"