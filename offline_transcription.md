# Offline MVP: Transcription & Indicators

This document contains a detailed implementation plan (offline/local) to build the pipeline you requested and a runnable skeleton for a FastAPI backend + Streamlit control panel MVP. It assumes you will run everything on a single machine (desktop/laptop / small server) and use local, open-source tools.

---

## Table of contents

1. Overview & goals
2. Project layout and file structure
3. Global infra & prerequisites
4. Step-by-step implementation plan (tasks, estimated effort, infra)
   - Local transcription (Whisper/whisper.cpp / faster-whisper)
   - Economic term detection (spaCy + rule-based + embeddings)
   - Economic glossary (DB + vector store + review queue)
   - Argentine colloquial detection + dictionary
   - Dashboard & Streamlit control panel
   - Scraper for official indicators (datos.gob.ar / BCRA)
   - Orchestration, scheduling, monitoring, backups
5. Database schema (SQLite/Postgres) & vector index layout
6. Minimal security & privacy considerations
7. FastAPI + Streamlit skeleton (files + code)
8. How to run & quick test
9. Next steps & scaling notes

---

## 1. Overview & goals

Goal: an offline, local pipeline that ingests Spanish MP3 audio, transcribes it, extracts economic terms (macro/micro), detects Argentine colloquial expressions, maintains two living glossaries (economic and Argentine expressions), scrapes official Argentine economic indicators, and exposes a simple control panel/dashboard (Streamlit) plus a FastAPI backend for ingestion and light orchestration.

Constraints: offline-first, open-source, compatible with LM Studio and local LLMs; minimal external dependencies; ability to run on a mid-range laptop (8–16 GB RAM) — GPU optional but helpful.

Assumptions: you are comfortable running Python, installing packages, and running local services. We'll use SQLite for MVP; upgrade to Postgres when scaling.

---

## 2. Project layout and file structure

```
arg-econ-monitor/                         # repo root
├─ backend/                                # FastAPI app + worker
│  ├─ app/
│  │  ├─ main.py                           # FastAPI app
│  │  ├─ api.py                            # endpoints
│  │  ├─ models.py                         # SQLAlchemy models
│  │  ├─ db.py                             # DB engine + session
│  │  ├─ processing.py                     # transcription pipeline wrapper
│  │  └─ scraper.py                        # scripts to fetch indicators
│  └─ worker.py                            # CLI worker to process files
├─ streamlit_app/
│  ├─ app.py                              # Streamlit control panel & dashboard
│  └─ utils.py                            # small helpers
├─ scripts/
│  ├─ ingest_local_audio.py                # simple uploader + call API
│  └─ fetch_indicators.py                  # run scraper standalone
├─ data/
│  ├─ audio_raw/                           # audio files
│  ├─ transcripts/                         # json transcripts
│  └─ backups/
├─ notebooks/                              # optional exploration
├─ requirements.txt
├─ README.md
└─ infra_notes.md
```

---

## 3. Global infra & prerequisites

Recommended packages & tools (MVP):

- Python 3.10+ (venv)
- SQLite (built-in) or Postgres for production
- `faster-whisper` or `whisperx` / or `whisper.cpp` (whisper.cpp is native binary; faster-whisper is pip-friendly)
- `spaCy` (Spanish model `es_core_news_lg`) + `spacy-transformers` optional
- `sentence-transformers` (e.g., `paraphrase-multilingual-MiniLM-L12-v2`)
- `faiss-cpu` (vector index) or `faiss-gpu` if you have GPU
- `SQLAlchemy` + `alembic` (optional)
- `FastAPI` + `uvicorn`
- `Streamlit` for UI
- `requests`, `beautifulsoup4` (for scrapers)
- `librosa`, `pydub` (audio preprocessing) and `webrtcvad` or `silero-vad` for VAD

Estimated disk space: audio (variable), plus space for models (SBERT ~200–300MB; Spanish spaCy model ~700MB; Whisper models vary 50MB–2GB depending on size).

