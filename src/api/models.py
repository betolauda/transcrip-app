"""
Enhanced API models with comprehensive documentation and examples.

This module defines Pydantic models for API requests and responses
with detailed documentation, validation rules, and examples.
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


class ResponseStatus(str, Enum):
    """Response status enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class BaseResponse(BaseModel):
    """Base response model for all API endpoints."""
    status: ResponseStatus = Field(
        ...,
        description="Response status indicator",
        example=ResponseStatus.SUCCESS
    )
    message: str = Field(
        ...,
        description="Human-readable response message",
        example="Operation completed successfully"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response timestamp in ISO format",
        example="2024-01-15T10:30:00Z"
    )

    class Config:
        use_enum_values = True


class TranscriptionRequest(BaseModel):
    """Request model for audio transcription."""
    # Note: File upload is handled separately in FastAPI
    # This model documents the expected form data structure

    class Config:
        schema_extra = {
            "example": {
                "file": "spanish_audio.mp3",
                "description": "MP3 file containing Spanish audio to transcribe"
            }
        }


class TranscriptionStats(BaseModel):
    """Statistics from transcription processing."""
    economic_terms_found: int = Field(
        ...,
        description="Number of economic terms detected",
        example=12,
        ge=0
    )
    argentine_expressions_found: int = Field(
        ...,
        description="Number of Argentine expressions detected",
        example=3,
        ge=0
    )
    new_candidates_detected: int = Field(
        ...,
        description="Number of new candidate terms detected",
        example=5,
        ge=0
    )
    processing_time_seconds: float = Field(
        ...,
        description="Total processing time in seconds",
        example=1.8,
        gt=0
    )
    transcript_length: int = Field(
        ...,
        description="Length of transcript in characters",
        example=1205,
        ge=0
    )


class TranscriptionResponse(BaseResponse):
    """Response model for successful audio transcription."""
    data: Dict[str, Any] = Field(
        ...,
        description="Transcription result data"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "File processed, saved, glossaries updated, candidates detected",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {
                    "filename": "spanish_news.mp3",
                    "transcript_preview": "En las últimas noticias económicas, la inflación ha alcanzado un 8.5% anual según reportes del instituto nacional de estadística...",
                    "stats": {
                        "economic_terms_found": 12,
                        "argentine_expressions_found": 3,
                        "new_candidates_detected": 5,
                        "processing_time_seconds": 1.8,
                        "transcript_length": 1205
                    },
                    "detected_terms": {
                        "economic": ["inflación", "PIB", "déficit", "reservas"],
                        "argentine": ["guita", "laburo", "bondi"]
                    }
                }
            }
        }


class GlossaryTerm(BaseModel):
    """Model for glossary terms."""
    id: int = Field(
        ...,
        description="Unique term identifier",
        example=1
    )
    term: str = Field(
        ...,
        description="The term or expression",
        example="inflación",
        min_length=1,
        max_length=200
    )
    definition: Optional[str] = Field(
        None,
        description="Term definition or meaning",
        example="Aumento generalizado y sostenido de precios en una economía",
        max_length=1000
    )
    category: Optional[str] = Field(
        None,
        description="Term category",
        example="macroeconomía",
        max_length=100
    )
    usage_count: int = Field(
        default=0,
        description="Number of times this term has been detected",
        example=47,
        ge=0
    )
    created_at: datetime = Field(
        ...,
        description="Term creation timestamp",
        example="2024-01-10T09:15:00Z"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Last update timestamp",
        example="2024-01-15T10:30:00Z"
    )


class ArgentineExpression(BaseModel):
    """Model for Argentine expressions."""
    id: int = Field(
        ...,
        description="Unique expression identifier",
        example=1
    )
    expression: str = Field(
        ...,
        description="The Argentine expression",
        example="guita",
        min_length=1,
        max_length=200
    )
    meaning: Optional[str] = Field(
        None,
        description="Expression meaning in standard Spanish",
        example="dinero",
        max_length=500
    )
    region: Optional[str] = Field(
        None,
        description="Regional usage area",
        example="rioplatense",
        max_length=100
    )
    usage_count: int = Field(
        default=0,
        description="Number of times this expression has been detected",
        example=15,
        ge=0
    )
    created_at: datetime = Field(
        ...,
        description="Expression creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Last update timestamp"
    )


class GlossariesResponse(BaseResponse):
    """Response model for glossaries endpoint."""
    data: Dict[str, List[Union[GlossaryTerm, ArgentineExpression]]] = Field(
        ...,
        description="Glossary data organized by type"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Glossaries retrieved successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {
                    "economic_glossary": [
                        {
                            "id": 1,
                            "term": "inflación",
                            "definition": "Aumento generalizado y sostenido de precios",
                            "category": "macroeconomía",
                            "usage_count": 47,
                            "created_at": "2024-01-10T09:15:00Z"
                        }
                    ],
                    "argentine_glossary": [
                        {
                            "id": 1,
                            "expression": "guita",
                            "meaning": "dinero",
                            "region": "rioplatense",
                            "usage_count": 15,
                            "created_at": "2024-01-12T14:20:00Z"
                        }
                    ]
                }
            }
        }


