"""
API examples and guides endpoints for developer assistance.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/examples", tags=["API Examples & Guides"])


@router.get("/quick-start")
async def get_quick_start_guide():
    """Get a quick start guide for using the API."""
    return {
        "title": "Spanish Transcription API - Quick Start Guide",
        "description": "Get up and running with the Spanish Audio Transcription API in minutes",
        "steps": [
            {
                "step": 1,
                "title": "Register an Account",
                "description": "Create a user account to get started",
                "endpoint": "POST /api/v1/auth/register",
                "example": {
                    "curl": """curl -X POST "http://localhost:8000/api/v1/auth/register" \\
     -H "Content-Type: application/json" \\
     -d '{
       "username": "your_username",
       "email": "your_email@example.com",
       "password": "SecurePassword123!",
       "full_name": "Your Full Name"
     }'""",
                    "python": """
import requests

response = requests.post(
    "http://localhost:8000/api/v1/auth/register",
    json={
        "username": "your_username",
        "email": "your_email@example.com",
        "password": "SecurePassword123!",
        "full_name": "Your Full Name"
    }
)
print(response.json())
"""
                }
            },
            {
                "step": 2,
                "title": "Authenticate",
                "description": "Login to get your access token",
                "endpoint": "POST /api/v1/auth/login",
                "example": {
                    "curl": """curl -X POST "http://localhost:8000/api/v1/auth/login" \\
     -H "Content-Type: application/json" \\
     -d '{
       "username": "your_username",
       "password": "SecurePassword123!"
     }'""",
                    "python": """
import requests

response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={
        "username": "your_username",
        "password": "SecurePassword123!"
    }
)
token_data = response.json()
access_token = token_data["access_token"]
"""
                }
            },
            {
                "step": 3,
                "title": "Upload Audio File",
                "description": "Upload an MP3 file for transcription",
                "endpoint": "POST /api/v1/upload",
                "example": {
                    "curl": """curl -X POST "http://localhost:8000/api/v1/upload" \\
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
     -F "file=@spanish_audio.mp3" """,
                    "python": """
import requests

headers = {"Authorization": f"Bearer {access_token}"}
files = {"file": ("spanish_audio.mp3", open("spanish_audio.mp3", "rb"), "audio/mpeg")}

response = requests.post(
    "http://localhost:8000/api/v1/upload",
    headers=headers,
    files=files
)
result = response.json()
print(f"Transcript: {result['transcript_preview']}")
"""
                }
            },
            {
                "step": 4,
                "title": "View Results",
                "description": "Check glossaries and candidate terms",
                "endpoint": "GET /api/v1/glossaries",
                "example": {
                    "curl": """curl -X GET "http://localhost:8000/api/v1/glossaries" \\
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" """,
                    "python": """
# Get glossaries
response = requests.get(
    "http://localhost:8000/api/v1/glossaries",
    headers=headers
)
glossaries = response.json()

# Get candidate terms
response = requests.get(
    "http://localhost:8000/api/v1/candidates",
    headers=headers
)
candidates = response.json()
"""
                }
            }
        ],
        "next_steps": [
            "Explore monitoring endpoints for usage analytics",
            "Set up API key authentication for automated access",
            "Configure rate limiting settings for your use case",
            "Review the full API documentation at /docs"
        ]
    }


@router.get("/authentication")
async def get_authentication_examples():
    """Get detailed authentication examples and patterns."""
    return {
        "title": "Authentication Guide",
        "description": "Complete guide to authenticating with the Spanish Transcription API",
        "methods": [
            {
                "name": "JWT Token Authentication",
                "description": "Standard JWT-based authentication for web applications",
                "flow": [
                    "Register user account",
                    "Login to get access and refresh tokens",
                    "Include access token in Authorization header",
                    "Refresh token when access token expires"
                ],
                "examples": {
                    "login": {
                        "curl": """curl -X POST "http://localhost:8000/api/v1/auth/login" \\
     -H "Content-Type: application/json" \\
     -d '{
       "username": "user@example.com",
       "password": "SecurePassword123!"
     }'""",
                        "response": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                            "refresh_expires_in": 604800
                        }
                    },
                    "authenticated_request": {
                        "curl": """curl -X GET "http://localhost:8000/api/v1/glossaries" \\
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." """,
                        "python": """
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}
response = requests.get("http://localhost:8000/api/v1/glossaries", headers=headers)
"""
                    },
                    "refresh_token": {
                        "curl": """curl -X POST "http://localhost:8000/api/v1/auth/refresh" \\
     -H "Content-Type: application/json" \\
     -d '{
       "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
     }'"""
                    }
                }
            },
            {
                "name": "API Key Authentication",
                "description": "API key authentication for server-to-server communication",
                "flow": [
                    "Login with username/password",
                    "Generate API key via /api/v1/auth/api-key",
                    "Use API key in X-API-Key header",
                    "Revoke API key when no longer needed"
                ],
                "examples": {
                    "generate_api_key": {
                        "curl": """curl -X POST "http://localhost:8000/api/v1/auth/api-key" \\
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" """,
                        "response": {
                            "api_key": "sk_live_abc123def456...",
                            "message": "API key created successfully. Store it securely - it won't be shown again."
                        }
                    },
                    "use_api_key": {
                        "curl": """curl -X GET "http://localhost:8000/api/v1/glossaries" \\
     -H "X-API-Key: sk_live_abc123def456..." """,
                        "python": """
headers = {
    "X-API-Key": "sk_live_abc123def456...",
    "Content-Type": "application/json"
}
response = requests.get("http://localhost:8000/api/v1/glossaries", headers=headers)
"""
                    }
                }
            }
        ],
        "security_notes": [
            "Always use HTTPS in production",
            "Store tokens securely (environment variables, key management systems)",
            "Implement token refresh logic for long-running applications",
            "Revoke API keys when they're no longer needed",
            "Monitor authentication failures for security alerts"
        ]
    }


