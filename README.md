# Content Summary and Research Analysis Tool

A powerful Python tool that processes YouTube videos and generates comprehensive content analysis with automated research capabilities.

## Features

- Downloads audio from YouTube videos, supports multiple urls (see config/settings.py)
- Transcribes audio content to text
- Generates detailed content analysis
- Performs automated research on key themes
- Creates comprehensive markdown reports

## Prerequisites

- Python 3.x
- Required environment variables (configure in `.env`)
- SQLite database for workflow storage
- Firecrawl API key (for research)
- AssemblyAI API key (for transcription)
- OpenAI API key (for analysis)
- Phidata

## Installation

```bash
# Clone the repository
git clone https://github.com/ayyzad/youtube-summary-agent

# Install dependencies
pip install -r requirements.txt