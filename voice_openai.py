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

client = OpenAI(api_key=auth_token)

# Queue for text waiting to be turned into audio
voice_buffer = Queue()

def add_to_voice_queue(text: str):
    """Enqueue text to be turned into speech by OpenAI TTS."""
    voice_buffer.put(text)

async def process_voice_queue(audio_queue):
    """Process text-to-speech using OpenAI's TTS API."""
    while True:
        if not voice_buffer.empty():
            text = voice_buffer.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"voice_output_{timestamp}.mp3"
            output_path = Path(f"output/{output_file}")
            
            try:
                response = client.audio.speech.create(
                    model="tts-1",
                    voice="shimmer",
                    input=text
                )
                response.stream_to_file(str(output_path))
                
                # Add to audio queue for playback
                audio_queue.put(str(output_path))
                
            except Exception as e:
                print(f"OpenAI TTS API error: {e}")
                
        await asyncio.sleep(0.1)