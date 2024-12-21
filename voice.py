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

client = ElevenLabs(api_key=voice_token)

# This queue holds text waiting to be turned into audio
voice_buffer = Queue()

def add_to_voice_queue(text: str):
    """
    Enqueue text to be turned into speech by ElevenLabs.
    """
    voice_buffer.put(text)

async def process_voice_queue(audio_queue):
    """
    Continuously check if there's text to be processed into TTS MP3 files.
    When an MP3 file is created, put it in audio_queue so the audio player can pick it up.
    """
    while True:
        if not voice_buffer.empty():
            text = voice_buffer.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"voice_output_{timestamp}.mp3"
            output_path = Path(f"output/{output_file}")
            
            try:
                audio_content = client.text_to_speech.convert(
                    voice_id="cgSgspJ2msm6clMCkdW9",
                    output_format="mp3_44100_128",
                    text=text,
                    model_id="eleven_multilingual_v2",
                )
                
                with open(output_path, "wb") as audio_file:
                    for chunk in audio_content:
                        audio_file.write(chunk)
                        
                # Instead of storing locally in another queue, send directly to audio_queue
                audio_queue.put(str(output_path))
            except Exception as e:
                print(f"Voice API error: {e}")
                
        await asyncio.sleep(0.1)