---

## 4. Step-by-step implementation plan

### 0) Common tasks (setup)

**Tasks**
- Create the repo and virtualenv.
- Install Python packages from `requirements.txt`.
- Initialize SQLite DB and run first migrations (or create tables).
- Download models: `faster-whisper` model weights (small/medium), spaCy Spanish model, SBERT model.

**Estimated effort**: 2–4 hours.

**Infra**: local machine, internet for initial downloads.

---

### 1) Local transcription (Whisper/whisper.cpp / faster-whisper)

**Goal**: Given an MP3, produce JSON transcript with timestamps and confidences.

**Tasks**
1. Implement audio preprocessor: convert MP3 -> WAV 16k mono (pydub / ffmpeg), normalize volume.
2. Implement VAD split to chunk long files (webrtcvad or silero VAD) into segments ≤ 5 minutes.
3. Call local STT (faster-whisper or whisper.cpp) to transcribe segments; collect start/end times, text, confidence.
4. Merge segment-level transcripts into one JSON for the file and store in `data/transcripts/` and DB.
5. Add retry logic: if low confidence, try alternative model size or re-run with higher precision.

**Estimated effort**: 1–2 days.

**Infra**: CPU-only works; GPU speeds up. Need model weights (small/medium for a balance).

**Code snippet (processing.py)**

```python
# backend/processing.py
from faster_whisper import WhisperModel
import soundfile as sf
from pydub import AudioSegment
import json

MODEL_SIZE = "small"
model = WhisperModel(MODEL_SIZE, device="cpu")

def convert_mp3_to_wav(mp3_path, wav_path, sr=16000):
    audio = AudioSegment.from_file(mp3_path)
    audio = audio.set_frame_rate(sr).set_channels(1)
    audio.export(wav_path, format="wav")

def transcribe(wav_path):
    segments, info = model.transcribe(wav_path, beam_size=5)
    out = []
    for segment in segments:
        out.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "avg_logprob": segment.avg_logprob,
            "compression_ratio": segment.compression_ratio
        })
    return out

if __name__ == "__main__":
    import sys
    wav = sys.argv[1]
    print(json.dumps(transcribe(wav), ensure_ascii=False, indent=2))
```

Notes: If you prefer `whisper.cpp`, replace the `transcribe` function with a subprocess call to the `main` binary and parse the output or use the JSON export.

---

### 2) Economic term detection (spaCy + rules + embeddings)

**Goal**: detect mentions of economic indicators and technical terms and extract numeric values when present.

**Tasks**
1. Build a small seed dictionary of canonical economic terms (e.g., inflación, IPC, PBI/PIB, reservas, desempleo, subsidios, déficit fiscal, volumen de importaciones, M2, tasa de interés, tasa de política monetaria — define canonical IDs).
2. Implement regex-based numeric and currency detection (percentages, pesos, dólares, millions/billions). Normalize text numbers to numeric values where possible.
3. Run spaCy Spanish pipeline to get tokens, lemmas, POS tags.
4. Use a `PhraseMatcher` and rule-based components for exact matches; then use SBERT embeddings + FAISS to find semantic matches to glossary terms (threshold-based).
5. Store detected mentions in `detected_terms` table with snippet, timestamp, numeric value (if any), and canonical_term.

**Estimated effort**: 1–2 days.

**Infra**: spaCy model + sentence-transformers + faiss.

**Code snippet (backend/processing.py)**

