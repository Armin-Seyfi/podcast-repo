# Lesson Recapper — Podcast Studio

Turn class notes or a public web article into a single-host podcast recap. Upload a text-based PDF or UTF-8 TXT file, or enter an article URL, then choose an approximate episode length. The Gradio app displays the generated script and lets you play and download the MP3.

Built as a three-person Ironhack AI Consulting and Integration Bootcamp project.

## How it works

1. **Data processing:** extract source text and normalize whitespace, Unicode, and common ligatures.
2. **Script generation:** use OpenAI `gpt-4o-mini` to write a spoken recap for the selected length.
3. **Audio generation:** use OpenAI `tts-1` with the `alloy` voice to generate audio chunks and combine them into an MP3.
4. **Interface:** Gradio connects the stages and displays the results.

| Module | Responsibility |
|---|---|
| `src/data_processor.py` | PDF/TXT reading, article extraction, and text cleaning |
| `src/llm_processor.py` | Podcast prompt, length settings, and script generation |
| `src/tts_generator.py` | Text chunking and speech generation |
| `src/main.py` | Pipeline coordination and Gradio interface |
| `requirements.txt` | Python dependencies |
| `outputs/` | Generated scripts and audio files |

## Requirements

- Python 3.11, the version used during development.
- Git and an internet connection.
- An OpenAI API key with access to both `gpt-4o-mini` and `tts-1`, plus available API credit or billing.

The current TTS implementation does **not** require FFmpeg.

## Setup

Run the following commands in a terminal. On Windows, use Anaconda Prompt for the Conda commands.

### 1. Clone the repository

```bash
git clone https://github.com/Armin-Seyfi/podcast-repo.git
cd podcast-repo
```

Open this folder in VS Code if you want to inspect or edit the code.

### 2. Activate a Python environment

If you already have the Bootcamp environment:

```bash
conda activate bootcamp-env
```

Otherwise, create a dedicated environment:

```bash
conda create -n podcast-studio python=3.11
conda activate podcast-studio
```

In VS Code, select the same environment through **Python: Select Interpreter** in the Command Palette.

### 3. Install dependencies

From the repository root:

```bash
python -m pip install -r requirements.txt
```

Dependencies include OpenAI, python-dotenv, pypdf, Requests, Trafilatura, and Gradio.

### 4. Configure your API key

Create a file named `.env` in the repository root, next to `requirements.txt`:

```dotenv
OPENAI_API_KEY=your_actual_api_key
```

Replace the placeholder with your own key. Do not put the key in Python files or commit `.env` to GitHub. Each teammate configures their own local `.env` file.

The application loads this file before importing the TTS module. If `OPENAI_API_KEY` is already set in your shell, that existing environment value takes precedence.

## Run the app

From the repository root, with your environment active:

```bash
python src/main.py
```

Open the local URL printed in the terminal, usually:

```text
http://127.0.0.1:7860
```

Use this launch command rather than `python -m src.main`; the current application uses imports relative to the `src` directory.

1. Upload a PDF/TXT file **or** enter an article URL. Use only one source at a time.
2. Select a podcast length.
3. Click **Submit** and wait for script and audio generation.
4. Review the script, listen to the audio, and download the podcast.

| Length | Target duration | Approximate script length |
|---|---|---|
| Short | 3 minutes | 450 words |
| Medium | 15 minutes | 2,250 words |
| Long | 30 minutes | 4,500 words |

These are targets, not guaranteed durations. Medium and long episodes use multiple LLM requests, and longer scripts require more TTS requests.

Opening the app does not send a generation request. **Submitting a valid source uses paid OpenAI APIs.** Start with a short document and the Short option.

Stop the server with **Ctrl + C**. Restart it after changing Python code. The app starts locally with `share=False`.

## Output files

Each request uses a unique identifier:

- `outputs/recap_<id>.txt`: generated podcast script.
- `outputs/recap_<id>.mp3`: generated podcast audio.

The script is saved before audio generation, so it remains available if TTS fails. The interface does not yet provide a retry-only-audio button; resubmitting regenerates the script and may incur additional costs. Outputs are not automatically deleted.

## Troubleshooting

| Problem | What to check |
|---|---|
| `ModuleNotFoundError` | Activate the intended environment and reinstall with `python -m pip install -r requirements.txt`. |
| Missing API key | Check the root `.env` file and the exact name `OPENAI_API_KEY`, then restart the app. |
| API 403 / model access error | Check that the project associated with your key allows the requested model. |
| API 429 | Inspect the terminal message for rate-limit or quota details; check API billing and usage. |
| Website HTTP 403 or 404 | The site rejected the request or did not return the requested page. Check the URL or upload an accessible PDF/TXT copy. |
| No readable PDF text | Scanned pages require OCR. This version also rejects encrypted PDFs and pages with no extracted text, including blank pages. |
| TTS input exceeds 4,096 characters | A very long sentence can exceed the current splitter's limit; the splitter needs a hard-length fallback for that case. |
| Audio generation failed after script generation | Inspect the full terminal error and find the saved script in `outputs/` before retrying. |

## Current limitations

- URL extraction supports accessible HTML pages, not direct PDF links. It does not execute JavaScript, sign in, or bypass access restrictions.
- Successful extraction does not prove completeness. Headers, tables, citation markers, and broken text can remain; compare important content with the source.
- There is no OCR or automatic handling of arbitrarily large inputs. Long source documents can increase cost or exceed model limits.
- The LLM can omit or misinterpret information. Review facts, numbers, and coverage before sharing a recap.
- The current TTS module joins MP3 chunk bytes directly. Playback duration, seeking, and voice continuity across chunks should be checked, especially for long episodes.
- This is a classroom prototype running locally, without authentication or production deployment controls. Source text is sent to OpenAI for generation; use material you are permitted to process and disclose that the audio is AI-generated.

## Team workflow

Work on a personal branch, commit only intended files, and open a Pull Request into `main` for review. Keep API keys, private source documents, and generated test outputs out of commits.

After the team merges changes, commit or stash local edits before updating:

```bash
git switch main
git pull --ff-only origin main
python -m pip install -r requirements.txt
```

Switch back to your working branch and merge the updated `main` before continuing development.
