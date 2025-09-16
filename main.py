from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import whisper
import sqlite3
import os
import shutil
import uvicorn
from datetime import datetime
from pathlib import Path
import re
import unicodedata
import string

# ---------- CONFIG ----------
DB_PATH = "data/transcriptions.db"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Load Whisper model once (you can switch "base" → "small" / "medium")
model = whisper.load_model("base")

# ---------- SAMPLE LEXICONS ----------
ECONOMIC_TERMS = [
    "inflación", "pobreza", "desempleo", "reservas", "dólar", "peso",
    "PIB", "déficit", "superávit", "tarifas", "subsidios", "impuestos"
]
ARG_EXPRESSIONS = [
    "laburo", "guita", "quilombo", "bondi", "mango", "fiaca",
    "che", "posta", "macana", "changas"
]

SPANISH_STOPWORDS = {
    "el","la","los","las","de","del","y","o","que","en","es","un","una","por",
    "con","al","se","lo","su","para","a","como","más","menos","ya","pero","sin",
    "sobre","esto","esta","ese","esa","esas","estos","esas","sí","no"
}

# ---------- DB SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Transcriptions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            transcript TEXT,
            created_at TEXT
        )
    """)
    # Economic glossary
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS economic_glossary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT UNIQUE,
            category TEXT,
            first_seen TEXT
        )
    """)
    # Argentine dictionary
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS argentine_dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expression TEXT UNIQUE,
            first_seen TEXT
        )
    """)
    # Candidate terms
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidate_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT UNIQUE,
            first_seen TEXT,
            context_snippet TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- HELPERS ----------
def update_glossaries(transcript: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    # Economic terms
    for term in ECONOMIC_TERMS:
        if re.search(rf"\b{term}\b", transcript, re.IGNORECASE):
            try:
                cursor.execute("""
                    INSERT INTO economic_glossary (term, category, first_seen)
                    VALUES (?, ?, ?)
                """, (term, "economic", now))
            except sqlite3.IntegrityError:
                pass  # already exists

    # Argentine expressions
    for exp in ARG_EXPRESSIONS:
        if re.search(rf"\b{exp}\b", transcript, re.IGNORECASE):
            try:
                cursor.execute("""
                    INSERT INTO argentine_dictionary (expression, first_seen)
                    VALUES (?, ?)
                """, (exp, now))
            except sqlite3.IntegrityError:
                pass  # already exists

    conn.commit()
    conn.close()


def normalize_token(token: str) -> str:
    token = token.lower().strip(string.punctuation)
    token = "".join(
        c for c in unicodedata.normalize("NFD", token)
        if unicodedata.category(c) != "Mn"
    )  # remove accents
    return token


def detect_new_terms(transcript: str):
    words = [normalize_token(w) for w in transcript.split()]
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for i, w in enumerate(words):
        if not w or w in SPANISH_STOPWORDS or len(w) < 3:
            continue

        # Already in glossaries?
        cursor.execute("SELECT 1 FROM economic_glossary WHERE term=?", (w,))
        if cursor.fetchone():
            continue
        cursor.execute("SELECT 1 FROM argentine_dictionary WHERE expression=?", (w,))
        if cursor.fetchone():
            continue
        cursor.execute("SELECT 1 FROM candidate_terms WHERE term=?", (w,))
        if cursor.fetchone():
            continue

        # Grab context window
        start = max(0, i-3)
        end = min(len(words), i+4)
        context = " ".join(words[start:end])

        try:
            cursor.execute("""
                INSERT INTO candidate_terms (term, first_seen, context_snippet)
                VALUES (?, ?, ?)
            """, (w, now, context))
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

# ---------- FASTAPI ----------
app = FastAPI(
    title="Argentina Economy Analyzer API",
    description="Offline transcription + glossary updater + candidate detection",
    version="0.3"
)

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    if not file.filename.endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Only .mp3 files are supported")

    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = model.transcribe(str(save_path), language="es")
        transcript_text = result["text"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    # Store transcription
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transcriptions (filename, transcript, created_at)
        VALUES (?, ?, ?)
    """, (file.filename, transcript_text, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    # Update glossaries & detect candidates
    update_glossaries(transcript_text)
    detect_new_terms(transcript_text)

    return JSONResponse(content={
        "filename": file.filename,
        "transcript_preview": transcript_text[:200] + ("..." if len(transcript_text) > 200 else ""),
        "message": "File processed, saved, glossaries updated, candidates detected"
    })


@app.get("/glossaries")
async def get_glossaries():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT term, category, first_seen FROM economic_glossary")
    econ = cursor.fetchall()
    cursor.execute("SELECT expression, first_seen FROM argentine_dictionary")
    arg = cursor.fetchall()
    conn.close()
    return {
        "economic_glossary": econ,
        "argentine_dictionary": arg
    }


@app.get("/candidates")
async def get_candidates():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT term, first_seen, context_snippet FROM candidate_terms")
    rows = cursor.fetchall()
    conn.close()
    return {"candidates": rows}


# ---------- MAIN ----------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
