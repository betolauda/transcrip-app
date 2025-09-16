# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Spanish audio transcription and economic analysis API** built with a modern service-oriented architecture. The application uses OpenAI's Whisper model for offline speech-to-text processing, combined with intelligent economic term detection and Argentine expression recognition. The system is designed for production use with comprehensive security, logging, and configuration management.

## Architecture

### Technology Stack
- **Backend Framework**: FastAPI with uvicorn server
- **Architecture Pattern**: Service-Oriented Architecture (SOA)
- **Speech Recognition**: OpenAI Whisper (configurable model) for Spanish transcription
- **Database**: SQLite with optimized schema and indexes
- **Configuration**: Environment-based settings management
- **Security**: File validation, input sanitization, comprehensive error handling
- **Logging**: Structured logging throughout the application
- **Language**: Spanish audio processing (`language="es"`)

### Service Architecture

The application follows clean architecture principles with clear separation of concerns:

```
src/
├── config/
│   └── settings.py              # Environment-based configuration
├── models/
│   └── domain_models.py         # Data classes and domain models
├── repositories/
│   └── database_repository.py   # Centralized database operations
└── services/
    ├── transcription_service.py    # Audio processing & Whisper integration
    ├── glossary_service.py         # Economic/Argentine term management
    └── term_detection_service.py   # Candidate term discovery
```

### Core Services

#### TranscriptionService (`src/services/transcription_service.py`)
- **Purpose**: Handles all audio transcription operations
- **Features**:
  - Lazy-loaded Whisper model for memory efficiency
  - File validation with security checks (magic numbers, size limits)
  - Error handling and logging
  - Automatic file cleanup
- **Key Methods**: `transcribe_audio()`, `validate_audio_file()`, `cleanup_file()`

#### GlossaryService (`src/services/glossary_service.py`)
- **Purpose**: Manages economic terms and Argentine expressions
- **Features**:
  - Automatic term detection in transcripts
  - Candidate term promotion to specific glossaries
  - Statistics tracking for glossary updates
- **Key Methods**: `update_glossaries()`, `promote_candidate_to_economic()`, `promote_candidate_to_argentine()`

#### TermDetectionService (`src/services/term_detection_service.py`)
- **Purpose**: Intelligent candidate term discovery and management
- **Features**:
  - Text normalization and accent removal
  - Context extraction for candidate terms
  - Spanish stopword filtering
  - Candidate promotion and cleanup
- **Key Methods**: `detect_new_terms()`, `normalize_token()`, `get_candidates()`

#### DatabaseRepository (`src/repositories/database_repository.py`)
- **Purpose**: Centralized database operations with connection management
- **Features**:
  - Context manager for safe database connections
  - Automatic schema initialization with indexes
  - Transaction management and rollback support
- **Key Methods**: Connection management, CRUD operations for all entities

## Configuration Management

### Environment Variables
The application uses environment-based configuration via `src/config/settings.py`:

```bash
# Database settings
DB_PATH=data/transcriptions.db

# File upload settings
UPLOAD_DIR=uploads
MAX_FILE_SIZE=50  # MB

# Whisper model settings
WHISPER_MODEL=base
TRANSCRIPTION_LANGUAGE=es

# API settings
API_HOST=0.0.0.0
API_PORT=8000
```

### Configuration Class
- **Settings**: Centralized configuration with sensible defaults
- **Auto-creation**: Directories and database automatically created
- **Validation**: Type checking and validation for all settings

## Database Schema

The application uses a normalized SQLite database with proper indexing:

### Tables

#### `transcriptions`
- **Purpose**: Store audio file transcripts
- **Fields**: id, filename, transcript, created_at
- **Index**: idx_transcriptions_created_at

#### `economic_glossary`
- **Purpose**: Economic terms and indicators
- **Fields**: id, term, category, first_seen
- **Index**: idx_economic_glossary_term

#### `argentine_dictionary`
- **Purpose**: Argentine colloquial expressions
- **Fields**: id, expression, first_seen
- **Index**: idx_argentine_dictionary_expression

#### `candidate_terms`
- **Purpose**: Discovered terms awaiting manual review
- **Fields**: id, term, first_seen, context_snippet
- **Index**: idx_candidate_terms_term

## API Endpoints

### Core Endpoints

