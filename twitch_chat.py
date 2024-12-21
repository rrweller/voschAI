#read chat messages from channel

import asyncio
from response_formatter import format_chat_message



async def read_twitch_chat(channel):
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
            writer.write('PONG\n'.encode('utf-8'))
        else:
            for line in response.split('\r\n'):
                if "PRIVMSG" in line:
                    formatted_message = format_chat_message(line)
                    return formatted_message