"""Connect document processing, script generation, and audio generation."""

import argparse
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from src.data_processor import process_file


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def make_podcast(file_path: str, max_words: int = 600) -> str:
    """Generate a podcast and return the absolute audio file path."""
    text = process_file(file_path)

    # Load credentials before importing the current TTS module.
    load_dotenv(PROJECT_ROOT / ".env")

    from src.llm_processor import create_script
    from src.tts_generator import generate_audio

    print("Generating podcast script...")
    script = create_script(text, max_words=max_words)

    if not isinstance(script, str) or not script.strip():
        raise RuntimeError("The LLM returned an empty or invalid script.")

    output_dir = PROJECT_ROOT / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use unique names to preserve previous results.
    session_id = uuid4().hex
    script_path = output_dir / f"recap_{session_id}.txt"
    audio_path = output_dir / f"recap_{session_id}.mp3"

    # Preserve the script even if audio generation fails.
    script_path.write_text(script, encoding="utf-8")
    print(f"Script saved: {script_path}")

    print("Generating podcast audio...")
    saved_path = generate_audio(script, path=str(audio_path))

    saved_audio = Path(saved_path)

    if not saved_audio.is_file() or saved_audio.stat().st_size == 0:
        raise RuntimeError("TTS did not produce a non-empty audio file.")

    return str(saved_audio.resolve())


def main():
    parser = argparse.ArgumentParser(description="Podcast Studio")
    parser.add_argument("file_path", help="Path to a PDF or TXT file")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate script and audio using paid API calls",
    )
    parser.add_argument("--max-words", type=int, default=600)
    args = parser.parse_args()

    if args.max_words <= 0:
        parser.error("--max-words must be a positive number.")

    if args.generate:
        audio_path = make_podcast(args.file_path, args.max_words)
        print(f"Podcast saved: {audio_path}")
    else:
        text = process_file(args.file_path)
        print(text[:1500])
        print(f"\nTotal characters: {len(text)}")
        print("Preview only. No LLM or TTS API calls were made.")


if __name__ == "__main__":
    main()