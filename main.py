import asyncio
from twitch_chat import read_chat_forever
from gpt import send_to_openai
from pathlib import Path
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
from pygame import mixer
from queue import Queue
import json
import sys
import logging
from ui import start_voice_ui
import threading

# Import from avatar
from avatar import run_avatar_server, set_avatar_state

# Load config
with open('config.json') as f:
    config = json.load(f)

# Create custom filter
class ChatFilter(logging.Filter):
    def filter(self, record):
        return "HTTP Request" not in record.getMessage()

# Configure logging with UTF-8 encoding
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create file handler with simplified format
file_handler = logging.FileHandler('gpt.log', encoding='utf-8')
file_handler.setFormatter(
    logging.Formatter('%(asctime)s: %(message)s', 
                     datefmt='%Y-%m-%d %H:%M:%S')
)
file_handler.addFilter(ChatFilter())
logger.addHandler(file_handler)

# Disable ALL OpenAI logging
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("openai.api_requestor").setLevel(logging.ERROR)
logging.getLogger("openai.http_client").setLevel(logging.ERROR)

# Disable httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)

Path(config['paths']['output_dir']).mkdir(exist_ok=True)
mixer.init()

audio_queue = Queue()
channel_name = config['twitch']['channel_name']

current_game = None
current_title = None

# This is our new AI name from config
AI_NAME = config['gpt'].get('ai_name', 'assistant')

voice_mode = config['voice']['mode']
if voice_mode == 'openai':
    from voice_openai import process_voice_queue, add_to_voice_queue
else:
    from voice import process_voice_queue, add_to_voice_queue

def play_audio_file(audio_file):
    if not mixer.music.get_busy():
        try:
            mixer.music.load(audio_file)
            mixer.music.play()
            return True
        except Exception as e:
            print(f"Audio playback error: {e}")
    return False

async def process_audio_queue():
    while True:
        # If mixer isn't busy AND we have a file, play it
        if not mixer.music.get_busy() and not audio_queue.empty():
            audio_file, emotion = audio_queue.get()
            if emotion:
                set_avatar_state(emotion=emotion, talking=True)
            else:
                set_avatar_state(talking=True)

            play_audio_file(audio_file)

        await asyncio.sleep(0.1)

        # If playback ended AND queue empty, set talking=False
        if not mixer.music.get_busy() and audio_queue.empty():
            set_avatar_state(talking=False)

def process_voice_input(text):
    global current_title, current_game
    # Create special voice message that gets priority
    response = send_to_openai(current_title, current_game, "Streamer", text)
    if response:
        add_to_voice_queue(response)

async def main():
    # This queue receives all Twitch chat messages plus ("__channel_info__", ...) events
    chat_message_queue = asyncio.Queue()
    
    # We'll store the last known channel title/game
    global current_title, current_game

    # Start the avatar server
    asyncio.create_task(run_avatar_server())

    # Launch Twitch reading & TTS tasks
    twitch_task = asyncio.create_task(read_chat_forever(channel_name, chat_message_queue, config))
    voice_task  = asyncio.create_task(process_voice_queue(audio_queue))
    audio_task  = asyncio.create_task(process_audio_queue())
    
    # This is our queue for messages that specifically mention the AI
    mention_queue = []

    # Start the voice UI thread
    voice_ui_thread = threading.Thread(
        target=start_voice_ui,
        args=(process_voice_input,),
        daemon=True
    )
    voice_ui_thread.start()

    while True:
        try:
            # 1) Wait for the next incoming item from Twitch
            username, msg_or_tuple = await chat_message_queue.get()

            # 2) Check if it's channel info or normal chat
            if username == "__channel_info__":
                title, game_name = msg_or_tuple
                current_title = title
                current_game = game_name
                print(f"[CHANNEL INFO] Title='{title}', Game='{game_name}'")
                logger.info(f"[CHANNEL INFO] Title='{title}', Game='{game_name}'")
            
            else:
                # A normal chat message
                msg = msg_or_tuple
                if msg:
                    # 3) Does this message mention the AI name?
                    #    We'll do a case-insensitive check
                    if AI_NAME.lower() in msg.lower():
                        # Add to mention_queue
                        mention_queue.append({"username": username, "msg": msg})
                        # If we exceed 5, pop the oldest
                        if len(mention_queue) > 5:
                            mention_queue.pop(0)
            
            # 4) If mention_queue has messages, respond to them (FIFO: pop(0))
            if mention_queue:
                mention = mention_queue.pop(0)
                user = mention["username"]
                text = mention["msg"]

                print(f"[MENTION] {user}: {text}")
                logger.info(f"[MENTION] {user}: {text}")

                # 5) Send to GPT
                gpt_response = send_to_openai(
                    current_title,
                    current_game,
                    user,
                    text
                )

                # 6) Check for emotion prefix ([happy], [sad], [angry])
                emotion = None
                if gpt_response.startswith("["):
                    end_idx = gpt_response.find("]")
                    if end_idx != -1:
                        potential_emotion = gpt_response[1:end_idx].strip().lower()
                        if potential_emotion in ["happy", "sad", "angry"]:
                            emotion = potential_emotion
                            gpt_response = gpt_response[end_idx + 1:].strip()

                print(f"[GPT RESPONSE][{emotion}]: {gpt_response}")
                logger.info(f"[GPT RESPONSE][{emotion}]: {gpt_response}")

                # 7) Send result to TTS queue
                add_to_voice_queue(gpt_response, emotion=emotion)

            # Let the loop breathe
            await asyncio.sleep(0.01)

        except Exception as e:
            print(f"Error in main loop: {e}", file=sys.stderr)
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())