class CandidateTerm(BaseModel):
    """Model for candidate terms awaiting promotion."""
    id: int = Field(
        ...,
        description="Unique candidate identifier",
        example=1
    )
    term: str = Field(
        ...,
        description="The candidate term",
        example="monetización",
        min_length=1,
        max_length=200
    )
    detection_count: int = Field(
        ...,
        description="Number of times detected",
        example=5,
        ge=1
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score (0.0-1.0)",
        example=0.85,
        ge=0.0,
        le=1.0
    )
    contexts: List[str] = Field(
        ...,
        description="Context snippets where term was found",
        example=[
            "...proceso de monetización de la deuda...",
            "...estrategia de monetización del déficit..."
        ]
    )
    first_detected: datetime = Field(
        ...,
        description="First detection timestamp"
    )
    last_detected: datetime = Field(
        ...,
        description="Most recent detection timestamp"
    )


class CandidatesResponse(BaseResponse):
    """Response model for candidates endpoint."""
    data: Dict[str, Any] = Field(
        ...,
        description="Candidate terms and statistics"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Candidate terms retrieved successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {
                    "candidates": [
                        {
                            "id": 1,
                            "term": "monetización",
                            "detection_count": 5,
                            "confidence_score": 0.85,
                            "contexts": [
                                "...proceso de monetización de la deuda...",
                                "...estrategia de monetización del déficit..."
                            ],
                            "first_detected": "2024-01-14T08:30:00Z",
                            "last_detected": "2024-01-15T10:15:00Z"
                        }
                    ],
                    "stats": {
                        "total_candidates": 12,
                        "high_confidence": 3,
                        "recent_detections": 5
                    }
                }
            }
        }


class PromotionRequest(BaseModel):
    """Request model for promoting candidate terms."""
    term: str = Field(
        ...,
        description="Term to promote",
        example="monetización",
        min_length=1,
        max_length=200
    )
    glossary: str = Field(
        ...,
        description="Target glossary: 'economic' or 'argentine'",
        example="economic"
    )

    @validator('glossary')
    def validate_glossary(cls, v):
        if v not in ['economic', 'argentine']:
            raise ValueError("Glossary must be 'economic' or 'argentine'")
        return v

    class Config:
        schema_extra = {
            "example": {
                "term": "monetización",
                "glossary": "economic"
            }
        }


class PerformanceMetrics(BaseModel):
    """Model for API performance metrics."""
    total_requests: int = Field(
        ...,
        description="Total number of requests",
        example=15420,
        ge=0
    )
    error_rate: float = Field(
        ...,
        description="Error rate percentage",
        example=2.3,
        ge=0.0,
        le=100.0
    )
    avg_response_time: float = Field(
        ...,
        description="Average response time in seconds",
        example=0.245,
        gt=0
    )
    p95_response_time: float = Field(
        ...,
        description="95th percentile response time",
        example=0.850,
        gt=0
    )
    requests_per_minute: float = Field(
        ...,
        description="Average requests per minute",
        example=25.7,
        ge=0
    )


class MonitoringResponse(BaseResponse):
    """Response model for monitoring endpoints."""
    data: Dict[str, Any] = Field(
        ...,
        description="Monitoring data"
    )


class ErrorResponse(BaseResponse):
    """Response model for error cases."""
    status: ResponseStatus = ResponseStatus.ERROR
    error_code: Optional[str] = Field(
        None,
        description="Machine-readable error code",
        example="VALIDATION_ERROR"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "message": "Validation failed",
                "timestamp": "2024-01-15T10:30:00Z",
                "error_code": "VALIDATION_ERROR",
                "details": {
                    "field": "file",
                    "issue": "Only MP3 files are supported"
                }
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoints."""
    status: str = Field(
        ...,
        description="Health status",
        example="healthy"
    )
    version: str = Field(
        ...,
        description="API version",
        example="1.1.0"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Health check timestamp"
    )
    authenticated: bool = Field(
        ...,
        description="Whether request is authenticated",
        example=True
    )
    user: Optional[str] = Field(
        None,
        description="Current user if authenticated",
        example="john_doe"
    )
    role: Optional[str] = Field(
        None,
        description="User role if authenticated",
        example="user"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="System warnings",
        example=[]
    )
    metrics: Optional[Dict[str, Union[str, int, float]]] = Field(
        None,
        description="Basic system metrics"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.1.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "authenticated": True,
                "user": "john_doe",
                "role": "user",
                "warnings": [],
                "metrics": {
                    "uptime_hours": 24,
                    "error_rate": 1.2,
                    "avg_response_time": 0.245,
                    "active_users": 42
                }
            }
        }