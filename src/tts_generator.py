# tts_generator.py
import re
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # make sure the API key is loaded, even if this file is used on its own
client = OpenAI()

# The TTS model accepts at most 4096 characters per request, so we stay safely below that
MAX_CHARS = 4000


def split_text(script, max_chars=MAX_CHARS):
    """Split the script into chunks under max_chars, breaking at paragraphs or sentences."""
    chunks = []
    current = ""

    for paragraph in script.split("\n\n"):
        # A paragraph that is too long on its own gets split into sentences
        pieces = [paragraph] if len(paragraph) <= max_chars else re.split(r"(?<=[.!?])\s+", paragraph)

        for piece in pieces:
            if current and len(current) + len(piece) + 2 > max_chars:
                chunks.append(current)
                current = ""
            current = f"{current}\n\n{piece}" if current else piece

    if current:
        chunks.append(current)
    return chunks


def _speak(text):
    # Convert one chunk of text into speech and return the mp3 bytes
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
    )
    return response.content


def generate_audio(script, path="outputs/recap.mp3"):
    # Convert all chunks at the same time (much faster for long episodes), order is kept
    chunks = split_text(script)
    with ThreadPoolExecutor(max_workers=4) as pool:
        audio_parts = list(pool.map(_speak, chunks))

    # MP3 files can simply be joined one after another into one file
    with open(path, "wb") as file:
        for part in audio_parts:
            file.write(part)
    return path
