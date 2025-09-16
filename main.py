import logging
import shutil
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from src.config.settings import settings
from src.services.transcription_service import TranscriptionService
from src.services.glossary_service import GlossaryService
from src.services.term_detection_service import TermDetectionService
from src.repositories.database_repository import DatabaseRepository

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
    yield
    logger.info("Shutting down Argentina Economy Analyzer API")

# Initialize FastAPI app
app = FastAPI(
    title="Argentina Economy Analyzer API",
    description="Offline transcription + glossary updater + candidate detection (Refactored)",
    version="1.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0"}

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
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

        logger.info(f"Successfully processed {file.filename}: {response_data['stats']}")
        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing {file.filename if file.filename else 'unknown'}: {e}")
        # Try to clean up file if it exists
        if 'save_path' in locals() and save_path.exists():
            transcription_service.cleanup_file(save_path)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/glossaries")
async def get_glossaries():
    """Get all terms from economic glossary and Argentine dictionary"""
    try:
        glossaries = glossary_service.get_glossaries()
        return glossaries
    except Exception as e:
        logger.error(f"Error retrieving glossaries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve glossaries")

@app.get("/candidates")
async def get_candidates():
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

@app.post("/promote")
async def promote_candidate(
    term: str = Query(..., description="Candidate term to promote"),
    glossary: str = Query(..., description="Target glossary: 'economic' or 'argentine'")
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

        logger.info(f"Successfully promoted '{term}' to {glossary} glossary")
        return {"message": f"Term '{term}' promoted to {glossary} glossary"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting candidate '{term}': {e}")
        raise HTTPException(status_code=500, detail="Failed to promote candidate term")

@app.delete("/candidates/{term}")
async def remove_candidate(term: str):
    """Remove a candidate term (for manual cleanup)"""
    try:
        success = term_detection_service.remove_candidate(term)

        if not success:
            raise HTTPException(status_code=404, detail="Candidate term not found")

        return {"message": f"Candidate term '{term}' removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing candidate '{term}': {e}")
        raise HTTPException(status_code=500, detail="Failed to remove candidate term")

# ---------- MAIN ----------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )