from typing import Optional
from phi.tools import Toolkit
from phi.utils.log import logger
from yt_dlp import YoutubeDL
import os
from pathlib import Path

class YoutubeTools(Toolkit):
    def __init__(self):
        super().__init__(name="youtube_tools")
        
        # Get the project root directory (2 levels up from tools directory)
        self.project_root = Path(__file__).parent.parent
        
        # Set the output path relative to project root
        self.output_path = self.project_root / 'audio'
        logger.info(f"YouTube download directory: {self.output_path}")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_path, exist_ok=True)
        
        # Register the download function
        self.register(self.download_audio)

    def download_audio(self, url: str) -> str:
        """Downloads audio from a YouTube video and saves it as MP3."""
        logger.info(f"Downloading audio from: {url}")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',  # Default quality
            }],
            'outtmpl': str(self.output_path / '%(title)s.%(ext)s'),
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # Check for the downloaded file
                files = list(self.output_path.glob('*.mp3'))
                if not files:
                    raise FileNotFoundError("No MP3 file was created")
                
                return f"Successfully downloaded: {files[0].name}"
                
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg)
            return error_msg