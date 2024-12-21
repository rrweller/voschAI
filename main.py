import asyncio
from twitch_chat import read_twitch_chat
from gpt import send_to_openai
from voice import process_voice_queue, add_to_voice_queue
import random
from pathlib import Path
from pygame import mixer
from queue import Queue

# Create output directory if it doesn't exist
Path("output").mkdir(exist_ok=True)
mixer.init()
audio_queue = Queue()

channel_name = 'msvosch'
buffer = []

def compute_buffer_size():
    return random.randint(2,4)

def play_audio_file(audio_file):
    """
    This function attempts to load and play audio_file immediately.
    Returns True if playback started, False otherwise.
    """
    if not mixer.music.get_busy():
        try:
            mixer.music.load(audio_file)
            mixer.music.play()
            return True
        except Exception as e:
            print(f"Audio playback error: {e}")
    return False

async def process_audio_queue():
    """
    Continuously check if there's anything in the audio_queue;
    if the mixer is free, load the next file and play it.
    """
    while True:
        if not mixer.music.get_busy() and not audio_queue.empty():
            audio_file = audio_queue.get()
            play_audio_file(audio_file)
        await asyncio.sleep(0.1)

async def main():
    buffer_size = compute_buffer_size()
    
    # Launch the voice queue task (creates MP3 in background)
    voice_task = asyncio.create_task(process_voice_queue(audio_queue))
    
    # Launch audio playback task
    audio_task = asyncio.create_task(process_audio_queue())
    
    while True:
        try:
            # Read one chat message asynchronously
            chat_task = asyncio.create_task(read_twitch_chat(channel_name))
            msg = await chat_task
            
            if msg:
                buffer.append(msg)
                print(msg)
                
                # If buffer is at capacity, send message to OpenAI -> ElevenLabs
                if len(buffer) >= buffer_size:
                    # Send the most recent chat message to OpenAI
                    gpt_response = send_to_openai(buffer[-1])
                    
                    # Add text to ElevenLabs queue (which will produce an MP3)
                    add_to_voice_queue(gpt_response)
                    
                    # Clear buffer and recalc the next buffer size
                    buffer.clear()
                    buffer_size = compute_buffer_size()
                    
        except Exception as e:
            print(f"Error in main loop: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
