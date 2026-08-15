# 📚 ResearchMate AI — AI Research Assistant (AIML-06 Hackathon)

A simple web-based AI research assistant for students. Upload a research paper PDF,
get an AI summary, ask grounded questions with page citations, search the paper,
and compare two papers.

Built with **Python + Flask + SQLite + HTML/CSS/Vanilla JS**. No React, no vector DB.

---

## ✨ Features

- Upload a text-based PDF research paper (max 10 MB)
- Automatic text extraction + chunking (page numbers preserved)
- AI summary: Research Topic, Problem, Objective, Methodology, Key Findings, Limitations, Future Scope
- Grounded AI chat — answers use **only** retrieved paper content
- Page-level "Grounded Sources" for every answer
- TF-IDF similarity search inside the paper
- Paper library with open/delete
- Basic comparison of two papers

### How the grounded answers work (Lightweight RAG using TF-IDF)

```
Question -> TF-IDF search over stored chunks -> top 3-5 chunks
         -> only those chunks sent to Gemini -> grounded answer + page numbers
```

If nothing relevant is retrieved, the app answers
*"I could not find this information in the uploaded paper."* — it never guesses.
Greetings like "hi" / "hello" are answered directly without retrieval.

---

## 🛠 Technology Stack

| Layer     | Tech                                    |
|-----------|-----------------------------------------|
| Backend   | Python 3, Flask                         |
| Database  | SQLite (built-in `sqlite3`)             |
| PDF       | pypdf                                   |
| AI        | Gemini API (`google-generativeai`)      |
| Search    | scikit-learn TF-IDF + cosine similarity |
| Frontend  | HTML5, CSS3, Vanilla JS, Jinja2         |

---

## 📁 Project Structure

```
researchmate_ai/
├── app.py            # Flask routes and APIs
├── database.py       # SQLite tables and queries
├── pdf_utils.py      # PDF text extraction + chunking
├── ai_service.py     # TF-IDF retrieval + Gemini prompts
├── requirements.txt
├── .env              # your Gemini key (create from .env.example)
├── run.bat           # one-click run on Windows
├── build_exe.bat     # build the .exe on Windows
├── README.md
├── researchmate.db   # created automatically
├── uploads/          # uploaded PDFs
├── templates/
│   ├── base.html
│   ├── index.html    # home + library
│   └── paper.html
└── static/
    ├── style.css
    └── script.js
```

---

## 🚀 Installation

```bash
python -m venv venv
```

Activate it:

- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

Install dependencies:

```bash
pip install -r requirements.txt
```

### Configure the Gemini API key

1. Get a free key at https://aistudio.google.com/apikey
2. Copy `.env.example` to `.env`
3. Put your key inside:

```
GEMINI_API_KEY=your_api_key_here
```

The key stays on the server — the browser never sees it.

### Run

```bash
python app.py
```

Open http://127.0.0.1:5000 (it opens automatically).

On Windows you can simply double-click **run.bat**.

---

## 💻 Building the .exe (Windows)

Double-click **build_exe.bat**. It installs PyInstaller and produces:

```
dist\ResearchMateAI.exe
```

Copy your `.env` file next to the `.exe`, then double-click it — the browser opens
automatically at http://127.0.0.1:5000. The `uploads/` folder and `researchmate.db`
are created beside the `.exe`.

> Note: a Windows `.exe` must be built on a Windows machine.

---

## 🎬 Demo Flow

1. Open http://127.0.0.1:5000
2. Upload a research paper PDF
3. Click **Generate AI Summary**
4. Ask: *"What is the main contribution of this paper?"* → answer + Grounded Sources (Page 3, Page 5)
5. Ask something not in the paper → *"I could not find this information in the uploaded paper."*
6. Search *"attention"* → relevant pages with similarity scores
7. Upload a second paper → go to **Library** → compare two papers

---

## 🔮 Future Improvements

- Sentence-level embeddings instead of TF-IDF
- Export summaries as PDF
- Highlight the exact matched sentence in the paper
- Support for scanned PDFs (OCR)
