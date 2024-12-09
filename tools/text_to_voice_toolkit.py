from typing import Optional, Dict
from phi.tools import Toolkit
from phi.utils.log import logger
from openai import OpenAI
from pathlib import Path
from pydub import AudioSegment
import json
import dotenv

class TextToVoiceTools(Toolkit):
    def __init__(self):
        super().__init__(name="text_to_voice_tools")
        
        # Get the project root directory
        self.project_root = Path(__file__).parent.parent
        
        # Load environment variables
        dotenv.load_dotenv()
        
        # Initialize OpenAI client
        self.client = OpenAI()
        
        # Set up directories
        self.output_dir = Path('podcast-agent-output/conversation-audio')
        self.temp_dir = self.output_dir / 'temp_audio'
        # Create both directories
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        
        # Register the tools
        self.register(self.create_conversation_audio)
    
    def create_conversation_audio(self, json_file_path: str) -> str:
        """Convert conversation from JSON file to audio using different voices."""
        try:
            # Get the base name of the input JSON file (without extension)
            input_filename = Path(json_file_path).stem
            
            # Assign different voices to speakers
            voices = {
                "Person A": "alloy",
                "Person B": "echo"
            }
            
            # Create temporary directory
            self.temp_dir.mkdir(exist_ok=True)
            
            # Load conversation from JSON file
            with open(json_file_path, 'r') as file:
                data = json.load(file)
                conversation = data.get('dialogue', {}).get('messages', [])
            
            # Generate audio for each message and concatenate
            combined_audio = AudioSegment.empty()
            
            for i, entry in enumerate(conversation):
                if isinstance(entry, dict) and "speaker" in entry and "message" in entry:
                    speaker = entry["speaker"]
                    message = entry["message"]
                    voice = voices.get(speaker, "alloy")
                    
                    response = self.client.audio.speech.create(
                        model="tts-1",
                        voice=voice,
                        input=message
                    )
                    
                    # Save the response content to a temporary file
                    temp_file = self.temp_dir / f"part_{i}.mp3"
                    with open(temp_file, 'wb') as f:
                        f.write(response.content)
                    
                    # Load the audio segment and append it
                    audio_segment = AudioSegment.from_file(temp_file)
                    combined_audio += audio_segment
                else:
                    logger.warning(f"Skipping invalid entry at index {i}: {entry}")
            
            # Save the combined audio using the input filename
            output_file = self.output_dir / f"{input_filename}.mp3"
            combined_audio.export(output_file, format="mp3")
            
            # Clean up temporary files
            for temp_file in self.temp_dir.glob("*.mp3"):
                temp_file.unlink()
            self.temp_dir.rmdir()
            
            return f"Audio created successfully: {output_file}"
            
        except Exception as e:
            error_msg = f"Error creating audio: {str(e)}"
            logger.error(error_msg)
            return error_msg