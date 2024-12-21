import json
import logging
from openai import OpenAI
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

def send_to_openai(message):
    print(message)
    logger.info(message)
    with open('gpt-prompt.txt', 'r') as prompt_file:
        system_content = prompt_file.read()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": message}
        ],
        max_tokens=50
    )
    formatted_response = format_openai_response(response)
    print(f"GPT: {formatted_response}")
    logger.info(f"GPT: {formatted_response}")
    return formatted_response