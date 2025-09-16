# 🇦🇷 Argentina Economy Transcription API

A production-ready Spanish audio transcription and economic analysis system built with modern service-oriented architecture. Uses OpenAI Whisper for offline processing of Argentine economic content with intelligent glossary building and comprehensive security features.

## ✨ Features

### 🎤 **Audio Processing**
- **Spanish MP3 Transcription**: High-quality Whisper-based transcription optimized for Argentine dialect
- **File Security**: Magic number validation, size limits, and secure file handling
- **Automatic Cleanup**: Temporary files removed after processing

### 📊 **Economic Intelligence**
- **Economic Term Detection**: Automatically identifies economic indicators (inflación, PIB, dólar, etc.)
- **Argentine Expression Recognition**: Detects colloquial terms (laburo, guita, che, etc.)
- **Candidate Discovery**: Finds and catalogs unknown terms with contextual information
- **Manual Curation**: Promote candidate terms to specific glossaries with web interface

### 🏗️ **Modern Architecture**
- **Service-Oriented Design**: Clean separation of concerns with dedicated services
- **Production Ready**: Comprehensive logging, error handling, and monitoring
- **Configuration Management**: Environment-based settings for different deployments
- **Database Optimization**: Indexed SQLite schema with efficient queries

### 🔒 **Security & Reliability**
- **File Validation**: Multi-layer security checks beyond file extensions
- **Input Sanitization**: Comprehensive validation for all user inputs
- **Resource Management**: Automatic connection pooling and cleanup
- **Health Monitoring**: Built-in health checks for load balancer integration

### 🌐 **User Experience**
- **Web Interface**: User-friendly Streamlit dashboard for complete workflow
- **REST API**: Full-featured API with automatic documentation
- **Offline Processing**: No external APIs required after initial setup
- **Real-time Statistics**: Processing stats and performance metrics

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- 8GB+ RAM recommended
- 2GB+ disk space for models and data

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

### Configuration (Optional)

Create a `.env` file to customize settings:

```bash
# Database settings
DB_PATH=data/transcriptions.db

# File upload settings
UPLOAD_DIR=uploads
MAX_FILE_SIZE=50  # MB

# Whisper model settings (small, base, medium, large)
WHISPER_MODEL=base
TRANSCRIPTION_LANGUAGE=es

# API settings
API_HOST=0.0.0.0
API_PORT=8000
```

### Run the Application

```bash
# Terminal 1: Start FastAPI backend
python3 main.py

# Terminal 2: Start Streamlit frontend
streamlit run app.py
```

**Service URLs:**
- **🌐 Web Interface**: http://localhost:8501
- **📖 API Documentation**: http://localhost:8000/docs
- **🔍 Health Check**: http://localhost:8000/health
- **⚡ API Endpoint**: http://localhost:8000

## 📖 Usage

### Web Interface Workflow
1. **Upload**: Navigate to http://localhost:8501 and upload MP3 files
2. **Review**: Examine detected economic terms and Argentine expressions
3. **Curate**: Promote candidate terms to appropriate glossaries
4. **Monitor**: Track processing statistics and system health

### API Integration

