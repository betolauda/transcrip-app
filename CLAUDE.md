# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Spanish audio transcription API** that uses OpenAI's Whisper model for offline speech-to-text processing. The application is built with FastAPI and focuses on transcribing Spanish audio files (specifically MP3) and storing transcripts in a local SQLite database.

## Architecture

- **Backend Framework**: FastAPI with uvicorn server
- **Speech Recognition**: OpenAI Whisper (base model) for Spanish transcription
- **Database**: SQLite (`data/transcriptions.db`)
- **File Storage**: Local uploads directory for audio files
- **Language**: Spanish audio processing (`language="es"`)

### Core Components

- `main.py`: FastAPI application with transcription endpoint
- `/upload` endpoint: Accepts MP3 files, transcribes them, stores results
- SQLite database with transcriptions table (id, filename, transcript, created_at)

## Development Commands

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start FastAPI backend
python3 main.py

# Start Streamlit frontend (separate terminal)
streamlit run app.py
```

- **API**: `http://localhost:8000`
- **Web Interface**: `http://localhost:8501`
- **API Documentation**: `http://localhost:8000/docs`

### Dependencies

Core dependencies (see `requirements.txt`):
- `fastapi` - Web framework for the API
- `uvicorn` - ASGI server for FastAPI
- `whisper-openai` - OpenAI Whisper for transcription
- `streamlit` - Web interface framework
- `requests` - HTTP client for frontend-backend communication
- `python-multipart` - File upload support

### Database Setup

The database is automatically initialized on startup with the following schema:

```sql
CREATE TABLE transcriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    transcript TEXT,
    created_at TEXT
);
```

## API Usage

### POST /upload
- Accepts MP3 files only
- Returns JSON with filename, truncated transcript preview, and success message
- Stores full transcript in database
- Creates `uploads/` and `data/` directories if they don't exist

## File Structure Context

The project appears to be part of a larger Argentine economic monitoring system as documented in `offline_transcription.md`. This current implementation serves as the core transcription service that would be integrated into the broader pipeline described in that document.

## Important Notes

- Only MP3 files are supported for upload
- Whisper model loads once at startup (base model for balance of speed/accuracy)
- Spanish language is hardcoded (`language="es"`)
- Database path: `data/transcriptions.db`
- Upload directory: `uploads/`
- Server runs on all interfaces (0.0.0.0) port 8000 by default