import asyncio
from twitch_chat import read_chat_forever
from gpt import send_to_openai
from pathlib import Path
from pygame import mixer
from queue import Queue
import json
import sys

# Import from avatar
from avatar import run_avatar_server, set_avatar_state

# Load config
with open('config.json') as f:
    config = json.load(f)

Path(config['paths']['output_dir']).mkdir(exist_ok=True)
mixer.init()

audio_queue = Queue()
channel_name = config['twitch']['channel_name']

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
            print(f"Playing: {audio_file}")

        await asyncio.sleep(0.1)

        # If playback ended AND queue empty, set talking=False
        if not mixer.music.get_busy() and audio_queue.empty():
            set_avatar_state(talking=False)

async def main():
    # This queue receives all Twitch chat messages plus ("__channel_info__", ...) events
    chat_message_queue = asyncio.Queue()
    
    # We'll store the last known channel title/game
    current_title = None
    current_game = None

    # Start the avatar server
    asyncio.create_task(run_avatar_server())

    # Launch Twitch reading & TTS tasks
    twitch_task = asyncio.create_task(read_chat_forever(channel_name, chat_message_queue, config))
    voice_task  = asyncio.create_task(process_voice_queue(audio_queue))
    audio_task  = asyncio.create_task(process_audio_queue())
    
    # This is our queue for messages that specifically mention the AI
    mention_queue = []

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

                print(f"GPT => (emotion={emotion}): {gpt_response}")

                # 7) Send result to TTS queue
                add_to_voice_queue(gpt_response, emotion=emotion)

            # Let the loop breathe
            await asyncio.sleep(0.01)

        except Exception as e:
            print(f"Error in main loop: {e}", file=sys.stderr)
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
