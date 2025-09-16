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

# ---------- CONFIG ----------
DB_PATH = "data/transcriptions.db"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Load Whisper model once
model = whisper.load_model("base")

# ---------- SAMPLE LEXICONS ----------
# Expand these lists over time, or connect to external CSVs
ECONOMIC_TERMS = [
    "inflación", "pobreza", "desempleo", "reservas", "dólar", "peso",
    "PIB", "déficit", "superávit", "tarifas", "subsidios", "impuestos"
]
ARG_EXPRESSIONS = [
    "laburo", "guita", "quilombo", "bondi", "mango", "fiaca",
    "che", "posta", "macana", "changas"
]

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

# ---------- FASTAPI ----------
app = FastAPI(title="Argentina Economy Analyzer API",
              description="Offline transcription + glossary pipeline",
              version="0.2")

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

    # Update glossaries
    update_glossaries(transcript_text)

    return JSONResponse(content={
        "filename": file.filename,
        "transcript_preview": transcript_text[:200] + ("..." if len(transcript_text) > 200 else ""),
        "message": "File processed, saved, and glossaries updated"
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

# ---------- MAIN ----------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
