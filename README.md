# Content Generation and Analysis Tools

A collection of Python tools for content analysis, podcast generation, and research capabilities.

## Features

- **YouTube Analysis Tool**
  - Downloads audio from YouTube videos
  - Transcribes audio content to text
  - Generates detailed content analysis
  - Performs automated research on key themes

- **Podcast Generation Tool**
  - Creates natural dialogue from any topic
  - Generates blog post content
  - Converts dialogue to audio format
  - Saves transcriptions and audio files

## Prerequisites

- Python 3.x
- Required API keys (configure in `.env`):
  - AssemblyAI API key (transcription)
  - OpenAI API key (analysis)
  - Firecrawl API key (research)
- SQLite database for workflow storage
- ffmpeg (for audio processing)

## Installation

```bash
# Clone the repository
git clone https://github.com/ayyzad/phitdata-agent-examples

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Usage

### YouTube Analysis Tool
-enter the youtube url in the settings.py file
```

### Podcast Generation Tool
-enter the topic in the podcast_agent.py file at the bottom of the script
```
