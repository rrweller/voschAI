import json
import asyncio
from openai import OpenAI
from twitch_chat import buffer, read_twitch_chat
from response_formatter import format_openai_response

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

async def process_chat_messages():
    while True:
        if buffer:
            message = buffer.pop(0)
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "You are a chatbot in a Twitch chat. Respond naturally as if you were another viewer. Do not respond with more than 2 sentences."},
                    {"role": "user", "content": message}
                ]
            )
            formatted_response = format_openai_response(response)
            print(f"GPT:", formatted_response)
        await asyncio.sleep(1)  # Adjust the sleep time as needed

async def main():
    channel_name = 'littlebunny_x'
    chat_task = asyncio.create_task(read_twitch_chat(channel_name))
    process_task = asyncio.create_task(process_chat_messages())
    await asyncio.gather(chat_task, process_task)

if __name__ == "__main__":
    asyncio.run(main())