@router.get("/file-upload")
async def get_file_upload_examples():
    """Get file upload examples and best practices."""
    return {
        "title": "File Upload Guide",
        "description": "How to upload audio files for transcription",
        "requirements": {
            "file_format": "MP3 only",
            "max_file_size": "50 MB",
            "content_type": "audio/mpeg",
            "authentication": "JWT token or API key required"
        },
        "examples": [
            {
                "language": "curl",
                "description": "Basic file upload with curl",
                "code": """curl -X POST "http://localhost:8000/api/v1/upload" \\
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
     -F "file=@spanish_audio.mp3" """
            },
            {
                "language": "python",
                "description": "File upload with Python requests",
                "code": """
import requests

# Authentication
headers = {"Authorization": "Bearer YOUR_ACCESS_TOKEN"}

# File upload
with open("spanish_audio.mp3", "rb") as audio_file:
    files = {"file": ("spanish_audio.mp3", audio_file, "audio/mpeg")}
    response = requests.post(
        "http://localhost:8000/api/v1/upload",
        headers=headers,
        files=files
    )

result = response.json()
print(f"Transcript: {result['transcript_preview']}")
print(f"Stats: {result['stats']}")
"""
            },
            {
                "language": "javascript",
                "description": "File upload with JavaScript fetch",
                "code": """
const uploadAudio = async (audioFile, accessToken) => {
    const formData = new FormData();
    formData.append('file', audioFile);

    const response = await fetch('http://localhost:8000/api/v1/upload', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`
        },
        body: formData
    });

    const result = await response.json();
    return result;
};

// Usage
const fileInput = document.getElementById('audio-file');
const file = fileInput.files[0];
const result = await uploadAudio(file, 'YOUR_ACCESS_TOKEN');
"""
            }
        ],
        "response_format": {
            "description": "Successful upload response format",
            "example": {
                "filename": "spanish_news.mp3",
                "transcript_preview": "En las últimas noticias económicas, la inflación ha alcanzado...",
                "message": "File processed, saved, glossaries updated, candidates detected",
                "stats": {
                    "economic_terms_found": 12,
                    "argentine_expressions_found": 3,
                    "new_candidates_detected": 5,
                    "processing_time_seconds": 1.8
                }
            }
        },
        "error_handling": [
            {
                "status_code": 400,
                "description": "Invalid file format or validation error",
                "example": {
                    "detail": "Only .mp3 files are supported"
                }
            },
            {
                "status_code": 413,
                "description": "File too large",
                "example": {
                    "detail": "Request too large"
                }
            },
            {
                "status_code": 429,
                "description": "Rate limit exceeded",
                "example": {
                    "detail": "Upload rate limit exceeded. Try again later.",
                    "retry_after": 3600
                }
            }
        ]
    }


