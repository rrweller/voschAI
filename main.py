import asyncio
from twitch_chat import read_chat_forever
from gpt import send_to_openai
import random
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
buffer = []

voice_mode = config['voice']['mode']
if voice_mode == 'openai':
    from voice_openai import process_voice_queue, add_to_voice_queue
else:
    from voice import process_voice_queue, add_to_voice_queue

def compute_buffer_size():
    return random.randint(
        config['twitch']['buffer_size']['min'],
        config['twitch']['buffer_size']['max']
    )

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
        if not mixer.music.get_busy() and not audio_queue.empty():
            # We expect (audio_file, emotion)
            audio_file, emotion = audio_queue.get()

            # Now we set the avatar emotion only right before playback
            if emotion:
                set_avatar_state(emotion=emotion, talking=True)
            else:
                # If none given, keep current emotion, just set talking=True
                set_avatar_state(talking=True)

            played = play_audio_file(audio_file)
            
        await asyncio.sleep(0.1)

        if not mixer.music.get_busy():
            # If playback ended, set talking=False. The server logic may revert to happy if needed.
            set_avatar_state(talking=False)

async def main():
    chat_message_queue = asyncio.Queue()
    buffer_size = compute_buffer_size()

    # Start avatar server
    asyncio.create_task(run_avatar_server())

    # Launch twitch chat, TTS, audio playback
    twitch_task = asyncio.create_task(read_chat_forever(channel_name, chat_message_queue, config))
    voice_task  = asyncio.create_task(process_voice_queue(audio_queue))
    audio_task  = asyncio.create_task(process_audio_queue())
    
    current_title = None
    current_game  = None
    
    while True:
        try:
            username, msg_or_tuple = await chat_message_queue.get()
            if username == "__channel_info__":
                title, game_name = msg_or_tuple
                current_title = title
                current_game = game_name
                print(f"[CHANNEL INFO] Title='{title}', Game='{game_name}'")
                continue
            else:
                msg = msg_or_tuple
                if msg:
                    buffer.append({"username": username, "msg": msg})

                    if len(buffer) >= buffer_size:
                        last_message = buffer[-1]
                        gpt_response = send_to_openai(
                            current_title,
                            current_game,
                            last_message["username"],
                            last_message["msg"]
                        )
                        print(f'{last_message["username"]}: {last_message["msg"]}')
                        # Extract emotion from brackets [happy], [sad], [angry]
                        emotion = None
                        if gpt_response.startswith("["):
                            end_idx = gpt_response.find("]")
                            if end_idx != -1:
                                potential_emotion = gpt_response[1:end_idx].strip().lower()
                                if potential_emotion in ["happy", "sad", "angry"]:
                                    emotion = potential_emotion
                                    gpt_response = gpt_response[end_idx + 1:].strip()

                        print(f"GPT says (emotion={emotion}): {gpt_response}")

                        # Instead of setting emotion now, pass to TTS queue
                        # TTS -> (audio_file, emotion) -> audio_queue -> playback
                        add_to_voice_queue(gpt_response, emotion=emotion)

                        buffer.clear()
                        buffer_size = compute_buffer_size()

            await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Error in main loop: {e}", file=sys.stderr)
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
