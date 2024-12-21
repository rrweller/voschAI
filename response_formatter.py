# Format responses

def format_openai_response(response):
    return response.choices[0].message.content

def format_chat_message(line):
    parts = line.split('!', 1)
    username = parts[0][1:]
    message = parts[1].split('PRIVMSG', 1)[1].split(':', 1)[1]
    return f'{username}: {message}'