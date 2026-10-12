from pathlib import Path
import re
import unicodedata

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

