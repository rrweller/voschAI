import asyncio
from response_formatter import format_chat_message

async def read_blacklist():
    try:
        with open('blacklist.txt', 'r') as f:
            return set(line.strip() for line in f)
    except Exception as e:
        print(f"Error reading blacklist: {e}")

async def read_chat_forever(channel, chat_queue):
    server = 'irc.chat.twitch.tv'
    port = 6667
    nickname = 'justinfan12345'  # Anonymous connection
    channel = f'#{channel}'

    reader, writer = await asyncio.open_connection(server, port)
    writer.write(f'NICK {nickname}\n'.encode('utf-8'))
    writer.write(f'JOIN {channel}\n'.encode('utf-8'))

    blacklist = await read_blacklist()

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
                    blacklist = await read_blacklist()
                    username, message = format_chat_message(line)
                    # Check if the username is not in the blacklist
                    if username and message and username not in blacklist:
                        await chat_queue.put((username, message))

        await asyncio.sleep(0.01)  # Let other tasks run