@router.get("/rate-limits")
async def get_rate_limit_info():
    """Get information about API rate limits."""
    return {
        "title": "Rate Limiting Guide",
        "description": "Understanding API rate limits and how to handle them",
        "rate_limits": [
            {
                "category": "General API",
                "limit": "100 requests per hour per user",
                "scope": "Per authenticated user",
                "endpoints": "All authenticated endpoints except uploads"
            },
            {
                "category": "File Upload",
                "limit": "10 uploads per hour per user",
                "scope": "Per authenticated user",
                "endpoints": "/api/v1/upload"
            },
            {
                "category": "Authentication",
                "limit": "5 attempts per 5 minutes",
                "scope": "Per IP address",
                "endpoints": "/api/v1/auth/login, /api/v1/auth/register"
            },
            {
                "category": "Global IP Limit",
                "limit": "1000 requests per hour",
                "scope": "Per IP address",
                "endpoints": "All endpoints"
            }
        ],
        "headers": {
            "description": "Rate limit headers included in responses",
            "examples": {
                "X-RateLimit-Limit-user_general": "100",
                "X-RateLimit-Remaining-user_general": "87",
                "X-RateLimit-Reset-user_general": "1705312200",
                "X-RateLimit-Limit-upload": "10",
                "X-RateLimit-Remaining-upload": "8"
            }
        },
        "handling_rate_limits": {
            "detection": "HTTP 429 status code with Retry-After header",
            "retry_strategy": "Exponential backoff with jitter",
            "example_response": {
                "status_code": 429,
                "headers": {
                    "Retry-After": "3600"
                },
                "body": {
                    "detail": "Rate limit exceeded. Try again later.",
                    "retry_after": 3600
                }
            },
            "python_example": """
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session_with_retries():
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

def make_request_with_rate_limit_handling(url, headers):
    session = create_session_with_retries()

    try:
        response = session.get(url, headers=headers)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            return make_request_with_rate_limit_handling(url, headers)

        return response
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
"""
        }
    }


@router.get("/error-handling")
async def get_error_handling_guide():
    """Get comprehensive error handling guide."""
    return {
        "title": "Error Handling Guide",
        "description": "How to handle errors and exceptions in the API",
        "status_codes": [
            {
                "code": 200,
                "name": "OK",
                "description": "Request successful",
                "action": "Process response data normally"
            },
            {
                "code": 400,
                "name": "Bad Request",
                "description": "Invalid request data or validation error",
                "action": "Check request format and fix validation errors",
                "example": {
                    "detail": "Validation failed",
                    "errors": [
                        {"field": "password", "message": "Password must be at least 8 characters"}
                    ]
                }
            },
            {
                "code": 401,
                "name": "Unauthorized",
                "description": "Authentication required or token invalid",
                "action": "Provide valid authentication credentials",
                "example": {
                    "detail": "Could not validate credentials"
                }
            },
            {
                "code": 403,
                "name": "Forbidden",
                "description": "Insufficient permissions",
                "action": "Check user role and permissions",
                "example": {
                    "detail": "Admin access required"
                }
            },
            {
                "code": 404,
                "name": "Not Found",
                "description": "Resource not found",
                "action": "Check resource identifier",
                "example": {
                    "detail": "Candidate term not found"
                }
            },
            {
                "code": 429,
                "name": "Too Many Requests",
                "description": "Rate limit exceeded",
                "action": "Wait and retry after specified time",
                "example": {
                    "detail": "Rate limit exceeded. Try again later.",
                    "retry_after": 3600
                }
            },
            {
                "code": 500,
                "name": "Internal Server Error",
                "description": "Server error",
                "action": "Retry request or contact support",
                "example": {
                    "detail": "Internal server error"
                }
            }
        ],
        "best_practices": [
            "Always check HTTP status codes before processing response",
            "Implement retry logic for transient errors (5xx, 429)",
            "Log errors with sufficient detail for debugging",
            "Handle authentication errors by refreshing tokens",
            "Validate request data before sending to avoid 400 errors",
            "Monitor error rates and patterns for system health"
        ],
        "python_example": """
import requests
import time
import logging

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, base_url, access_token):
        self.base_url = base_url
        self.access_token = access_token

    def make_request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f"Bearer {self.access_token}"

        try:
            response = requests.request(method, url, headers=headers, **kwargs)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("Authentication failed - token may be expired")
                raise AuthenticationError("Invalid or expired token")
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited - waiting {retry_after} seconds")
                time.sleep(retry_after)
                return self.make_request(method, endpoint, **kwargs)
            elif response.status_code >= 500:
                logger.error(f"Server error: {response.status_code}")
                raise ServerError(f"Server error: {response.status_code}")
            else:
                error_data = response.json() if response.content else {}
                logger.error(f"API error: {response.status_code} - {error_data}")
                raise APIError(f"API error: {response.status_code}", error_data)

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise NetworkError(f"Network error: {e}")

class APIError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details

class AuthenticationError(APIError):
    pass

class ServerError(APIError):
    pass

class NetworkError(APIError):
    pass
"""
    }


