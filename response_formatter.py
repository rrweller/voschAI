# Format responses

def format_openai_response(response):
    return response.choices[0].message.content

def format_chat_message(line):
    parts = line.split('!', 1)
    username = parts[0][1:]
    message = parts[1].split('PRIVMSG', 1)[1].split(':', 1)[1]
    return username, message

def extract_emotion(text):
    """Extract emotion prefix and return (emotion, cleaned_text)"""
    emotion = None
    cleaned_text = text
    
    if text.startswith("["):
        end_idx = text.find("]")
        if end_idx != -1:
            potential_emotion = text[1:end_idx].strip().lower()
            if potential_emotion in ["happy", "sad", "angry"]:
                emotion = potential_emotion
                cleaned_text = text[end_idx + 1:].strip()
    
    return emotion, cleaned_text