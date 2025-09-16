"""
API endpoints for audio processing analytics and management.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse

from ..auth.dependencies import get_current_active_user, require_admin
from ..auth.models import User
from ..services.audio_processor import OptimizedAudioProcessor

router = APIRouter(prefix="/audio", tags=["Audio Processing"])


@router.post("/analyze")
async def analyze_audio_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Analyze uploaded audio file without transcription."""
    try:
        if not file.filename or not file.filename.endswith('.mp3'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only MP3 files are supported"
            )

        # Save file temporarily for analysis
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            content = await file.read()
            temp_file.write(content)

        try:
            # Analyze audio
            processor = OptimizedAudioProcessor()
            metadata = processor.analyze_audio_file(temp_path)
            recommendations = processor.get_optimization_recommendations(metadata)

            # Clean up temp file
            temp_path.unlink()

            return {
                "filename": file.filename,
                "metadata": {
                    "duration_seconds": metadata.duration_seconds,
                    "sample_rate": metadata.sample_rate,
                    "channels": metadata.channels,
                    "format": metadata.format,
                    "file_size_bytes": metadata.file_size_bytes,
                    "file_size_mb": round(metadata.file_size_bytes / (1024 * 1024), 2),
                    "quality_score": round(metadata.quality_score, 3),
                    "noise_level": round(metadata.noise_level, 3),
                    "speech_probability": round(metadata.speech_probability, 3)
                },
                "recommendations": recommendations,
                "quality_assessment": _assess_audio_quality(metadata),
                "estimated_processing_time": _estimate_processing_time(metadata)
            }

        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analysis failed: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File analysis failed: {str(e)}"
        )


@router.get("/processing-stats")
async def get_processing_statistics(
    current_user: User = Depends(require_admin)
):
    """Get audio processing statistics (admin only)."""
    try:
        # In a real implementation, this would query the database
        # for historical processing statistics
        stats = {
            "total_files_processed": 1250,
            "average_processing_time": 2.4,
            "average_quality_score": 0.72,
            "optimization_usage": {
                "files_optimized": 450,
                "optimization_rate": 36.0,
                "average_quality_improvement": 0.18
            },
            "file_size_distribution": {
                "small_files_mb": {"count": 800, "range": "< 10 MB"},
                "medium_files_mb": {"count": 350, "range": "10-50 MB"},
                "large_files_mb": {"count": 100, "range": "> 50 MB"}
            },
            "quality_distribution": {
                "poor_quality": {"count": 125, "range": "< 0.3"},
                "fair_quality": {"count": 375, "range": "0.3-0.6"},
                "good_quality": {"count": 500, "range": "0.6-0.8"},
                "excellent_quality": {"count": 250, "range": "> 0.8"}
            },
            "common_issues": [
                {"issue": "High noise level", "frequency": 280},
                {"issue": "Low volume", "frequency": 150},
                {"issue": "Poor sample rate", "frequency": 95},
                {"issue": "Multiple channels", "frequency": 75}
            ],
            "performance_trends": {
                "last_24h": {"avg_time": 2.1, "files": 45},
                "last_7d": {"avg_time": 2.3, "files": 312},
                "last_30d": {"avg_time": 2.4, "files": 1250}
            }
        }

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing statistics: {str(e)}"
        )


@router.get("/optimization-settings")
async def get_optimization_settings(
    current_user: User = Depends(require_admin)
):
    """Get current audio optimization settings (admin only)."""
    return {
        "audio_enhancement": {
            "enabled": True,
            "quality_threshold": 0.6,
            "noise_threshold": 0.3,
            "auto_enhancement": True
        },
        "chunked_processing": {
            "enabled": True,
            "duration_threshold_seconds": 300,
            "chunk_duration_seconds": 30,
            "overlap_seconds": 2
        },
        "whisper_optimization": {
            "enabled": True,
            "adaptive_parameters": True,
            "temperature_adjustment": True,
            "confidence_thresholds": True
        },
        "performance": {
            "target_sample_rate": 16000,
            "target_channels": 1,
            "max_file_size_mb": 50,
            "cleanup_processed_files": True
        }
    }


