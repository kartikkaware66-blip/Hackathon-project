"""Gemini AI + TF-IDF retrieval. The browser never talks to Gemini directly."""

import os

from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_NAME = "gemini-3.7-flash"

GREETINGS = {
    "hi", "hii", "hello", "hey", "yo", "good morning", "good evening",
    "good afternoon", "who are you", "what are you", "thanks", "thank you",
}


def is_greeting(text):
    return text.strip().lower().strip("!?.,") in GREETINGS


# ---------------------------------------------------------------- retrieval
def search_chunks(query, chunks, top_k=5, threshold=0.05):
    """Simple TF-IDF + cosine similarity search over the paper chunks."""
    if not chunks or not query.strip():
        return []
    texts = [c["text"] for c in chunks]
    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(texts + [query])
    except ValueError:
        return []
    scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    results = []
    for chunk, score in ranked[:top_k]:
        if score >= threshold:
            results.append({"page": chunk["page"], "text": chunk["text"], "score": round(float(score), 2)})
    return results


# ---------------------------------------------------------------- gemini
def _call_gemini(prompt):
    """Send a prompt to Gemini and return plain text. Raises on failure."""
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key is missing. Add GEMINI_API_KEY to your .env file.")
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    text = (getattr(response, "text", "") or "").strip()
    if not text:
        raise RuntimeError("The AI returned an empty response.")
    return text


def generate_summary(paper_text):
    prompt = (
        "You are an academic research assistant.\n"
        "Summarize the following research paper.\n"
        "Use ONLY the supplied paper text. Do not invent information.\n"
        "If a section is not available, say: 'Not clearly stated in the paper.'\n"
        "Return the result using exactly these headings:\n"
        "Research Topic:\nProblem Statement:\nObjective:\nMethodology:\n"
        "Key Findings:\nLimitations:\nFuture Scope:\n\n"
        f"Paper text:\n{paper_text[:20000]}"
    )
    return _call_gemini(prompt)


def answer_question(question, context):
    prompt = (
        "You are a research assistant.\n"
        "Answer the user's question using ONLY the provided research paper excerpts.\n"
        "Do not use outside knowledge. Do not invent information.\n"
        "If the answer cannot be found in the provided excerpts, say:\n"
        "'I could not find this information in the uploaded paper.'\n\n"
        f"Question:\n{question}\n\n"
        f"Research paper excerpts:\n{context}\n\n"
        "Provide a concise academic answer that a student can understand. "
        "At the end, mention the relevant page numbers."
    )
    return _call_gemini(prompt)


def compare_papers(paper1, paper2):
    prompt = (
        "Compare the following two research papers.\n"
        "Use only the supplied information. Do not invent information.\n"
        "Compare:\n1. Research Problem\n2. Methodology\n3. Main Findings\n"
        "4. Limitations\n5. Similarities\n6. Differences\n\n"
        f"Paper 1:\n{paper1}\n\nPaper 2:\n{paper2}"
    )
    return _call_gemini(prompt)


def build_context(results):
    """Turn retrieved chunks into a numbered SOURCE block for the prompt."""
    parts = []
    for i, r in enumerate(results, start=1):
        parts.append(f'SOURCE {i}\nPage: {r["page"]}\n"{r["text"]}"')
    return "\n\n".join(parts)