#### Upload and Process Audio
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3"
```

#### Retrieve Glossaries
```bash
curl -X GET "http://localhost:8000/glossaries"
```

#### Get Candidate Terms
```bash
curl -X GET "http://localhost:8000/candidates"
```

#### Promote Candidate to Economic Glossary
```bash
curl -X POST "http://localhost:8000/promote?term=blockchain&glossary=economic"
```

## 🏗️ Architecture

### Service-Oriented Design

```
transcrip-app/
├── src/
│   ├── config/
│   │   └── settings.py              # Environment-based configuration
│   ├── models/
│   │   └── domain_models.py         # Data classes and domain models
│   ├── repositories/
│   │   └── database_repository.py   # Centralized database operations
│   └── services/
│       ├── transcription_service.py    # Audio processing & Whisper
│       ├── glossary_service.py         # Economic/Argentine terms
│       └── term_detection_service.py   # Candidate discovery
├── main.py                          # FastAPI application
├── app.py                           # Streamlit web interface
├── dashboard.py                     # Economic indicators dashboard
├── requirements.txt                 # Python dependencies
├── CLAUDE.md                        # Development guide
├── data/                            # SQLite database (auto-created)
├── uploads/                         # Audio file storage (auto-created)
└── README.md                        # This file
```

### Core Services

- **🎯 TranscriptionService**: Handles Whisper model integration with security validation
- **📚 GlossaryService**: Manages economic terms and Argentine expressions
- **🔍 TermDetectionService**: Discovers new candidate terms with context
- **💾 DatabaseRepository**: Centralized data operations with connection management

## 🗄️ Database Schema

### Optimized SQLite Database
- **`transcriptions`**: Audio file transcripts with timestamps and metadata
- **`economic_glossary`**: Economic terms with categories and detection timestamps
- **`argentine_dictionary`**: Argentine colloquial expressions with usage context
- **`candidate_terms`**: Discovered terms awaiting manual review with context snippets

### Performance Features
- **Indexed Queries**: Optimized database performance with strategic indexing
- **Connection Pooling**: Efficient database connection management
- **Transaction Safety**: Rollback support for data integrity

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `data/transcriptions.db` | Database file location |
| `UPLOAD_DIR` | `uploads` | Upload directory path |
| `MAX_FILE_SIZE` | `50` | Maximum file size in MB |
| `WHISPER_MODEL` | `base` | Whisper model size (small/base/medium/large) |
| `TRANSCRIPTION_LANGUAGE` | `es` | Audio language code |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |

### Whisper Models
- **small**: Fast, lower accuracy (~150MB)
- **base**: Balanced performance (~300MB) - **Recommended**
- **medium**: Higher accuracy (~1GB)
- **large**: Best accuracy (~3GB)

## 🛠️ Development

### Architecture Principles
- **Service Separation**: Each service has a single responsibility
- **Dependency Injection**: Services receive dependencies through constructors
- **Error Handling**: Comprehensive exception handling with logging
- **Configuration**: Environment-based settings management
- **Testing**: Services designed for independent unit testing

### Adding New Features
1. **Services**: Create new services in `src/services/` with proper dependency injection
2. **Database**: Update schema in `database_repository.py` with migration logic
3. **API**: Add endpoints in `main.py` following existing patterns
4. **Frontend**: Update Streamlit interface in `app.py`

### Development Tools
- **Health Check**: Monitor service status at `/health`
- **API Docs**: Interactive documentation at `/docs`
- **Logging**: Structured logging for debugging and monitoring
- **Database Tools**: Direct SQLite access via repository methods

## 📊 Performance & Monitoring

### System Requirements
- **Minimum**: 8GB RAM, 2GB disk space
- **Recommended**: 16GB RAM, 5GB disk space, SSD storage
- **GPU**: Optional, speeds up transcription significantly

### Monitoring Features
- **Health Endpoint**: Service status monitoring
- **Processing Statistics**: Real-time performance metrics
- **Error Tracking**: Comprehensive error logging
- **Resource Usage**: Database and file system monitoring

## 🔒 Security Features

### File Security
- **Type Validation**: Magic number checking beyond file extensions
- **Size Limits**: Configurable maximum file sizes
- **Path Sanitization**: Secure file handling and storage
- **Cleanup**: Automatic removal of temporary files

### Application Security
- **Input Validation**: Comprehensive data validation using Pydantic
- **SQL Injection Protection**: Parameterized queries throughout
- **Error Sanitization**: Safe error messages without information leakage
- **Resource Limits**: Protection against resource exhaustion

## 🔍 Troubleshooting

### Common Issues

#### Model Loading Errors
```bash
# Ensure whisper-openai is properly installed
pip install --upgrade whisper-openai
```

#### Memory Issues
```bash
# Reduce model size in configuration
export WHISPER_MODEL=small
```

#### Database Lock Errors
- The application uses connection pooling to prevent this automatically
- Check disk space and file permissions

#### Performance Issues
- Monitor `/health` endpoint for system status
- Consider upgrading to medium/large Whisper model for better accuracy
- Check database indexes and query performance

### Support
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs
- **Logs**: Check application logs for detailed error information

## 📜 License

Open source side project for Argentine economic content analysis.

## 🤝 Contributing

This project uses modern Python development practices:
- Service-oriented architecture
- Comprehensive error handling
- Environment-based configuration
- Structured logging
- Production-ready security features

---

*🤖 Enhanced with Claude Code for intelligent Argentine economic content processing*

---

## Recent Updates

### v1.0 - Service-Oriented Architecture Refactor
- ✅ **Complete architectural redesign** with service separation
- ✅ **Enhanced security** with file validation and input sanitization
- ✅ **Production readiness** with logging, monitoring, and error handling
- ✅ **Configuration management** with environment-based settings
- ✅ **Database optimization** with indexes and connection pooling
- ✅ **Improved API** with health checks and comprehensive endpoints