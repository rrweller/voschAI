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
    
    # Load existing history or create a new structure
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)
    else:
        user_data = {"username": username, "messages": []}

    # Add new message
    new_message = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": message_type,
        "content": content
    }
    
    user_data["messages"].append(new_message)

    # Enforce message limit (only count user messages)
    user_messages = [msg for msg in user_data["messages"] if msg["type"] == "user"]
    if len(user_messages) > max_messages:
        # Remove the oldest user message and its paired AI response
        oldest_user_index = next(i for i, msg in enumerate(user_data["messages"]) if msg["type"] == "user")
        del user_data["messages"][oldest_user_index]
        
        # Remove corresponding AI response (if exists)
        if oldest_user_index < len(user_data["messages"]) and user_data["messages"][oldest_user_index]["type"] == "ai":
            del user_data["messages"][oldest_user_index]

    # Save updated history
    with open(user_file, "w", encoding="utf-8") as f:
        json.dump(user_data, f, indent=4, ensure_ascii=False)

def read_user_history(username):
    """
    Reads the user's message history from their JSON file and formats it for the OpenAI API.

    Args:
        username (str): The user's name.

    Returns:
        list: A list of formatted messages (role: user/assistant, content: message).
    """
    user_file = os.path.join(data_dir, f"{username}.json")

    if os.path.exists(user_file):
        with open(user_file, "r") as f:
            user_data = json.load(f)
        return [
            {"role": "user" if msg["type"] == "user" else "assistant", "content": msg["content"]}
            for msg in user_data["messages"]
        ]
    else:
        return []

def send_to_openai(title, game, username, message):
    message = message.replace("\n", " ").strip()
    logger.info(f"Received following message from {username}: {message}")
    
    # Fetch the current user history
    user_context = read_user_history(username)
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
        system_content = system_content.replace("\n", " ").strip()

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

    # Save the current message and the AI response
    save_message(username, "user", message)  # Save the user's message
    save_message(username, "ai", formatted_response, ai_name=AI_name)  # Save the AI's response

    return formatted_response