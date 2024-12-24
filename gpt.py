import json
import logging
from openai import OpenAI
from response_formatter import format_openai_response

# Load config
with open('config.json') as f:
    config = json.load(f)

logger = logging.getLogger("my_app.gpt")
logger.setLevel(logging.INFO)
logger.propagate = False

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
AI_name = config['gpt']['ai_name']

def send_to_openai(title, game, username, message):
    logger.info(message)
    with open(config['paths']['prompt'], 'r') as prompt_file:
        system_content = prompt_file.read()
    
    response = client.chat.completions.create(
        model=config['gpt']['model'],
        messages=[
            {"role": "system", "content": f"ALWAYS START THE MESSAGE WITH THE EMOTION YOU WANT TO CONVEY IN THE FORMAT [EMOTION]. THE ONLY VALID OPTIONS FOR EMOTIONS ARE HAPPY, SAD, ANGRY. DO NOT USE ANY OTHER EMOTIONS AS A MESSAGE PREFIX. ALWAYS KEEP THE FORMATTING I HAVE DEFINED. Only use SAD or ANGRY if you REALLY are feeling those emotions and they are intense. Use the stream title and current game as context for your response, but do not always mention it, only using it when it makes sense. Respond with short, concise responses that are natural conversation. Respond in ONLY one or two SHORT sentences. {system_content}"},
            {"role": "user", "content": f"{streamer} is streaming {game} with the title {title}. You are an AI assistant named {AI_name} who helps {streamer}. Respond to the following message sent by {username}: {message}."},
        ],
        max_tokens=config['gpt']['max_tokens']
    )
    formatted_response = format_openai_response(response)
    return formatted_response