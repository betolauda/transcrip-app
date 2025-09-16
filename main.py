import logging
import shutil
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.services.transcription_service import TranscriptionService
from src.services.glossary_service import GlossaryService
from src.services.term_detection_service import TermDetectionService
from src.repositories.database_repository import DatabaseRepository
from src.api.auth_endpoints import router as auth_router
from src.api.monitoring_endpoints import router as monitoring_router
from src.api.database_endpoints import router as database_router
from src.api.examples_endpoints import router as examples_router
from src.api.audio_endpoints import router as audio_router
from src.auth.dependencies import get_current_active_user, rate_limit_upload, rate_limit_general
from src.middleware.rate_limiting import rate_limit_middleware, setup_periodic_cleanup
from src.middleware.validation import validation_middleware
from src.middleware.monitoring import monitoring_middleware
from src.api.documentation import get_custom_openapi, get_custom_swagger_ui_html, get_custom_redoc_html

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
db_repository = DatabaseRepository()
transcription_service = TranscriptionService(db_repository)
glossary_service = GlossaryService(db_repository)
term_detection_service = TermDetectionService(db_repository)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Argentina Economy Analyzer API")
    logger.info(f"Database path: {settings.DB_PATH}")
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")

    # Start periodic cleanup for rate limiting
    if settings.ENABLE_RATE_LIMITING:
        setup_periodic_cleanup()
        logger.info("Started rate limiting cleanup worker")

    # Auto-apply database migrations on startup
    try:
        from src.database.migrations import auto_migrate
        if auto_migrate():
            logger.info("Database migrations applied successfully")
        else:
            logger.warning("Database migration check failed")
    except Exception as e:
        logger.error(f"Error during database migration: {e}")

    yield
    logger.info("Shutting down Argentina Economy Analyzer API")

