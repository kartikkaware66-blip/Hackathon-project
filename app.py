import os
import sys
import webbrowser
from threading import Timer

from flask import Flask, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

import ai_service
import pdf_utils

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# When packaged as an .exe, keep uploads next to the executable.
DATA_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else BASE_DIR
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
MAX_SIZE = 10 * 1024 * 1024  # 10 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_SIZE

papers = {}
chunks_store = {}
summaries_store = {}
next_paper_id = 1


# ------------------------------------------------------------------ pages
@app.route("/")
def home():
    stats = {
        "papers": len(papers),
        "pages": sum(p["pages"] for p in papers.values()),
        "chunks": sum(len(c) for c in chunks_store.values()),
    }

    return render_template(
        "index.html",
        papers=list(papers.values())[:4],
        stats=stats,
    )


@app.route("/library")
def library():
    stats = {
        "papers": len(papers),
        "pages": sum(p["pages"] for p in papers.values()),
        "chunks": sum(len(c) for c in chunks_store.values()),
    }

    return render_template(
        "index.html",
        papers=list(papers.values()),
        stats=stats,
        library_view=True,
    )


@app.route("/paper/<int:paper_id>")
def paper_page(paper_id):
    paper = papers.get(paper_id)

    if not paper:
        return redirect(url_for("library"))

    return render_template(
        "paper.html",
        paper=paper,
        summary=summaries_store.get(paper_id),
        papers=list(papers.values()),
    )


# ------------------------------------------------------------------ upload
@app.route("/upload", methods=["POST"])
def upload():
    global next_paper_id

    file = request.files.get("pdf_file")

    if not file or file.filename == "":
        return render_error("Please choose a PDF file to upload.")

    if not file.filename.lower().endswith(".pdf"):
        return render_error("Only PDF files are allowed.")

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    if os.path.getsize(path) > MAX_SIZE:
        os.remove(path)
        return render_error("File is too large. Maximum size is 10 MB.")

    try:
        pages = pdf_utils.extract_pdf_text(path)
    except Exception:
        os.remove(path)
        return render_error("This file could not be read as a valid PDF.")

    if not any(p["text"] for p in pages):
        os.remove(path)
        return render_error(
            "This PDF does not contain readable text. Please upload a text-based research paper."
        )

    title = pdf_utils.guess_title(
        pages,
        os.path.splitext(filename)[0],
    )

    paper_id = next_paper_id
    next_paper_id += 1

    paper = {
        "id": paper_id,
        "title": title,
        "filename": filename,
        "pages": len(pages),
        "word_count": pdf_utils.count_words(pages),
    }

    papers[paper_id] = paper
    chunks_store[paper_id] = pdf_utils.create_chunks(pages)
    summaries_store[paper_id] = None

    return redirect(url_for("paper_page", paper_id=paper_id))


def render_error(message):
    stats = {
        "papers": len(papers),
        "pages": sum(p["pages"] for p in papers.values()),
        "chunks": sum(len(c) for c in chunks_store.values()),
    }

    return render_template(
        "index.html",
        papers=list(papers.values())[:4],
        stats=stats,
        error=message,
    )


# ------------------------------------------------------------------ api
@app.route("/api/summarize/<int:paper_id>", methods=["POST"])
def api_summarize(paper_id):
    paper = papers.get(paper_id)

    if not paper:
        return jsonify({"success": False, "error": "Paper not found."})

    chunks = chunks_store.get(paper_id, [])

    if not chunks:
        return jsonify({"success": False, "error": "No readable content in this paper."})

    text = "\n".join(c["text"] for c in chunks)

    try:
        summary = ai_service.generate_summary(text)
    except Exception as e:
        return jsonify({"success": False, "error": friendly(e)})

    summaries_store[paper_id] = summary

    return jsonify({"success": True, "summary": summary})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}

    question = (data.get("question") or "").strip()
    paper_id = data.get("paper_id")

    if not question:
        return jsonify({"success": False, "error": "Please type a question."})

    # Greetings are answered directly, no retrieval.
    if ai_service.is_greeting(question):
        return jsonify({
            "success": True,
            "answer": "Hello! I am ResearchMate AI. Ask me a question about your uploaded research paper.",
            "sources": [],
        })

    chunks = chunks_store.get(paper_id, [])

    if not chunks:
        return jsonify({"success": False, "error": "This paper has no indexed content."})

    results = ai_service.search_chunks(question, chunks, top_k=4)

    if not results:
        return jsonify({
            "success": True,
            "answer": "I could not find this information in the uploaded paper.",
            "sources": [],
        })

    try:
        answer = ai_service.answer_question(
            question,
            ai_service.build_context(results),
        )
    except Exception as e:
        return jsonify({"success": False, "error": friendly(e)})

    sources = [
        {"page": r["page"], "text": r["text"][:280]}
        for r in results
    ]

    return jsonify({
        "success": True,
        "answer": answer,
        "sources": sources,
    })


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(silent=True) or {}

    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({
            "success": False,
            "error": "Please enter a search term.",
        })

    chunks = chunks_store.get(
        data.get("paper_id"),
        [],
    )

    results = ai_service.search_chunks(
        query,
        chunks,
        top_k=5,
    )

    return jsonify({
        "success": True,
        "results": results,
    })


@app.route("/api/delete/<int:paper_id>", methods=["POST"])
def api_delete(paper_id):
    paper = papers.get(paper_id)

    if paper:
        path = os.path.join(
            UPLOAD_FOLDER,
            paper["filename"],
        )

        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

        papers.pop(paper_id, None)
        chunks_store.pop(paper_id, None)
        summaries_store.pop(paper_id, None)

    return jsonify({"success": True})


@app.route("/api/compare", methods=["POST"])
def api_compare():
    data = request.get_json(silent=True) or {}

    ids = data.get("paper_ids") or []

    if len(ids) != 2:
        return jsonify({
            "success": False,
            "error": "Please select exactly two papers.",
        })

    info = []

    for pid in ids:
        paper = papers.get(pid)

        if not paper:
            return jsonify({
                "success": False,
                "error": "One of the papers was not found.",
            })

        summary = summaries_store.get(pid)

        if not summary:
            chunks = chunks_store.get(pid, [])
            summary = " ".join(
                c["text"] for c in chunks
            )[:6000]

        info.append(
            f'Title: {paper["title"]}\nPages: {paper["pages"]}\n'
            f'Words: {paper["word_count"]}\nContent:\n{summary}'
        )

    try:
        result = ai_service.compare_papers(
            info[0],
            info[1],
        )
    except Exception as e:
        return jsonify({
            "success": False,
            "error": friendly(e),
        })

    return jsonify({
        "success": True,
        "comparison": result,
    })


@app.errorhandler(413)
def too_large(_e):
    return render_error(
        "File is too large. Maximum size is 10 MB."
    )


def friendly(error):
    """Never leak stack traces to the browser."""

    message = str(error)

    if "API key" in message:
        return "Gemini API key is missing. Add GEMINI_API_KEY in the .env file."

    return "Unable to generate the answer. Please try again."


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    Timer(1.2, open_browser).start()
    app.run(debug=False, port=5000)