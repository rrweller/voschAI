import asyncio
from twitch_chat import read_chat_forever
from gpt import send_to_openai
#from voice import process_voice_queue, add_to_voice_queue
from voice_openai import process_voice_queue, add_to_voice_queue
import random
from pathlib import Path
from pygame import mixer
from queue import Queue
import sys

# Create output directory if it doesn't exist
Path("output").mkdir(exist_ok=True)
mixer.init()

# We'll keep this queue for audio file paths
audio_queue = Queue()

channel_name = 'msvosch'
buffer = []

def compute_buffer_size():
    return random.randint(1,1)

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
    Continuously check if there's anything in audio_queue;
    if the mixer is free, load the next file and play it.
    """
    while True:
        if not mixer.music.get_busy() and not audio_queue.empty():
            audio_file = audio_queue.get()
            play_audio_file(audio_file)
        await asyncio.sleep(0.1)

async def main():
    # This queue will hold (username, message) pairs from Twitch
    chat_message_queue = asyncio.Queue()

    buffer_size = compute_buffer_size()
    
    # 1) Launch the background task that continuously reads Twitch messages
    twitch_task = asyncio.create_task(read_chat_forever(channel_name, chat_message_queue))
    
    # 2) Launch the voice queue task (creates MP3 in background)
    voice_task = asyncio.create_task(process_voice_queue(audio_queue))
    
    # 3) Launch audio playback task
    audio_task = asyncio.create_task(process_audio_queue())
    
    # Main loop: pull from chat_message_queue, handle logic
    while True:
        try:
            # Grab next chat message if available
            username, msg = await chat_message_queue.get()  # This will yield if queue is empty
            
            if msg:
                buffer.append({"username": username, "msg": msg})
                print(f"{username}: {msg}")
                
                # If buffer is at capacity, send message to OpenAI -> TTS
                if len(buffer) >= buffer_size:
                    last_message = buffer[-1]
                    gpt_response = send_to_openai(last_message["username"], last_message["msg"])
                    
                    # Add text to ElevenLabs queue
                    add_to_voice_queue(gpt_response)
                    
                    # Clear buffer and recalc next buffer size
                    buffer.clear()
                    buffer_size = compute_buffer_size()
                    
            # Slight pause so event loop can continue tasks
            await asyncio.sleep(0.01)

        except Exception as e:
            print(f"Error in main loop: {e}", file=sys.stderr)
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