# Initialize FastAPI app
app = FastAPI(
    title="Spanish Audio Transcription API",
    description="Professional Spanish audio transcription with economic term detection and user authentication",
    version="1.1.0",
    lifespan=lifespan,
    docs_url=None,  # Disable default docs
    redoc_url=None  # Disable default redoc
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security and validation middleware (order matters)
# Monitoring should be first to capture all requests
app.middleware("http")(monitoring_middleware)
logger.info("Enabled monitoring middleware")

if settings.ENABLE_REQUEST_VALIDATION:
    app.middleware("http")(validation_middleware)
    logger.info("Enabled request validation middleware")

if settings.ENABLE_RATE_LIMITING:
    app.middleware("http")(rate_limit_middleware)
    logger.info("Enabled rate limiting middleware")

# Include authentication router
app.include_router(auth_router, prefix=f"/api/{settings.API_VERSION}")

# Include monitoring router
app.include_router(monitoring_router, prefix=f"/api/{settings.API_VERSION}")

# Include database management router
app.include_router(database_router, prefix=f"/api/{settings.API_VERSION}")

# Include examples and guides router
app.include_router(examples_router, prefix=f"/api/{settings.API_VERSION}")

# Include audio processing router
app.include_router(audio_router, prefix=f"/api/{settings.API_VERSION}")

# Create a router for protected endpoints
from fastapi import APIRouter
protected_router = APIRouter(prefix=f"/api/{settings.API_VERSION}", dependencies=[Depends(get_current_active_user)])

@app.get("/health")
async def health_check():
    """Public health check endpoint"""
    return {"status": "healthy", "version": "1.1.0", "authenticated": False}

@app.get("/api/{settings.API_VERSION}/health")
async def protected_health_check(current_user = Depends(get_current_active_user)):
    """Protected health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.1.0",
        "authenticated": True,
        "user": current_user.username,
        "role": current_user.role
    }

@protected_router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    current_user = Depends(rate_limit_upload)
):
    """
    Upload and process audio file
    - Validates file format and security
    - Transcribes audio using Whisper
    - Updates glossaries with found terms
    - Detects new candidate terms
    """
    try:
        # Basic file validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        if not file.filename.endswith(".mp3"):
            raise HTTPException(status_code=400, detail="Only .mp3 files are supported")

        # Save uploaded file
        save_path = settings.UPLOAD_DIR / file.filename
        try:
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")

        # Transcribe audio
        transcription_result = transcription_service.transcribe_audio(save_path, file.filename)

        if not transcription_result.success:
            # Clean up file on failure
            transcription_service.cleanup_file(save_path)
            raise HTTPException(
                status_code=400 if "validation" in transcription_result.message.lower() else 500,
                detail=transcription_result.error or transcription_result.message
            )

        # Use the full transcript for processing glossaries and term detection
        full_transcript = transcription_result.full_transcript

        # Update glossaries
        glossary_stats = glossary_service.update_glossaries(full_transcript)

        # Detect new terms
        detection_stats = term_detection_service.detect_new_terms(full_transcript)

        # Clean up uploaded file
        transcription_service.cleanup_file(save_path)

        # Prepare response
        response_data = {
            "filename": file.filename,
            "transcript_preview": transcription_result.transcript_preview,
            "message": "File processed, saved, glossaries updated, candidates detected",
            "stats": {
                **glossary_stats,
                **detection_stats
            }
        }

        logger.info(f"Successfully processed {file.filename} by user {current_user.username}: {response_data['stats']}")
        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing {file.filename if file.filename else 'unknown'}: {e}")
        # Try to clean up file if it exists
        if 'save_path' in locals() and save_path.exists():
            transcription_service.cleanup_file(save_path)
        raise HTTPException(status_code=500, detail="Internal server error")

@protected_router.get("/glossaries")
async def get_glossaries(current_user = Depends(rate_limit_general)):
    """Get all terms from economic glossary and Argentine dictionary"""
    try:
        glossaries = glossary_service.get_glossaries()
        return glossaries
    except Exception as e:
        logger.error(f"Error retrieving glossaries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve glossaries")

@protected_router.get("/candidates")
async def get_candidates(current_user = Depends(rate_limit_general)):
    """Get all candidate terms awaiting promotion"""
    try:
        candidates = term_detection_service.get_candidates()
        stats = term_detection_service.get_candidate_statistics()

        return {
            "candidates": candidates,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error retrieving candidates: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve candidates")

@protected_router.post("/promote")
async def promote_candidate(
    term: str = Query(..., description="Candidate term to promote"),
    glossary: str = Query(..., description="Target glossary: 'economic' or 'argentine'"),
    current_user = Depends(rate_limit_general)
):
    """Promote a candidate term to either economic glossary or Argentine dictionary"""
    try:
        # Validate glossary parameter
        if glossary not in ["economic", "argentine"]:
            raise HTTPException(
                status_code=400,
                detail="Glossary must be 'economic' or 'argentine'"
            )

        # Validate term exists
        if not db_repository.candidate_term_exists(term):
            raise HTTPException(status_code=404, detail="Candidate term not found")

        # Promote based on target glossary
        if glossary == "economic":
            success = glossary_service.promote_candidate_to_economic(term)
        else:
            success = glossary_service.promote_candidate_to_argentine(term)

        if not success:
            raise HTTPException(
                status_code=409,
                detail=f"Term '{term}' already exists in {glossary} glossary"
            )

        logger.info(f"Successfully promoted '{term}' to {glossary} glossary by user {current_user.username}")
        return {"message": f"Term '{term}' promoted to {glossary} glossary"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting candidate '{term}': {e}")
        raise HTTPException(status_code=500, detail="Failed to promote candidate term")

@protected_router.delete("/candidates/{term}")
async def remove_candidate(term: str, current_user = Depends(rate_limit_general)):
    """Remove a candidate term (for manual cleanup)"""
    try:
        success = term_detection_service.remove_candidate(term)

        if not success:
            raise HTTPException(status_code=404, detail="Candidate term not found")

        logger.info(f"Candidate term '{term}' removed by user {current_user.username}")
        return {"message": f"Candidate term '{term}' removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing candidate '{term}': {e}")
        raise HTTPException(status_code=500, detail="Failed to remove candidate term")

# Include protected router
app.include_router(protected_router)

# Custom OpenAPI and documentation endpoints
app.openapi = lambda: get_custom_openapi(app)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI documentation."""
    return get_custom_swagger_ui_html()

@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """Custom ReDoc documentation."""
    return get_custom_redoc_html()

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    """Get OpenAPI schema."""
    return app.openapi()

# ---------- MAIN ----------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )