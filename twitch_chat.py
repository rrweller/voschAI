import asyncio
from response_formatter import format_chat_message

async def read_chat_forever(channel, chat_queue):
    server = 'irc.chat.twitch.tv'
    port = 6667
    nickname = 'justinfan12345'  # Anonymous connection
    channel = f'#{channel}'

    reader, writer = await asyncio.open_connection(server, port)
    writer.write(f'NICK {nickname}\n'.encode('utf-8'))
    writer.write(f'JOIN {channel}\n'.encode('utf-8'))

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
                    username, message = format_chat_message(line)
                    # Instead of returning, we put the message in the queue
                    await chat_queue.put((username, message))

        await asyncio.sleep(0.01)  # Let other tasks run
