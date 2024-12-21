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

def add_to_voice_queue(text: str):
    """
    Enqueue text to be turned into speech by ElevenLabs.
    """
    voice_buffer.put(text)

async def process_voice_queue(audio_queue):
    while True:
        if not voice_buffer.empty():
            text = voice_buffer.get()
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
                audio_queue.put(str(output_path))
            except Exception as e:
                print(f"Voice API error: {e}")
                
        await asyncio.sleep(0.1)
