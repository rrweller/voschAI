from elevenlabs import ElevenLabs

client = ElevenLabs(
    api_key="sk_c8a2be6082881748f73409315c80c9dc510b3608da4bd463",
)
audio_content = client.text_to_speech.convert(
    voice_id="9BWtsMINqrJLrRacOk9x",
    output_format="mp3_44100_128",
    text="The first move is what sets everything in motion.",
    model_id="eleven_multilingual_v2",
)

# Save the audio content to a file
with open("output.mp3", "wb") as audio_file:
    for chunk in audio_content:
        audio_file.write(chunk)