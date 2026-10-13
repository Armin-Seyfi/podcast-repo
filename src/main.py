"""Gradio app: turn a PDF, TXT, or article URL into a podcast."""

import logging
from pathlib import Path
from uuid import uuid4

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAIError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load credentials before importing the current TTS module.
load_dotenv(PROJECT_ROOT / ".env")

from data_processor import process_file, process_url
from llm_processor import create_script, LENGTHS
from tts_generator import generate_audio


# Map the displayed label to the length key used by the LLM.
LENGTH_CHOICES = {
    f"{name.capitalize()} (~{settings['minutes']} min)": name
    for name, settings in LENGTHS.items()
}


def make_recap(
    file_path,
    article_url,
    length_label,
    progress=gr.Progress(),
):
    """Return the script, audio path, and download path."""
    article_url = (article_url or "").strip()

    if not file_path and not article_url:
        raise gr.Error(
            "Please upload a PDF/TXT file or enter an article URL."
        )

    if file_path and article_url:
        raise gr.Error(
            "Please use one source: a file OR an article URL."
        )

    if length_label not in LENGTH_CHOICES:
        raise gr.Error("Please select a valid podcast length.")

    # Step 1: Extract and clean the source text.
    progress(0.05, desc="Reading the source...")

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

    # Step 2: Generate the script using the selected length.
    progress(0.2, desc="Generating the podcast script...")

    try:
        script = create_script(
            text,
            length=LENGTH_CHOICES[length_label],
        )
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

    # Preserve the script even if TTS fails.
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

    # Step 3: Generate audio. The TTS module handles chunking.
    progress(0.6, desc="Recording the audio...")

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

    try:
        if not saved_audio.is_file() or saved_audio.stat().st_size == 0:
            raise RuntimeError("TTS did not produce a non-empty audio file.")
    except (OSError, RuntimeError) as error:
        raise gr.Error(
            f"{error} Your script is saved as {script_path.name}."
        ) from error

    audio_file = str(saved_audio.resolve())

    progress(1.0, desc="Podcast ready!")

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
        gr.Radio(
            choices=list(LENGTH_CHOICES),
            value=list(LENGTH_CHOICES)[0],
            label="Podcast length",
        ),
    ],
    outputs=[
        gr.Textbox(label="Recap script", lines=15),
        gr.Audio(label="Recap podcast"),
        gr.File(label="Download podcast"),
    ],
    title="Lesson Recapper",
    description=(
        "Upload a PDF/TXT file OR enter a public article URL "
        "and choose an approximate podcast length. "
        "Generation uses paid AI APIs."
    ),
)

if __name__ == "__main__":
    demo.launch(share=False)
    
    