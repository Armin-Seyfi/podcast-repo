# tts_generator.py
from openai import OpenAI
client = OpenAI()
 
def generate_audio(script, path="outputs/recap.mp3"):
    # Convert text into speech
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=script,
    )
    # Save the audio file
    response.write_to_file(path)
    return path
