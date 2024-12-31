import keyboard
import sounddevice as sd
import numpy as np
import wave
import json
import os
import tempfile
import logging
from datetime import datetime
from openai import OpenAI
from pathlib import Path
from response_formatter import extract_emotion
import time

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Custom formatter that only shows the message
class CleanFormatter(logging.Formatter):
    def format(self, record):
        return record.getMessage()

# Create console handler with clean formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(CleanFormatter())
logger.handlers = [console_handler]

# Load config
with open('config.json') as f:
    config = json.load(f)
    
with open('SECRETS.json') as f:
    secrets = json.load(f)
    auth_token = secrets["openAI"]["authToken"]

client = OpenAI(api_key=auth_token)
RECORD_KEY = config['ui'].get('record_key', 'k')  # Default to 'k'
SAMPLE_RATE = 44100
MIN_AUDIO_LENGTH = 0.5  # Minimum audio length in seconds
voice_mode = config['voice']['mode']

class VoiceRecorder:
    def __init__(self, gpt_callback):
        self.recording = False
        self.audio_data = []
        self.gpt_callback = gpt_callback

    def start_recording(self):
        if not self.recording:
            print("\nStarting recording...")  # Simplified log message
            self.recording = True
            self.audio_data = []
            
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"Audio status: {status}")  # Simplified warning
                if self.recording:
                    self.audio_data.append(indata.copy())
            
            self.stream = sd.InputStream(
                channels=1,
                samplerate=SAMPLE_RATE,
                callback=audio_callback,
                dtype=np.float32
            )
            self.stream.start()
            print("\nRecording... (Release key to stop)")

    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.stream.stop()
            self.stream.close()
            
            if len(self.audio_data) > 0:
                audio_data = np.concatenate(self.audio_data, axis=0)
                
                # Check minimum length
                if len(audio_data) / SAMPLE_RATE < MIN_AUDIO_LENGTH:
                    print("\nRecording too short, ignored")
                    print("\nReady to record...")
                    return
                
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                    wav_path = temp_wav.name
                    with wave.open(wav_path, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(SAMPLE_RATE)
                        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
                
                try:
                    with open(wav_path, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text"
                        )
                    logger.debug(f"Whisper API response: {transcription}")
                    if not transcription.strip():
                        logger.debug("Transcription result is empty.")
                        raise ValueError("Transcription result is empty.")
                    if transcription:
                        print(f"\nTranscribed: {transcription}")
                        # Get GPT response through callback
                        gpt_response = self.gpt_callback(transcription)
                        
                        if gpt_response:
                            # Extract emotion from GPT response
                            emotion, cleaned_text = extract_emotion(gpt_response)
                            print(f"[GPT RESPONSE][{emotion}]: {cleaned_text}")
                            
                            if voice_mode == 'openai':
                                from voice_openai import add_to_voice_queue
                            elif voice_mode == 'elevenlabs':
                                from voice import add_to_voice_queue
                                
                            # Add to voice queue with extracted emotion
                            add_to_voice_queue(cleaned_text, emotion=emotion)
                    
                except Exception as e:
                    logger.error(f"Transcription error: {str(e)}")
                    print(f"\nError transcribing audio: {str(e)}")
                    
                finally:
                    try:
                        os.unlink(wav_path)
                    except Exception as e:
                        logger.error(f"Error cleaning up temp file: {str(e)}")
            
            print("\nReady to record...")

def start_voice_ui(gpt_callback):
    recorder = VoiceRecorder(gpt_callback)
    time.sleep(3)
    print(f"\nPress and hold {RECORD_KEY} to record...")
    
    keyboard.on_press_key(RECORD_KEY, lambda _: recorder.start_recording())
    keyboard.on_release_key(RECORD_KEY, lambda _: recorder.stop_recording())

    try:
        keyboard.wait('esc')
    except KeyboardInterrupt:
        pass