#### `POST /upload`
- **Purpose**: Upload and process audio files
- **Features**:
  - File validation and security checks
  - Transcription processing
  - Automatic glossary updates
  - Candidate term detection
- **Returns**: Processing statistics and transcript preview

#### `GET /glossaries`
- **Purpose**: Retrieve all economic and Argentine terms
- **Returns**: Complete glossary data with timestamps

#### `GET /candidates`
- **Purpose**: Get candidate terms awaiting promotion
- **Returns**: Candidate terms with context and statistics

#### `POST /promote`
- **Purpose**: Promote candidate terms to specific glossaries
- **Parameters**: term (string), glossary ("economic" or "argentine")

#### `DELETE /candidates/{term}`
- **Purpose**: Remove candidate terms (cleanup)

#### `GET /health`
- **Purpose**: Health check endpoint for monitoring

## Development Commands

### Environment Setup

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

**Service URLs:**
- **API**: `http://localhost:8000`
- **Web Interface**: `http://localhost:8501`
- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

### Dependencies

Enhanced dependencies in `requirements.txt`:
- `fastapi` - Web framework for the API
- `uvicorn[standard]` - ASGI server for FastAPI
- `whisper-openai` - OpenAI Whisper for transcription
- `streamlit` - Web interface framework
- `requests` - HTTP client for frontend-backend communication
- `python-multipart` - File upload support
- `python-magic` - File type validation (security)
- `pydantic` - Data validation and settings management

## Security Features

### File Security
- **Magic Number Validation**: Checks actual file type, not just extension
- **Size Limits**: Configurable maximum file size (default 50MB)
- **Path Sanitization**: Secure file handling and storage
- **Automatic Cleanup**: Files removed after processing

### Input Validation
- **Type Checking**: Pydantic models for all data structures
- **SQL Injection Protection**: Parameterized queries throughout
- **Error Sanitization**: Safe error messages without information leakage

### Production Considerations
- **Structured Logging**: Comprehensive logging for monitoring
- **Health Checks**: Endpoint for load balancer integration
- **Resource Management**: Proper connection pooling and cleanup
- **Configuration Security**: Environment-based secrets management

## Development Guidelines

### Adding New Services
1. Create service class in `src/services/`
2. Implement dependency injection for DatabaseRepository
3. Add comprehensive error handling and logging
4. Write unit tests covering all methods
5. Update API endpoints to integrate new service

### Database Changes
1. Modify schema in `database_repository.py`
2. Add migration logic in `init_db()` method
3. Update domain models in `src/models/domain_models.py`
4. Test with existing data for backward compatibility

### Configuration Updates
1. Add new settings to `src/config/settings.py`
2. Document environment variables
3. Provide sensible defaults
4. Update documentation

## Troubleshooting

### Common Issues

#### "No module named 'whisper'"
- **Solution**: Ensure `whisper-openai` is installed in your virtual environment

#### Database Lock Errors
- **Solution**: The repository uses context managers to prevent connection leaks

#### Memory Issues with Large Files
- **Solution**: Adjust `MAX_FILE_SIZE` setting and monitor system resources

#### Performance Issues
- **Solution**: Check database indexes and consider upgrading from SQLite to PostgreSQL

### Development Tips
- Use the health check endpoint (`/health`) to verify service status
- Check logs for detailed error information
- The database repository handles all connection management automatically
- Services are designed to be independently testable

## File Structure Context

This transcription API serves as the core component of a larger Argentine economic monitoring system. The service-oriented architecture makes it easy to integrate with additional services like news scrapers, indicator dashers, and analysis engines.

## Important Notes

### Current Capabilities
- **File Support**: MP3 files only (configurable)
- **Language**: Spanish language optimized for Argentine dialect
- **Model**: Whisper base model (configurable via WHISPER_MODEL env var)
- **Database**: SQLite with production-ready schema and indexes
- **Security**: Comprehensive file validation and input sanitization
- **Monitoring**: Health checks and structured logging
- **Configuration**: Environment-based configuration management

### Production Readiness
- **Error Handling**: Comprehensive exception handling throughout
- **Logging**: Structured logging for monitoring and debugging
- **Security**: File validation, input sanitization, resource cleanup
- **Performance**: Optimized database queries with proper indexing
- **Scalability**: Service-oriented architecture for horizontal scaling