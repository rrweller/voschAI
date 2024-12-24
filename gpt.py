import json
import logging
from openai import OpenAI
from response_formatter import format_openai_response

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

streamer = config['twitch']['channel_name']

def send_to_openai(title, game, username, message):
    logger.info(message)
    with open(config['paths']['prompt'], 'r') as prompt_file:
        system_content = prompt_file.read()
    
    response = client.chat.completions.create(
        model=config['gpt']['model'],
        messages=[
            {"role": "system", "content": f"ALWAYS START THE MESSAGE WITH THE EMOTION YOU WANT TO CONVEY IN THE FORMAT [EMOTION]. THE ONLY VALID OPTIONS FOR EMOTIONS ARE HAPPY, SAD, ANGRY. DO NOT USE ANY OTHER EMOTIONS AS A MESSAGE PREFIX. Use the stream title and current game as context for your response, but do not always mention it, only using it when it makes sense. {system_content}"},
            {"role": "user", "content": f"{streamer} is streaming {game} with the title {title}. You are an AI assistant for {streamer}. Address the message to the user {username} with the message: {message}."},
        ],
        max_tokens=config['gpt']['max_tokens']
    )
    formatted_response = format_openai_response(response)
    logger.info(f"GPT: {formatted_response}")
    return formatted_response