import json
import logging
import os
from openai import OpenAI
from response_formatter import format_openai_response
from datetime import datetime

# Load config
with open('config.json') as f:
    config = json.load(f)

logger = logging.getLogger("my_app.gpt")
logger.setLevel(logging.INFO)
#logger.propagate = False

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

data_dir = config['user_history']['data_dir']
max_messages = config['user_history']['max_messages']

def save_message(username, message_type, content, ai_name=None):
    """
    Saves a message (user or AI) to the user's JSON file and enforces the max message limit.
    User messages are used to check the limit; AI messages are paired with the user messages.

    Args:
        username (str): The user's name.
        message_type (str): Either "user" or "ai".
        content (str): The message content.
        ai_name (str): The AI's name (for storing AI responses).
    """
    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)
    user_file = os.path.join(data_dir, f"{username}.json")
    
    # Check if the file exists, if not, create it with an initial structure
    if not os.path.exists(user_file):
        user_data = {"username": username, "messages": []}
        with open(user_file, "w") as f:
            json.dump(user_data, f, indent=4)
    else:
        with open(user_file, "r") as f:
            user_data = json.load(f)
    
    # Add new message
    new_message = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": message_type,
        "content": content
    }
    if message_type == "ai" and ai_name:
        new_message["name"] = ai_name  # Add AI name to responses
    
    user_data["messages"].append(new_message)
    
    # Enforce message limit (only count user messages)
    user_messages = [msg for msg in user_data["messages"] if msg["type"] == "user"]
    if len(user_messages) > max_messages:
        # Find the oldest user message and its corresponding AI response
        oldest_user_index = next(i for i, msg in enumerate(user_data["messages"]) if msg["type"] == "user")
        del user_data["messages"][oldest_user_index]  # Remove oldest user message
        
        # Remove corresponding AI response (if exists and follows the user message)
        if oldest_user_index < len(user_data["messages"]) and user_data["messages"][oldest_user_index]["type"] == "ai":
            del user_data["messages"][oldest_user_index]
    
    # Save updated data back to the file and return its content
    with open(user_file, "w") as f:
        json.dump(user_data, f, indent=4)
        
    # Return properly formatted message history
    return [
        {"role": "user" if msg["type"] == "user" else "assistant", 
         "content": msg["content"]}
        for msg in user_data["messages"]
    ]

def send_to_openai(title, game, username, message):
    logger.info(f"Received following message from {username}: {message}, storing into user history.")
    user_context = save_message(username, "user", message, AI_name)
    logger.info(f"User context: {user_context}")
    
    prompt_path = config['paths']['prompt']
    
    # Check if prompt file exists, create if not
    if not os.path.exists(prompt_path):
        default_prompt = ""
        with open(prompt_path, 'w') as f:
            f.write(default_prompt)
        print("Error: Prompt file not found. Created an empty prompt file. Please add your prompt to the file.")
    
    with open(prompt_path, 'r') as prompt_file:
        system_content = prompt_file.read()

    system_message = {
        "role": "system",
        "content": (
            f"ALWAYS START THE MESSAGE WITH THE EMOTION YOU WANT TO CONVEY IN THE FORMAT [EMOTION]. "
            f"THE ONLY VALID OPTIONS FOR EMOTIONS ARE HAPPY, SAD, ANGRY. DO NOT USE ANY OTHER EMOTIONS AS A MESSAGE PREFIX. "
            f"ALWAYS KEEP THE FORMATTING I HAVE DEFINED. Only use SAD or ANGRY if you REALLY are feeling those emotions and they are intense. "
            f"Use the stream title and current game as context for your response, but do not always mention it, only using it when it makes sense. "
            f"Respond with short, concise responses that are natural conversation. Respond in ONLY one or two SHORT sentences. {system_content}"
        )
    }

    prompt = {
        "role": "user",
        "content": (
            f"{streamer} is streaming {game} with the title {title}. "
            f"You are an AI assistant named {AI_name} who helps {streamer}. "
            f"Here is the conversation history with {username} including your responses:"
        )
    }

    api_messages = [system_message, prompt] + user_context + [
        {"role": "user", "content": f"Respond to the following message sent by {username}: {message}."}
    ]
    logger.info(f"Sending the following request to OpenAI: {api_messages}")
    
    response = client.chat.completions.create(
        model=config['gpt']['model'],
        messages=api_messages,
        max_tokens=config['gpt']['max_tokens']
    )
    formatted_response = format_openai_response(response)
    logger.info(formatted_response)
    return formatted_response