@router.put("/optimization-settings")
async def update_optimization_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(require_admin)
):
    """Update audio optimization settings (admin only)."""
    try:
        # Validate settings
        valid_keys = {
            "audio_enhancement", "chunked_processing",
            "whisper_optimization", "performance"
        }

        for key in settings.keys():
            if key not in valid_keys:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid setting key: {key}"
                )

        # In a real implementation, save to database or config file
        # For now, just return the updated settings
        return {
            "message": "Optimization settings updated successfully",
            "updated_settings": settings
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@router.get("/quality-report")
async def get_quality_report(
    days: int = 7,
    current_user: User = Depends(require_admin)
):
    """Get audio quality report for specified period (admin only)."""
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )

        # Mock data - in real implementation, query database
        report = {
            "period": {
                "days": days,
                "start_date": "2024-01-08T00:00:00Z",
                "end_date": "2024-01-15T00:00:00Z"
            },
            "summary": {
                "total_files": 150,
                "average_quality": 0.68,
                "files_needing_optimization": 54,
                "optimization_success_rate": 0.87
            },
            "quality_trends": [
                {"date": "2024-01-08", "avg_quality": 0.65, "file_count": 18},
                {"date": "2024-01-09", "avg_quality": 0.71, "file_count": 22},
                {"date": "2024-01-10", "avg_quality": 0.69, "file_count": 25},
                {"date": "2024-01-11", "avg_quality": 0.66, "file_count": 19},
                {"date": "2024-01-12", "avg_quality": 0.72, "file_count": 21},
                {"date": "2024-01-13", "avg_quality": 0.70, "file_count": 24},
                {"date": "2024-01-14", "avg_quality": 0.68, "file_count": 21}
            ],
            "improvement_metrics": {
                "average_quality_gain": 0.23,
                "noise_reduction_effectiveness": 0.45,
                "processing_time_overhead": 1.8
            },
            "recommendations": [
                "Consider adjusting noise reduction settings for better performance",
                "Monitor files with quality scores below 0.4 for manual review",
                "Optimize chunked processing for files over 5 minutes"
            ]
        }

        return report

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quality report: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_processed_files(
    max_age_hours: int = 24,
    current_user: User = Depends(require_admin)
):
    """Clean up old processed audio files (admin only)."""
    try:
        if max_age_hours < 1 or max_age_hours > 168:  # 1 week max
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Max age must be between 1 and 168 hours"
            )

        processor = OptimizedAudioProcessor()
        processor.cleanup_processed_files(max_age_hours)

        return {
            "message": f"Cleanup completed for files older than {max_age_hours} hours",
            "max_age_hours": max_age_hours
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )


def _assess_audio_quality(metadata) -> Dict[str, Any]:
    """Assess audio quality and provide detailed breakdown."""
    quality = metadata.quality_score

    if quality >= 0.8:
        assessment = "Excellent"
        color = "green"
    elif quality >= 0.6:
        assessment = "Good"
        color = "blue"
    elif quality >= 0.4:
        assessment = "Fair"
        color = "yellow"
    elif quality >= 0.2:
        assessment = "Poor"
        color = "orange"
    else:
        assessment = "Very Poor"
        color = "red"

    factors = []

    if metadata.noise_level > 0.5:
        factors.append("High background noise detected")
    if metadata.speech_probability < 0.4:
        factors.append("Low speech content probability")
    if metadata.sample_rate < 16000:
        factors.append("Low sample rate may affect accuracy")
    if metadata.channels > 1:
        factors.append("Stereo audio - mono recommended for speech")

    return {
        "overall": assessment,
        "score": quality,
        "color": color,
        "factors_affecting_quality": factors,
        "transcription_suitability": quality > 0.3
    }


def _estimate_processing_time(metadata) -> Dict[str, Any]:
    """Estimate processing time based on audio characteristics."""
    base_time_per_second = 0.1  # Base processing time
    duration = metadata.duration_seconds

    # Adjust based on quality (poor quality takes longer)
    quality_multiplier = 1.0
    if metadata.quality_score < 0.4:
        quality_multiplier = 1.5
    elif metadata.quality_score < 0.6:
        quality_multiplier = 1.2

    # Adjust based on duration (chunked processing for long files)
    duration_multiplier = 1.0
    if duration > 300:  # 5 minutes
        duration_multiplier = 0.8  # Chunked processing is more efficient

    estimated_seconds = duration * base_time_per_second * quality_multiplier * duration_multiplier

    # Add optimization overhead if needed
    if metadata.quality_score < 0.6 or metadata.noise_level > 0.3:
        estimated_seconds += duration * 0.05  # 5% overhead for optimization

    return {
        "estimated_seconds": round(estimated_seconds, 1),
        "estimated_minutes": round(estimated_seconds / 60, 1),
        "factors": {
            "audio_duration": duration,
            "quality_impact": quality_multiplier,
            "processing_efficiency": duration_multiplier,
            "optimization_needed": metadata.quality_score < 0.6
        }
    }