import asyncio
from openai import OpenAI
from datetime import datetime
import json
from queue import Queue
from pathlib import Path

# Load secrets
with open('SECRETS.json') as f:
    secrets = json.load(f)
    auth_token = secrets["openAI"]["authToken"]

# Load config
with open('config.json') as f:
    config = json.load(f)

voice_config = config['voice']['openai']
output_dir = Path(config['paths']['output_dir'])

client = OpenAI(api_key=auth_token)

# Queue for text waiting to be turned into audio
voice_buffer = Queue()

def add_to_voice_queue(text: str):
    """Enqueue text to be turned into speech by OpenAI TTS."""
    voice_buffer.put(text)

async def cleanup_mp3_files(directory: Path, max_files: int = 20):
    """
    Asynchronously ensure that the number of .mp3 files in 'directory'
    does not exceed 'max_files'. If it does, delete the oldest files.
    """
    try:
        if not directory.exists():
            return

        mp3_files = list(directory.glob("*.mp3"))

        if len(mp3_files) <= max_files:
            return

        # Sort by modification time (oldest first)
        mp3_files.sort(key=lambda f: f.stat().st_mtime)

        num_to_remove = len(mp3_files) - max_files

        for i in range(num_to_remove):
            try:
                old_file = mp3_files[i]
                old_file.unlink()
            except Exception as e:
                print(f"[ERROR] Could not delete {mp3_files[i]}: {e}")

    except Exception as e:
        print(f"[ERROR] cleanup_mp3_files encountered an error: {e}")

async def process_voice_queue(audio_queue):
    while True:
        if not voice_buffer.empty():
            text = voice_buffer.get()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"voice_output_{timestamp}.mp3"
            output_path = output_dir / output_file
            
            try:
                response = client.audio.speech.create(
                    model=voice_config['model'],
                    voice=voice_config['voice'],
                    input=text
                )
                # Stream to file
                response.stream_to_file(str(output_path))
                
                # Add to audio queue for playback
                audio_queue.put(str(output_path))

                # Schedule the cleanup asynchronously
                asyncio.create_task(cleanup_mp3_files(output_dir, max_files=20))

            except Exception as e:
                print(f"OpenAI TTS API error: {e}")
                
        # Small delay to let other coroutines run
        await asyncio.sleep(0.1)