```python
# snippet: term extractor
import re
from spacy.lang.es import Spanish
from spacy.matcher import PhraseMatcher
from sentence_transformers import SentenceTransformer
import faiss

nlp = Spanish()
# load larger model in reality: spacy.load("es_core_news_lg")
sbert = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

ECON_TERMS = ["inflación", "IPC", "PIB", "reservas", "desempleo", "tasa de interés", "dólar"]
phrase_matcher = PhraseMatcher(nlp.vocab)
patterns = [nlp.make_doc(t) for t in ECON_TERMS]
phrase_matcher.add("ECON", patterns)

number_re = re.compile(r"(\d+[\.,]?\d*|un|dos|tres|cuatro|cinco)\s*(%|por ciento|pesos|u\$s|usd)?", re.I)

def extract_terms(text):
    doc = nlp(text)
    matches = phrase_matcher(doc)
    findings = []
    for match_id, start, end in matches:
        span = doc[start:end]
        findings.append({"term": span.text, "lemma": span.lemma_})
    for m in number_re.finditer(text):
        findings.append({"number_raw": m.group(0)})
    return findings
```

---

### 3) Economic Glossary (DB + vector store + review queue)

**Goal**: maintain a local glossary that is created at first run and updated when new terms are detected.

**Tasks**
1. Create `glossary_terms` table: id, term, canonical_label, definition, category, first_seen, last_seen, example, embeddings_blob, review_status.
2. When a detected term is not matched above threshold via FAISS search, add to `candidates` queue.
3. Provide an endpoint in FastAPI to list candidates and accept/reject with optional edit of definition.
4. When adding a term, compute and store its embedding in FAISS and DB.

**Estimated effort**: 1–2 days.

**Infra**: FAISS and SQLite; small review UI in Streamlit.

**Code snippet (backend/models.py)**

```python
# SQLAlchemy snippet
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class GlossaryTerm(Base):
    __tablename__ = 'glossary_terms'
    id = Column(Integer, primary_key=True)
    term = Column(String, unique=True)
    canonical = Column(String)
    definition = Column(Text)
    category = Column(String)
    first_seen = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime)
    example = Column(Text)
    review_status = Column(String, default='pending')
```

---

### 4) Argentine colloquial detection + dictionary

**Goal**: detect colloquial Argentine words and add them to a separate dictionary.

**Tasks**
1. Prepare seed list of Arg expressions (boludo, laburo, pibe, quilombo, re, posta, macanudo...). Put in `arg_dict_seed.json`.
2. After tokenization, identify OOV tokens versus spaCy Spanish vocabulary. Candidate OOV tokens that appear often or in context windows should be flagged.
3. Generate a suggested definition via local LLM (LM Studio) or manual entry in UI.
4. Store into `arg_dictionary` table (same schema as glossary with region field).

**Estimated effort**: 1 day.

**Infra**: same DB + local LLM for suggestion.

---

### 5) Dashboard & Streamlit control panel

**Goal**: provide a single-page control panel to upload audio, view processing status, inspect transcripts, view glossary candidates, and view basic indicator time series.

