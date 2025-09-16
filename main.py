from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import whisper
import sqlite3
import os
import shutil
import uvicorn
from datetime import datetime
from pathlib import Path

# ---------- CONFIG ----------
DB_PATH = "data/transcriptions.db"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Load Whisper model (you can swap for "small", "medium", etc.)
# This loads once at startup
model = whisper.load_model("base")

# ---------- DB SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            transcript TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- FASTAPI ----------
app = FastAPI(title="Argentina Economy Transcriber API",
              description="Offline transcription & analysis workflow",
              version="0.1")

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    # Check file extension
    if not file.filename.endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Only .mp3 files are supported")

    # Save file locally
    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run Whisper transcription
    try:
        result = model.transcribe(str(save_path), language="es")
        transcript_text = result["text"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    # Store in DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transcriptions (filename, transcript, created_at)
        VALUES (?, ?, ?)
    """, (file.filename, transcript_text, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    return JSONResponse(content={
        "filename": file.filename,
        "transcript": transcript_text[:200] + ("..." if len(transcript_text) > 200 else ""),
        "message": "File processed and saved successfully"
    })

# For local dev
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
