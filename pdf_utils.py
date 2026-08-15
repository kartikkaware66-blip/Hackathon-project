"""PDF text extraction and chunking (text-based PDFs only, no OCR)."""

from pypdf import PdfReader


def extract_pdf_text(file_path):
    """Return a list like [{"page": 1, "text": "..."}, ...]."""
    pages = []
    reader = PdfReader(file_path)
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = " ".join(text.split())  # clean extra whitespace
        pages.append({"page": index, "text": text})
    return pages


def count_words(pages):
    return sum(len(p["text"].split()) for p in pages)


def guess_title(pages, fallback):
    """Very simple title guess: first reasonable line of page 1."""
    if not pages or not pages[0]["text"]:
        return fallback
    words = pages[0]["text"].split()
    title = " ".join(words[:12]).strip()
    return title if len(title) > 5 else fallback


def create_chunks(page_text, chunk_size=1000):
    """Split each page's text into chunks, keeping the page number."""
    chunks = []
    for page in page_text:
        text = page["text"]
        if not text:
            continue
        start = 0
        while start < len(text):
            piece = text[start:start + chunk_size].strip()
            if len(piece) > 40:  # skip tiny leftovers
                chunks.append({"page": page["page"], "text": piece})
            start += chunk_size
    return chunks