**Tasks**
1. Build endpoints in FastAPI: `/upload`, `/status/{id}`, `/transcript/{id}`, `/candidates`, `/indicators`.
2. Streamlit app with four tabs: Ingest, Recent transcripts (searchable), Glossary candidates (review queue), Indicators (time series from DB).
3. Link transcript lines to audio playback (Streamlit's `st.audio` with timestamped seek is limited; provide a small player and links).

**Estimated effort**: 2–3 days.

**Infra**: Streamlit, FastAPI running on localhost.

**Code snippet (streamlit_app/app.py)**

```python
# streamlit_app/app.py
import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.title("Argentine Econ Monitor - Local MVP")

tab = st.sidebar.radio("Panel", ["Ingest", "Transcripts", "Glossary", "Indicators"])

if tab == "Ingest":
    audio_file = st.file_uploader("Upload MP3", type=["mp3", "wav"])
    if audio_file:
        files = {"file": (audio_file.name, audio_file.getvalue())}
        r = requests.post(f"{API_BASE}/upload", files=files)
        st.write(r.json())

# more UI below for other tabs...
```

---

### 6) Scraper for official indicators (datos.gob.ar / BCRA)

**Goal**: pull time-series for official indicators and store them in `indicators` table.

**Tasks**
1. Identify series IDs you want (IPC (inflación mensual/índice), reservas internacionales, tipo de cambio oficial, desempleo, pobreza) from `datos.gob.ar` and BCRA. Store the series IDs in `config/sources.json`.
2. Implement `scraper.py` to call the API endpoints, normalize the response to `{indicator_code, date, value, source}` and upsert into DB.
3. Add CLI script `scripts/fetch_indicators.py` and test-run.
4. Schedule this script via cron (e.g., daily at 07:00) or systemd timer.

**Estimated effort**: 1–2 days (plus time to find exact series IDs; initial run may need troubleshooting).

**Infra**: internet required to fetch; but offline storage after fetch.

**Scraper snippet (backend/scraper.py)**

```python
# simplified example for datos.gob.ar
import requests

DATOS_API = "https://apis.datos.gob.ar/series/api/series"  # example

def fetch_series(series_id, start_date=None, end_date=None):
    params = {"ids": series_id}
    r = requests.get(DATOS_API, params=params)
    r.raise_for_status()
    payload = r.json()
    # normalize depending on payload structure
    return payload
```

Notes: for offline-only operation eventually you can manually download CSVs and place them in `data/indicators/` and run an import script.

---

### 7) Orchestration, scheduling, monitoring, backups

**Goal**: simple local orchestration to run ingestion jobs and scrapers regularly.

**Tasks**
1. Create CLI runner `backend/worker.py` that processes `data/audio_raw/` mailbox: picks new files, runs preprocess -> transcribe -> NLP -> store.
2. Use `cron` or `systemd` timers to call worker periodically or after upload.
3. Implement basic logging to file `logs/pipeline.log` and rotate logs.
4. Backups: nightly `sqlite3` dump or `pg_dump` if Postgres; copy `data/transcripts/` to `data/backups/`.

**Estimated effort**: 0.5–1 day.

---

## 5. Database schema (MVP)

**Tables** (SQLite):

- `transcripts`:
  - id (PK)
  - file_name
  - filepath
  - duration
  - processed_at
  - json_path

- `transcript_segments`:
  - id
  - transcript_id (FK)
  - start_sec
  - end_sec
  - text
  - confidence

- `detected_terms`:
  - id
  - transcript_segment_id
  - canonical_term_id (nullable)
  - raw_term
  - numeric_value (nullable)
  - detected_at

- `glossary_terms` (see models earlier)

- `arg_dictionary` (same fields as glossary_terms + region)

- `indicators`:
  - id
  - code
  - date
  - value
  - source
  - fetched_at

- `candidates_queue` (suggested new glossary entries): id, source_type, source_id, snippet, suggested_definition, created_at, status

Vector store: FAISS index saved under `data/faiss.index` with mapping table `vector_index_map` (id ↔ term id).

---

## 6. Minimal security & privacy considerations

- Audio can contain PII. Keep data on local disk with appropriate OS permissions (700 for data folder if single user).
- If exposing the API on LAN, bind only to localhost or use a reverse proxy with auth.
- Store API keys (if any) in environment variables or a local credentials file with tight permissions.

---

## 7. FastAPI + Streamlit skeleton (full files)

> **Important**: the repository file structure above is the reference. Below are minimal, ready-to-copy files for MVP.

### `backend/app/main.py`

```python
# backend/app/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from .processing import convert_mp3_to_wav

app = FastAPI()
DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
AUDIO_DIR = DATA_DIR / 'audio_raw'
TRANS_DIR = DATA_DIR / 'transcripts'
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TRANS_DIR.mkdir(parents=True, exist_ok=True)

@app.post('/upload')
async def upload_audio(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('mp3','wav')):
        raise HTTPException(status_code=400, detail='file must be mp3 or wav')
    save_path = AUDIO_DIR / file.filename
    with save_path.open('wb') as f:
        f.write(await file.read())
    # Optionally kick worker or return id for async processing
    return JSONResponse({'status': 'saved', 'filename': file.filename})

@app.get('/health')
async def health():
    return {'status': 'ok'}

# Add other endpoints for transcripts, candidates, indicators...
```

### `backend/app/processing.py`

```python
# backend/app/processing.py
from faster_whisper import WhisperModel
from pydub import AudioSegment
from pathlib import Path
import json

MODEL_SIZE = "small"
MODEL_DEVICE = "cpu"
model = WhisperModel(MODEL_SIZE, device=MODEL_DEVICE)

def convert_mp3_to_wav(mp3_path, wav_path, sr=16000):
    audio = AudioSegment.from_file(mp3_path)
    audio = audio.set_frame_rate(sr).set_channels(1)
    audio.export(wav_path, format="wav")

def transcribe_file(mp3_path, out_json_path):
    wav_path = str(Path(mp3_path).with_suffix('.wav'))
    convert_mp3_to_wav(mp3_path, wav_path)
    segments, info = model.transcribe(wav_path, beam_size=5)
    output = []
    for seg in segments:
        output.append({
            'start': seg.start,
            'end': seg.end,
            'text': seg.text,
            'avg_logprob': seg.avg_logprob
        })
    with open(out_json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    return out_json_path
```

### `backend/app/scraper.py` (simple example)

```python
# backend/app/scraper.py
import requests
from datetime import datetime

DATOS_API = "https://apis.datos.gob.ar/series/api/series"  # example

def fetch_indicador(series_id):
    params = {"ids": series_id}
    r = requests.get(DATOS_API, params=params)
    r.raise_for_status()
    payload = r.json()
    # extract values - depends on series format
    return payload

if __name__ == '__main__':
    print(fetch_indicador('INDEC/IPC'))
```

### `streamlit_app/app.py`

```python
# streamlit_app/app.py
import streamlit as st
import requests

API = 'http://localhost:8000'
st.title('Argentine Econ Monitor - Local')

tab = st.sidebar.selectbox('Panel', ['Ingest', 'Transcripts', 'Glossary', 'Indicators'])

if tab == 'Ingest':
    up = st.file_uploader('Upload mp3 or wav', type=['mp3','wav'])
    if up:
        files = {'file': (up.name, up.getvalue())}
        r = requests.post(f'{API}/upload', files=files)
        st.write(r.json())

if tab == 'Transcripts':
    st.write('List of recent transcripts (placeholder)')

if tab == 'Glossary':
    st.write('Candidates queue (placeholder)')

if tab == 'Indicators':
    st.write('Indicator panel (placeholder)')
```

---

## 8. How to run & quick test

1. Create venv and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Put `requirements.txt` with at least:
```
fastapi
uvicorn
streamlit
faster-whisper
pydub
sentence-transformers
faiss-cpu
sqlalchemy
spacy
spacy-langdetect
requests
python-multipart
```

2. Run FastAPI
```
cd backend
uvicorn app.main:app --reload --port 8000
```

3. Run Streamlit
```
cd streamlit_app
streamlit run app.py
```

4. Upload a small MP3 in Streamlit -> it will call `/upload` and save.
5. Manually run worker: `python backend/worker.py` to process files and produce transcripts.

---

## 9. Next steps & scaling notes

- Replace SQLite with Postgres and add Alembic migrations.
- Add speaker diarization (pyannote) if needed.
- Add sentiment/stance detection for mentions of indicators.
- Deploy FAISS to Milvus if vector dataset grows large.
- Add authentication and HTTPS for multi-user access.

---

## Appendix: estimated total effort (MVP)

- Setup & downloads: 0.5 day
- Transcription module: 1–2 days
- Term detection & small dictionary: 1–2 days
- Glossary DB + vectors + review UI: 1–2 days
- Scraper for 3–5 series + DB pipeline: 1 day
- FastAPI endpoints & Streamlit MVP: 1–2 days
- Orchestration + logging + tests: 0.5–1 day

**Total**: ~6–11 working days for a robust MVP. If you focus on a smaller scope (1–2 indicators, a seed glossary of 20 terms), you can do a minimal prototype in ~3 days.


---

_End of document._