@router.get("/sdks")
async def get_sdk_information():
    """Get information about available SDKs and client libraries."""
    return {
        "title": "SDKs and Client Libraries",
        "description": "Available SDKs and example implementations for different programming languages",
        "official_sdks": [
            {
                "language": "Python",
                "status": "Available",
                "description": "Full-featured Python SDK with async support",
                "installation": "pip install spanish-transcription-sdk",
                "repository": "https://github.com/betolauda/spanish-transcription-python-sdk",
                "example": """
from spanish_transcription import TranscriptionClient

client = TranscriptionClient(
    api_key="your-api-key",
    base_url="http://localhost:8000"
)

# Upload and transcribe
result = await client.transcribe_file("audio.mp3")
print(result.transcript)

# Get glossaries
glossaries = await client.get_glossaries()
"""
            }
        ],
        "community_sdks": [
            {
                "language": "JavaScript/Node.js",
                "status": "Community Maintained",
                "description": "Unofficial JavaScript/Node.js client",
                "installation": "npm install spanish-transcription-js",
                "example": """
const TranscriptionClient = require('spanish-transcription-js');

const client = new TranscriptionClient({
    apiKey: 'your-api-key',
    baseURL: 'http://localhost:8000'
});

// Upload file
const result = await client.uploadFile('audio.mp3');
console.log(result.transcript);
"""
            },
            {
                "language": "Go",
                "status": "Community Maintained",
                "description": "Go client library",
                "installation": "go get github.com/user/spanish-transcription-go",
                "example": """
package main

import (
    "github.com/user/spanish-transcription-go"
)

func main() {
    client := transcription.NewClient("your-api-key")

    result, err := client.TranscribeFile("audio.mp3")
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(result.Transcript)
}
"""
            }
        ],
        "diy_implementation": {
            "description": "Basic implementation guide for custom clients",
            "steps": [
                "Implement authentication (JWT or API key)",
                "Handle rate limiting and retries",
                "Implement file upload with proper headers",
                "Parse JSON responses",
                "Handle errors appropriately"
            ],
            "minimal_example": """
class BasicTranscriptionClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url

    def upload_file(self, file_path):
        headers = {'X-API-Key': self.api_key}
        files = {'file': open(file_path, 'rb')}

        response = requests.post(
            f'{self.base_url}/api/v1/upload',
            headers=headers,
            files=files
        )

        return response.json()
"""
        }
    }


@router.get("/integration-patterns")
async def get_integration_patterns():
    """Get common integration patterns and architectures."""
    return {
        "title": "Integration Patterns",
        "description": "Common patterns for integrating the Spanish Transcription API",
        "patterns": [
            {
                "name": "Batch Processing",
                "description": "Process multiple audio files in batches",
                "use_case": "Transcribe large volumes of audio files offline",
                "implementation": """
import asyncio
import aiohttp
from pathlib import Path

async def batch_transcribe(file_paths, api_key, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def transcribe_file(session, file_path):
        async with semaphore:
            headers = {'X-API-Key': api_key}
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename=file_path.name)

            async with session.post('/api/v1/upload', headers=headers, data=data) as response:
                return await response.json()

    async with aiohttp.ClientSession(base_url='http://localhost:8000') as session:
        tasks = [transcribe_file(session, Path(fp)) for fp in file_paths]
        results = await asyncio.gather(*tasks)
        return results

# Usage
file_paths = ['audio1.mp3', 'audio2.mp3', 'audio3.mp3']
results = asyncio.run(batch_transcribe(file_paths, 'your-api-key'))
"""
            },
            {
                "name": "Webhook Integration",
                "description": "Process transcriptions asynchronously with webhooks",
                "use_case": "Real-time processing with status updates",
                "implementation": """
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/webhook/transcription', methods=['POST'])
def handle_transcription_webhook():
    data = request.json

    # Process transcription result
    transcript = data.get('transcript')
    filename = data.get('filename')
    stats = data.get('stats', {})

    # Store in database or trigger downstream processing
    process_transcription_result(transcript, filename, stats)

    return jsonify({'status': 'received'})

def submit_for_transcription(file_path, webhook_url):
    headers = {'X-API-Key': 'your-api-key'}
    files = {'file': open(file_path, 'rb')}
    data = {'webhook_url': webhook_url}

    response = requests.post(
        'http://localhost:8000/api/v1/upload',
        headers=headers,
        files=files,
        data=data
    )

    return response.json()
"""
            },
            {
                "name": "Stream Processing",
                "description": "Real-time processing of audio streams",
                "use_case": "Live transcription of audio streams",
                "implementation": """
import asyncio
import websockets
import json

async def stream_transcription(websocket, audio_stream):
    # Connect to transcription service
    async with websockets.connect('ws://localhost:8000/ws/transcribe') as ws:
        # Send authentication
        auth_msg = {
            'type': 'auth',
            'token': 'your-jwt-token'
        }
        await ws.send(json.dumps(auth_msg))

        # Stream audio chunks
        async for audio_chunk in audio_stream:
            msg = {
                'type': 'audio_chunk',
                'data': audio_chunk.hex()
            }
            await ws.send(json.dumps(msg))

            # Receive partial transcription
            response = await ws.recv()
            data = json.loads(response)

            if data['type'] == 'partial_transcript':
                yield data['transcript']
"""
            }
        ]
    }