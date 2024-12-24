import asyncio
import json
import aiohttp  # We'll use aiohttp for async calls to the Twitch API
import requests  # We'll use requests for synchronous token retrieval
from response_formatter import format_chat_message
import os

SECRETS_FILE = 'secrets.json'

def ensure_oauth_token():
    """
    Ensures the 'twitch' object in secrets.json has a valid oauth_token.
    If missing or empty, retrieve a new one from Twitch and save it.
    
    Returns:
        (client_id, client_secret, oauth_token)
    """
    # 1) Read secrets
    if not os.path.isfile(SECRETS_FILE):
        raise FileNotFoundError(f"Could not find {SECRETS_FILE}")

    with open(SECRETS_FILE, 'r') as f:
        secrets = json.load(f)

    # 2) Make sure there's a "twitch" section
    if "twitch" not in secrets:
        secrets["twitch"] = {}

    # 3) Extract or set defaults for client_id / client_secret / oauth_token
    client_id = secrets["twitch"].get("client_id", "")
    client_secret = secrets["twitch"].get("client_secret", "")
    oauth_token = secrets["twitch"].get("oauth_token", "")

    # 4) If oauth_token is missing or empty, retrieve a new one
    if not oauth_token:
        print("No valid Twitch OAuth token found. Retrieving new token...")
        new_token = get_oauth_token(client_id, client_secret)
        if new_token:
            secrets["twitch"]["oauth_token"] = new_token
            oauth_token = new_token
            # 5) Write the updated secrets back to file
            with open(SECRETS_FILE, 'w') as out_f:
                json.dump(secrets, out_f, indent=2)
            print("New OAuth token saved to secrets.json")
        else:
            raise ValueError("Failed to obtain a new Twitch OAuth token.")

    return client_id, client_secret, oauth_token

def get_oauth_token(client_id, client_secret):
    """
    Retrieves an OAuth token from Twitch using client_credentials flow.
    """
    url = "https://id.twitch.tv/oauth2/token"
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'user:read:broadcast'
    }

    response = requests.post(url, data=payload)
    data = response.json()
    
    if 'access_token' in data:
        return data['access_token']
    else:
        # Print any error from Twitch
        print("Error getting OAuth token:", data)
        return None

async def update_channel_info(channel_name, chat_queue, client_id, oauth_token):
    """
    Periodically fetch the channel's title and current game using the Twitch Helix API.
    Every 5 minutes, put a special tuple into chat_queue with the updated info.
    If a 401 (Unauthorized) occurs, print a message about deleting old token.
    """
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: Search channels by name to find the broadcaster ID
                search_url = f"https://api.twitch.tv/helix/search/channels?query={channel_name}"
                async with session.get(search_url, headers=headers) as resp:
                    # If token is invalid/expired, Twitch returns 401
                    if resp.status == 401:
                        print("\n[WARNING] Twitch OAuth token may be expired or invalid.")
                        print("Please delete the old token in secrets.json so a new one can be generated.\n")
                        # Sleep 5 minutes before next attempt
                        await asyncio.sleep(300)
                        continue

                    search_data = await resp.json()

                    broadcaster_id = None
                    if 'data' in search_data:
                        for chan in search_data['data']:
                            # Compare channel login with config channel_name
                            if chan['broadcaster_login'].lower() == channel_name.lower():
                                broadcaster_id = chan['id']
                                break
                    
                    # If we couldn't find it, just skip for now
                    if not broadcaster_id:
                        print(f"Could not find broadcaster ID for {channel_name}")
                        await asyncio.sleep(300)  # 5 minutes
                        continue
                
                # Step 2: Now get channel info (title, game_id) using broadcaster_id
                info_url = f"https://api.twitch.tv/helix/channels?broadcaster_id={broadcaster_id}"
                async with session.get(info_url, headers=headers) as resp:
                    if resp.status == 401:
                        print("\n[WARNING] Twitch OAuth token may be expired or invalid.")
                        print("Please delete the old token in secrets.json so a new one can be generated.\n")
                        await asyncio.sleep(300)
                        continue

                    channel_data = await resp.json()
                    
                    if 'data' in channel_data and channel_data['data']:
                        channel_info = channel_data['data'][0]
                        title = channel_info.get('title', '')
                        game_name = channel_info.get('game_name', '')
                        await chat_queue.put(("__channel_info__", (title, game_name)))

        except Exception as e:
            print(f"Error fetching channel info: {e}")

        # Wait 5 minutes before next update
        await asyncio.sleep(300)

async def read_blacklist(config):
    try:
        with open(config['paths']['blacklist'], 'r') as f:
            return set(line.strip() for line in f)
    except Exception as e:
        print(f"Error reading blacklist: {e}")
        return set()

async def read_chat_forever(channel, chat_queue, config):
    """
    Connects to Twitch IRC and reads chat messages in a loop.
    Also starts a background task to fetch channel info every 5 minutes.
    """
    # 1) Ensure we have a valid OAuth token
    client_id, client_secret, oauth_token = ensure_oauth_token()
    
    # 2) Connect to Twitch IRC. We can continue using an anonymous nickname,
    #    since we only need the token for API calls, not for IRC auth.
    server = 'irc.chat.twitch.tv'
    port = 6667
    nickname = 'justinfan12345'  # Anonymous connection
    channel_str = f'#{channel}'

    reader, writer = await asyncio.open_connection(server, port)
    writer.write(f'NICK {nickname}\n'.encode('utf-8'))
    writer.write(f'JOIN {channel_str}\n'.encode('utf-8'))

    # 3) Kick off the background task to update channel info every 5 minutes
    asyncio.create_task(
        update_channel_info(channel_name=channel,
                            chat_queue=chat_queue,
                            client_id=client_id,
                            oauth_token=oauth_token)
    )

    # 4) Read the blacklist
    blacklist = await read_blacklist(config)

    # 5) Main loop to read chat
    while True:
        response = await reader.read(2048)
        response = response.decode('utf-8')

        if response.startswith('PING'):
            # Respond with PONG to keep connection alive
            writer.write('PONG\n'.encode('utf-8'))
            await writer.drain()
        else:
            for line in response.split('\r\n'):
                if "PRIVMSG" in line:
                    # Re-read blacklist in case it changed
                    blacklist = await read_blacklist(config)
                    username, message = format_chat_message(line)
                    
                    # Check if the username is not in the blacklist
                    if username and message and username not in blacklist:
                        await chat_queue.put((username, message))

        # Let other tasks run
        await asyncio.sleep(0.01)