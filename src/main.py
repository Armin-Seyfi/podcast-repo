"""main.py - Gradio app: upload a transcript, get a podcast script and audio recap."""

from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

#load_dotenv()  # load the API key from .env first
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from data_processor import read_transcript, clean_text
from llm_processor import create_script, LENGTHS
from tts_generator import generate_audio

# Save audio in the project's outputs/ folder, no matter where the app is started from
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# What the user sees in the app -> the length key used by create_script()
LENGTH_CHOICES = {
    f"{name.capitalize()} (~{settings['minutes']} min)": name
    for name, settings in LENGTHS.items()
}


def make_recap(file_path, length_label, progress=gr.Progress()):
    """Run the full pipeline: transcript -> clean text -> script -> audio."""
    if file_path is None:
        raise gr.Error("Please upload a transcript (.txt or .pdf)")

    progress(0.05, desc="Reading the transcript...")
    try:
        text = clean_text(read_transcript(file_path))
    except (ValueError, FileNotFoundError) as error:
        raise gr.Error(str(error))

    progress(0.15, desc="Writing the script (longer episodes take a few minutes)...")
    script = create_script(text, length=LENGTH_CHOICES[length_label])

    progress(0.6, desc="Recording the audio...")
    OUTPUT_DIR.mkdir(exist_ok=True)
    audio_path = generate_audio(script, path=str(OUTPUT_DIR / "recap.mp3"))

    return script, audio_path


demo = gr.Interface(
    fn=make_recap,
    inputs=[
        gr.File(
            label="Upload class transcript (.txt or .pdf)",
            type="filepath",
            file_types=[".txt", ".pdf"],
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
    ],
    title="Lesson Recapper",
    description="Upload your class notes and get a podcast-style recap to listen to.",
)

if __name__ == "__main__":
    #demo.launch(share=True)
    demo.launch()