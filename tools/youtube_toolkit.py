from typing import Optional
from phi.tools import Toolkit
from phi.utils.log import logger
from yt_dlp import YoutubeDL
import os
from pathlib import Path
import re

class YoutubeTools(Toolkit):
    def __init__(self):
        super().__init__(name="youtube_tools")
        
        # Get the project root directory (2 levels up from tools directory)
        self.project_root = Path(__file__).parent.parent
        
        # Set up base output directory using relative path
        self.output_base = self.project_root / 'agents/youtube-research-agent/summary-agent-output'
        
        # Set the audio output path
        self.output_path = self.output_base / 'audio'
        logger.info(f"YouTube download directory: {self.output_path}")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_path, exist_ok=True)
        
        # Register the download function
        self.register(self.download_audio)

    def clean_filename(self, filename: str) -> str:
        """Clean filename by removing invalid characters and replacing spaces with underscores."""
        return re.sub(r'[^a-zA-Z0-9_-]', '', filename.replace(' ', '_'))

    def download_audio(self, url: str) -> str:
        """Downloads audio from a YouTube video and saves it as MP3."""
        logger.info(f"Downloading audio from: {url}")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(self.output_path / '%(title)s.%(ext)s'),
            'restrictfilenames': True,
            'windowsfilenames': True,
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                # Get info dict before download to clean the filename
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'video')
                clean_title = self.clean_filename(title)
                
                # Update options with cleaned filename
                ydl_opts['outtmpl'] = str(self.output_path / f'{clean_title}.%(ext)s')
                
                # Download with cleaned filename
                with YoutubeDL(ydl_opts) as ydl_clean:
                    ydl_clean.download([url])
                
                # Check for the downloaded file
                files = list(self.output_path.glob('*.mp3'))
                if not files:
                    raise FileNotFoundError("No MP3 file was created")
                
                return f"Successfully downloaded: {files[0].name}"
                
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg)
            return error_msg