# 🇦🇷 Argentina Economy Transcription API

A Spanish audio transcription and economic term analysis system using OpenAI Whisper and FastAPI. Built for offline processing of Argentine economic content with intelligent glossary building.

## ✨ Features

- **🎤 Audio Transcription**: Spanish MP3 files transcribed using Whisper
- **📊 Economic Term Detection**: Automatically identifies economic indicators (inflación, PIB, dólar, etc.)
- **🗣️ Argentine Expression Recognition**: Detects colloquial Argentine terms (laburo, guita, che, etc.)
- **🔍 Candidate Discovery**: Finds and catalogs unknown terms with context
- **🎯 Manual Curation**: Promote candidate terms to specific glossaries
- **🌐 Web Interface**: User-friendly Streamlit dashboard for complete workflow
- **💾 Offline Processing**: No external APIs required after setup

## 🚀 Quick Start

### Setup

```bash
# Clone repository
git clone https://github.com/betolauda/transcrip-app.git
cd transcrip-app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Application

```bash
# Terminal 1: Start FastAPI backend
python3 main.py

# Terminal 2: Start Streamlit frontend
streamlit run app.py
```

- **Web Interface**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **API Endpoint**: http://localhost:8000

## 📖 Usage

### Web Interface
1. Open http://localhost:8501
2. Upload MP3 files through the interface
3. Review detected economic terms and Argentine expressions
4. Promote candidate terms to appropriate glossaries

### API Endpoints

- `POST /upload` - Upload and process MP3 files
- `GET /glossaries` - Retrieve economic and Argentine term glossaries
- `GET /candidates` - Get discovered candidate terms with context
- `POST /promote` - Move candidate terms to specific glossaries

## 🏗️ Architecture

- **Backend**: FastAPI with Whisper integration
- **Frontend**: Streamlit web interface
- **Database**: SQLite for transcript and glossary storage
- **Processing**: Intelligent term detection with context analysis
- **Language**: Spanish audio processing optimized for Argentine dialect

## 🗄️ Database Schema

- `transcriptions` - Audio file transcripts with timestamps
- `economic_glossary` - Detected economic terms and categories
- `argentine_dictionary` - Argentine colloquial expressions
- `candidate_terms` - Unknown terms awaiting manual review

## 📁 Project Structure

```
transcrip-app/
├── main.py              # FastAPI application
├── app.py               # Streamlit web interface
├── requirements.txt     # Python dependencies
├── CLAUDE.md           # Development guide
├── data/               # SQLite database (auto-created)
├── uploads/            # Audio file storage (auto-created)
└── README.md           # This file
```

## 🔧 Configuration

- **Whisper Model**: "base" (can be changed to "small", "medium", "large")
- **Language**: Spanish ("es")
- **Database**: SQLite at `data/transcriptions.db`
- **Upload Directory**: `uploads/`
- **Supported Formats**: MP3 only

## 🛠️ Development

Built with Python 3.12+ and designed for offline operation. The system automatically:

1. Transcribes Spanish audio using Whisper
2. Detects known economic terms and Argentine expressions
3. Identifies unknown terms as candidates with context
4. Provides web interface for manual curation and review

## 📜 License

Open source side project for Argentine economic content analysis.

---

*🤖 Enhanced with Claude Code for intelligent Argentine economic content processing*