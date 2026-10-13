"""Gradio app: turn a PDF, TXT, or article URL into a podcast."""

import logging
from pathlib import Path
from uuid import uuid4

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAIError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"

MAX_SCRIPT_WORDS = 300
MAX_TTS_CHARACTERS = 4096

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load credentials before importing the current TTS module.
load_dotenv(PROJECT_ROOT / ".env")

from data_processor import process_file, process_url
from llm_processor import create_script
from tts_generator import generate_audio


def make_recap(file_path, article_url):
    """Return the generated script, audio path, and download path."""
    article_url = (article_url or "").strip()

    if not file_path and not article_url:
        raise gr.Error(
            "Please upload a PDF/TXT file or enter an article URL."
        )

    if file_path and article_url:
        raise gr.Error(
            "Please use one source: a file OR an article URL."
        )

    # Step 1: Extract and clean the source text.
    try:
        if article_url:
            text = process_url(article_url)
        else:
            text = process_file(file_path)
    except (ValueError, OSError, RuntimeError) as error:
        raise gr.Error(str(error)) from error

    # Prepare unique output paths before making paid API calls.
    session_id = uuid4().hex
    script_path = OUTPUT_DIR / f"recap_{session_id}.txt"
    audio_path = OUTPUT_DIR / f"recap_{session_id}.mp3"

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise gr.Error("Could not create the outputs folder.") from error

    # Step 2: Generate the script.
    try:
        script = create_script(text, max_words=MAX_SCRIPT_WORDS)
    except OpenAIError as error:
        logger.exception("Script generation API request failed.")
        raise gr.Error(
            "Script generation failed. Check the Terminal for details."
        ) from error
    except (ValueError, RuntimeError) as error:
        raise gr.Error(str(error)) from error

    if not isinstance(script, str) or not script.strip():
        raise gr.Error("The LLM returned an empty or invalid script.")

    script = script.strip()

    # Save the script so it survives any subsequent TTS failure.
    try:
        script_path.write_text(script, encoding="utf-8")
    except OSError as error:
        raise gr.Error(
            "The script was generated but could not be saved."
        ) from error

    logger.info(
        "Script saved: %s (%s characters)",
        script_path,
        len(script),
    )

    # Step 3: Validate the TTS input before sending a request.
    if len(script) > MAX_TTS_CHARACTERS:
        raise gr.Error(
            f"The script has {len(script)} characters. "
            f"TTS accepts at most {MAX_TTS_CHARACTERS} per request. "
            f"The script is saved as {script_path.name}. "
            "No TTS request was sent."
        )

    # Step 4: Generate the audio.
    try:
        saved_audio = generate_audio(
            script,
            path=str(audio_path),
        )
    except OpenAIError as error:
        logger.exception("Audio generation API request failed.")
        raise gr.Error(
            "Audio generation failed. "
            f"Your script is saved as {script_path.name}. "
            "Check the Terminal for details."
        ) from error
    except (ValueError, OSError, RuntimeError) as error:
        raise gr.Error(
            f"Audio generation failed: {error}. "
            f"Your script is saved as {script_path.name}."
        ) from error

    if not isinstance(saved_audio, (str, Path)):
        raise gr.Error("TTS did not return a valid audio file path.")

    saved_audio = Path(saved_audio)

    if not saved_audio.is_file() or saved_audio.stat().st_size == 0:
        raise gr.Error(
            "TTS did not produce a non-empty audio file. "
            f"Your script is saved as {script_path.name}."
        )

    audio_file = str(saved_audio.resolve())

    return script, audio_file, audio_file


demo = gr.Interface(
    fn=make_recap,
    inputs=[
        gr.File(
            label="Upload PDF or TXT",
            type="filepath",
            file_types=[".txt", ".pdf"],
        ),
        gr.Textbox(
            label="Article URL",
            placeholder="https://example.com/article",
        ),
    ],
    outputs=[
        gr.Textbox(label="Recap script", lines=15),
        gr.Audio(label="Recap podcast"),
        gr.File(label="Download podcast"),
    ],
    title="Lesson Recapper",
    description=(
        "Upload a PDF/TXT file OR enter a public article URL. "
        "Get a short podcast recap. "
        "Generation uses paid AI APIs."
    ),
)

if __name__ == "__main__":
    demo.launch(share=False)
    