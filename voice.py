import asyncio
from elevenlabs import ElevenLabs
from datetime import datetime
import json
from queue import Queue
from pathlib import Path

# Load secrets
with open('SECRETS.json') as f:
    secrets = json.load(f)
    voice_token = secrets["elevenlabs"]["authToken"]

# Load config
with open('config.json') as f:
    config = json.load(f)

voice_config = config['voice']['elevenlabs']
output_dir = Path(config['paths']['output_dir'])

client = ElevenLabs(api_key=voice_token)

# This queue holds text waiting to be turned into audio
voice_buffer = Queue()

def add_to_voice_queue(text: str, emotion=None):
    # Instead of just text, store (text, emotion)
    voice_buffer.put((text, emotion))

async def cleanup_mp3_files(directory: Path, max_files: int = 20):
    """
    Asynchronously ensure that the number of .mp3 files in 'directory'
    does not exceed 'max_files'. If it does, delete the oldest files.
    """
    # Gather all .mp3 files
    mp3_files = list(directory.glob("*.mp3"))
    
    # Sort by modification time, oldest first
    mp3_files.sort(key=lambda f: f.stat().st_mtime)
    
    # If total files exceed max_files, delete the extra oldest ones
    if len(mp3_files) > max_files:
        num_to_remove = len(mp3_files) - max_files
        for i in range(num_to_remove):
            try:
                mp3_files[i].unlink()
                print(f"Deleted old mp3 file: {mp3_files[i].name}")
            except Exception as e:
                print(f"Error deleting file {mp3_files[i].name}: {e}")

async def process_voice_queue(audio_queue):
    while True:
        if not voice_buffer.empty():
            text, emotion = voice_buffer.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"voice_output_{timestamp}.mp3"
            output_path = output_dir / output_file
            
            try:
                audio_content = client.text_to_speech.convert(
                    voice_id=voice_config['voice_id'],
                    output_format=voice_config['output_format'],
                    text=text,
                    model_id=voice_config['model_id'],
                )
                
                with open(output_path, "wb") as audio_file:
                    for chunk in audio_content:
                        audio_file.write(chunk)
                        
                # Instead of storing locally in another queue, send directly to audio_queue
                audio_queue.put((str(output_path), emotion))

                # Schedule the cleanup check asynchronously so it doesn't block this loop
                asyncio.create_task(cleanup_mp3_files(output_dir, max_files=20))

            except Exception as e:
                print(f"Voice API error: {e}")
                
        # Small delay to let other coroutines run
        await asyncio.sleep(0.1)
