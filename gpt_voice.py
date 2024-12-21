import json
import logging
import base64
from openai import OpenAI
from datetime import datetime
from pathlib import Path
from response_formatter import format_openai_response

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

try:
    with open('SECRETS.json') as f:
        secrets = json.load(f)
        auth_token = secrets["openAI"]["authToken"]
except FileNotFoundError:
    raise FileNotFoundError("The SECRETS.json file was not found.")
except KeyError as e:
    raise KeyError(f"Key {e} not found in the SECRETS.json file.")
except json.JSONDecodeError:
    raise ValueError("The SECRETS.json file is not a valid JSON.")

client = OpenAI(api_key=auth_token)

def send_to_openai(username, message):
    logger.info(message)
    with open('gpt-prompt.txt', 'r') as prompt_file:
        system_content = prompt_file.read()
    
    completion = client.chat.completions.create(
        model="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={"voice": "alloy", "format": "mp3"},
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Address the message to the user {username} with the message: {message}"}
        ]
    )

    # Get text response
    formatted_response = format_openai_response(completion.choices[0].message)
    print(f"GPT: {formatted_response}")
    logger.info(f"GPT: {formatted_response}")

    # Save audio file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/voice_output_{timestamp}.mp3"
    
    audio_bytes = base64.b64decode(completion.choices[0].message.audio.data)
    with open(output_file, "wb") as f:
        f.write(audio_bytes)
    
    return formatted_response, output_file