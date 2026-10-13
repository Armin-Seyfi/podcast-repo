from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

import requests
import trafilatura

from pypdf import PdfReader


def read_transcript(file_path: str) -> str:
    """Extract text from a UTF-8 TXT file or a text-based PDF."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    extension = path.suffix.lower()

    if extension == ".txt":
        text = path.read_text(encoding="utf-8-sig")

    elif extension == ".pdf":
        reader = PdfReader(path)

        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")

        pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""

            if not page_text.strip():
                raise ValueError(
                    f"No readable text found on page {page_number}. "
                    "The page may be blank or require OCR."
                )

            pages.append(page_text)

        text = "\n\n".join(pages)

    else:
        raise ValueError("Unsupported file type. Please use PDF or TXT.")

    if not text.strip():
        raise ValueError("The file contains no readable text.")

    return text


def clean_text(text: str) -> str:
    """Normalize Unicode, expand ligatures, and clean whitespace."""
    # Normalize equivalent Unicode representations.
    text = unicodedata.normalize("NFC", text)

    # Expand common typographic ligatures.
    ligatures = {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\ufb05": "st",
        "\ufb06": "st",
    }

    for original, replacement in ligatures.items():
        text = text.replace(original, replacement)

    # Standardize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse spaces and tabs within each line.
    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.split("\n")
    ]
    text = "\n".join(lines)

    # Keep one blank line between paragraphs.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def process_file(file_path: str) -> str:
    """Read a supported file and return cleaned text."""
    raw_text = read_transcript(file_path)
    cleaned_text = clean_text(raw_text)

    if not cleaned_text:
        raise ValueError("No text remains after cleaning.")

    return cleaned_text

def process_url(url: str) -> str:
    """Download a public HTML page and return cleaned article text."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Please provide a website URL.")

    url = url.strip()
    parsed_url = urlsplit(url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise ValueError("Please provide a valid HTTP or HTTPS URL.")

    try:
        response = requests.get(
            url,
            timeout=(5, 20),
            headers={"User-Agent": "PodcastStudio/0.1"},
        )
        response.raise_for_status()

    except requests.exceptions.Timeout as error:
        raise RuntimeError("The website took too long to respond.") from error

    
    except requests.exceptions.HTTPError as error:
        status = error.response.status_code
        raise RuntimeError(
            f"The website returned HTTP {status}. "
            "The page could not be downloaded."
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            "Could not connect to the website. "
            "Check the URL and network connection."
        ) from error

    content_type = response.headers.get("Content-Type", "").lower()

    if not any(
        html_type in content_type
        for html_type in ("text/html", "application/xhtml+xml")
    ):
        raise ValueError(
            "The URL must point to an HTML page, not a PDF or another file."
        )

    extracted_text = trafilatura.extract(
        response.content,
        url=response.url,
        output_format="txt",
        include_comments=False,
        include_tables=True,
    )

    if not extracted_text or not extracted_text.strip():
        raise ValueError(
            "No article text could be extracted. "
            "The page may require JavaScript, login, or a subscription."
        )

    cleaned_text = clean_text(extracted_text)

    if not cleaned_text:
        raise ValueError("No text remains after cleaning.")

    return cleaned_text

