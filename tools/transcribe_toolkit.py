from typing import Optional, Dict, List
from phi.tools import Toolkit
from phi.utils.log import logger
import assemblyai as aai
import json
import time
import os
from pathlib import Path
from dotenv import load_dotenv

class TranscriptionTools(Toolkit):
    def __init__(self):
        super().__init__(name="transcription_tools")
        
        # Get the project root directory
        self.project_root = Path(__file__).parent.parent
        
        # Load environment variables
        load_dotenv(self.project_root / '.env')
        api_key = os.getenv('ASSEMBLYAI_API_KEY')
        if not api_key:
            raise ValueError("ASSEMBLYAI_API_KEY not found in environment variables")
        
        # Initialize AssemblyAI client
        aai.settings.api_key = api_key
        
        # Set up directories
        self.audio_dir = self.project_root / 'audio'
        self.transcriptions_dir = self.project_root / 'transcriptions'
        self.transcriptions_dir.mkdir(exist_ok=True)
        
        # Register the tools
        self.register(self.transcribe_audio)
        self.register(self.transcribe_all_audio)

    def transcribe_audio(self, file_name: str) -> str:
        """Transcribe an audio file and save full results to JSON, but return only the transcript text"""
        try:
            file_path = self.audio_dir / file_name
            
            if not file_path.exists():
                error_msg = f"Audio file not found: {file_name}"
                logger.error(error_msg)
                return error_msg
            
            config = aai.TranscriptionConfig(speaker_labels=True)
            
            logger.info(f"Transcribing: {file_name}")
            transcript = aai.Transcriber().transcribe(
                str(file_path),
                config=config
            )
            
            # Save full transcript data to JSON
            transcript_data = {
                'full_transcript': transcript.text,
                'speakers': [
                    {
                        'speaker': utterance.speaker,
                        'text': utterance.text
                    }
                    for utterance in transcript.utterances
                ],
                'audio_file': file_name,
                'transcribed_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Save complete data to JSON file
            output_path = self.transcriptions_dir / file_path.with_suffix('.json').name
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Transcription saved for: {file_name}")
            
            # Return only the transcript text
            return transcript.text
                
        except Exception as e:
            error_msg = f"Error transcribing {file_name}: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def transcribe_all_audio(self) -> List[Dict]:
        """
        Transcribe all supported audio files in the audio directory.
        
        Returns:
            list: List of transcript data or error messages for each file
        """
        audio_extensions = {'.mp3', '.mov'}
        results = []
        
        logger.info(f"Looking for audio files in: {self.audio_dir}")
        
        for file_name in os.listdir(self.audio_dir):
            if Path(file_name).suffix.lower() in audio_extensions:
                result = self.transcribe_audio(file_name)
                results.append(result)
        
        return results