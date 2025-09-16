"""
Enhanced API documentation and OpenAPI configuration.

This module provides comprehensive API documentation with examples,
detailed schemas, and enhanced metadata for better developer experience.
"""
from typing import Dict, Any, List
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse
import json


def get_custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced metadata."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Spanish Audio Transcription API",
        version="1.1.0",
        description=get_api_description(),
        routes=app.routes,
        tags=get_openapi_tags(),
        servers=get_openapi_servers()
    )

    # Add custom extensions
    openapi_schema["info"]["contact"] = {
        "name": "API Support",
        "email": "support@transcription.local",
        "url": "https://github.com/betolauda/transcrip-app"
    }

    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }

    # Add custom components
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /api/v1/auth/login"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for programmatic access"
        }
    }

    # Add examples
    add_request_examples(openapi_schema)

    # Add response examples
    add_response_examples(openapi_schema)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def get_api_description() -> str:
    """Get comprehensive API description."""
    return """
## Spanish Audio Transcription API

A professional-grade API for Spanish audio transcription with advanced features including:

### 🎯 Core Features
- **Spanish Audio Transcription**: High-quality speech-to-text using OpenAI Whisper
- **Economic Term Detection**: Specialized recognition of economic vocabulary
- **Argentine Expression Recognition**: Detection of Argentine Spanish expressions
- **Glossary Management**: Dynamic glossary updates and term promotion
- **User Authentication**: JWT-based authentication with role-based access control

### 🔒 Security Features
- **Rate Limiting**: Advanced token bucket rate limiting with IP-based protection
- **Request Validation**: Comprehensive security scanning for XSS, SQLi, and other attacks
- **File Security**: MIME type validation and malicious content detection
- **API Monitoring**: Real-time monitoring with security event tracking

### 📊 Analytics & Monitoring
- **Performance Metrics**: Detailed API performance and usage analytics
- **User Behavior Tracking**: User activity and endpoint usage statistics
- **Security Events**: Comprehensive security event logging and alerting
- **Database Management**: Migration system with integrity validation

### 🚀 Getting Started

1. **Register a User Account**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/register" \\
        -H "Content-Type: application/json" \\
        -d '{
          "username": "your_username",
          "email": "your_email@example.com",
          "password": "SecurePassword123!",
          "full_name": "Your Full Name"
        }'
   ```

2. **Authenticate and Get Token**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \\
        -H "Content-Type: application/json" \\
        -d '{
          "username": "your_username",
          "password": "SecurePassword123!"
        }'
   ```

3. **Upload Audio File**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/upload" \\
        -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
        -F "file=@audio_file.mp3"
   ```

### 📚 API Endpoints

#### Authentication & User Management
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Authenticate user
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/api-key` - Generate API key

#### Transcription & Processing
- `POST /api/v1/upload` - Upload and transcribe audio
- `GET /api/v1/glossaries` - Get glossary terms
- `GET /api/v1/candidates` - Get candidate terms
- `POST /api/v1/promote` - Promote candidate terms

#### Monitoring & Analytics (Admin)
- `GET /api/v1/monitoring/stats/performance` - Performance metrics
- `GET /api/v1/monitoring/stats/users` - User analytics
- `GET /api/v1/monitoring/dashboard` - Monitoring dashboard

#### Database Management (Admin)
- `GET /api/v1/database/migration-status` - Migration status
- `POST /api/v1/database/migrate` - Apply migrations
- `GET /api/v1/database/backup` - Create database backup

### 🏗️ Technical Architecture

- **Framework**: FastAPI with async/await support
- **Authentication**: JWT tokens with refresh token support
- **Database**: SQLite with migration system
- **Speech Recognition**: OpenAI Whisper (Spanish optimized)
- **Rate Limiting**: Token bucket algorithm with sliding window
- **Monitoring**: Real-time metrics collection and analytics

### 📈 Rate Limits

- **General API**: 100 requests/hour per user
- **File Upload**: 10 uploads/hour per user
- **Authentication**: 5 attempts/5 minutes per IP
- **Global**: 1000 requests/hour per IP

### 🛡️ Security

- **JWT Authentication**: Secure token-based authentication
- **API Key Support**: For programmatic access
- **Rate Limiting**: Multi-layer protection against abuse
- **Request Validation**: XSS, SQLi, and injection protection
- **File Security**: MIME validation and content scanning
- **HTTPS Only**: All endpoints require HTTPS in production

### 📄 Response Format

All API responses follow a consistent format:

```json
{
  "status": "success|error",
  "data": { ... },
  "message": "Human readable message",
  "timestamp": "ISO 8601 timestamp"
}
```

### ⚠️ Error Handling

Standard HTTP status codes are used:
- `200` - Success
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

### 🔧 Development

For development and testing:
- Interactive API docs: `/docs`
- Alternative docs: `/redoc`
- OpenAPI schema: `/openapi.json`
"""


def get_openapi_tags() -> List[Dict[str, Any]]:
    """Get OpenAPI tags with descriptions."""
    return [
        {
            "name": "Authentication",
            "description": "User authentication and authorization endpoints. Handle user registration, login, profile management, and API key generation."
        },
        {
            "name": "Transcription",
            "description": "Audio transcription and processing endpoints. Upload MP3 files for Spanish transcription with economic term detection."
        },
        {
            "name": "Glossary Management",
            "description": "Manage economic terms and Argentine expressions. View glossaries, promote candidate terms, and track usage."
        },
        {
            "name": "Monitoring & Analytics",
            "description": "API monitoring, performance metrics, and usage analytics. Admin-only endpoints for system monitoring."
        },
        {
            "name": "Database Management",
            "description": "Database administration endpoints. Manage migrations, backups, and schema operations. Admin-only access."
        },
        {
            "name": "Health & Status",
            "description": "System health checks and status endpoints. Public endpoints for service availability monitoring."
        }
    ]


def get_openapi_servers() -> List[Dict[str, Any]]:
    """Get OpenAPI server configurations."""
    return [
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.transcription.local",
            "description": "Production server"
        }
    ]


def add_request_examples(openapi_schema: Dict[str, Any]) -> None:
    """Add request examples to OpenAPI schema."""

    # User registration example
    if "paths" in openapi_schema and "/api/v1/auth/register" in openapi_schema["paths"]:
        openapi_schema["paths"]["/api/v1/auth/register"]["post"]["requestBody"]["content"]["application/json"]["examples"] = {
            "user_registration": {
                "summary": "User Registration Example",
                "description": "Example of registering a new user account",
                "value": {
                    "username": "john_doe",
                    "email": "john.doe@example.com",
                    "password": "SecurePassword123!",
                    "full_name": "John Doe",
                    "role": "user"
                }
            },
            "admin_registration": {
                "summary": "Admin Registration Example",
                "description": "Example of registering an admin user",
                "value": {
                    "username": "admin_user",
                    "email": "admin@company.com",
                    "password": "AdminPassword456!",
                    "full_name": "System Administrator",
                    "role": "admin"
                }
            }
        }

    # Login example
    if "paths" in openapi_schema and "/api/v1/auth/login" in openapi_schema["paths"]:
        openapi_schema["paths"]["/api/v1/auth/login"]["post"]["requestBody"]["content"]["application/json"]["examples"] = {
            "user_login": {
                "summary": "User Login Example",
                "description": "Example of user authentication",
                "value": {
                    "username": "john_doe",
                    "password": "SecurePassword123!"
                }
            },
            "email_login": {
                "summary": "Email Login Example",
                "description": "Login using email instead of username",
                "value": {
                    "username": "john.doe@example.com",
                    "password": "SecurePassword123!"
                }
            }
        }


def add_response_examples(openapi_schema: Dict[str, Any]) -> None:
    """Add response examples to OpenAPI schema."""

    # Authentication response examples
    auth_token_example = {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800,
        "refresh_expires_in": 604800
    }

    # Upload response example
    upload_response_example = {
        "filename": "spanish_news.mp3",
        "transcript_preview": "En las últimas noticias económicas, la inflación ha alcanzado un 8.5% anual...",
        "message": "File processed, saved, glossaries updated, candidates detected",
        "stats": {
            "economic_terms_found": 12,
            "argentine_expressions_found": 3,
            "new_candidates_detected": 5,
            "processing_time_seconds": 1.8
        }
    }

    # Glossary response example
    glossary_response_example = {
        "economic_glossary": [
            {
                "id": 1,
                "term": "inflación",
                "definition": "Aumento generalizado y sostenido de precios",
                "category": "macroeconomía",
                "usage_count": 47
            },
            {
                "id": 2,
                "term": "PIB",
                "definition": "Producto Interno Bruto",
                "category": "indicadores",
                "usage_count": 23
            }
        ],
        "argentine_glossary": [
            {
                "id": 1,
                "expression": "guita",
                "meaning": "dinero",
                "region": "rioplatense",
                "usage_count": 15
            }
        ]
    }

    # Error response examples
    error_examples = {
        "validation_error": {
            "summary": "Validation Error",
            "value": {
                "detail": "Validation failed",
                "errors": [
                    {
                        "field": "password",
                        "message": "Password must be at least 8 characters"
                    }
                ]
            }
        },
        "authentication_error": {
            "summary": "Authentication Error",
            "value": {
                "detail": "Could not validate credentials"
            }
        },
        "rate_limit_error": {
            "summary": "Rate Limit Error",
            "value": {
                "detail": "Rate limit exceeded. Try again later.",
                "retry_after": 3600
            }
        }
    }

    # Add examples to schema components
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    if "examples" not in openapi_schema["components"]:
        openapi_schema["components"]["examples"] = {}

    openapi_schema["components"]["examples"].update({
        "AuthTokenResponse": {
            "summary": "Authentication Token Response",
            "value": auth_token_example
        },
        "UploadResponse": {
            "summary": "File Upload Response",
            "value": upload_response_example
        },
        "GlossaryResponse": {
            "summary": "Glossary Data Response",
            "value": glossary_response_example
        },
        "ValidationError": error_examples["validation_error"],
        "AuthenticationError": error_examples["authentication_error"],
        "RateLimitError": error_examples["rate_limit_error"]
    })


def get_custom_swagger_ui_html(
    openapi_url: str = "/openapi.json",
    title: str = "Spanish Audio Transcription API",
    swagger_js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
    swagger_css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
) -> HTMLResponse:
    """Generate custom Swagger UI with enhanced styling."""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <link rel="stylesheet" type="text/css" href="{swagger_css_url}">
        <link rel="icon" type="image/png" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==">
        <style>
            .swagger-ui .topbar {{ display: none; }}
            .swagger-ui .info .title {{ color: #3b82f6; }}
            .swagger-ui .info .description {{ font-size: 14px; line-height: 1.6; }}
            .swagger-ui .scheme-container {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .swagger-ui .auth-wrapper {{ margin-top: 20px; }}
            .custom-header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                text-align: center;
                margin-bottom: 20px;
            }}
            .custom-header h1 {{ margin: 0; font-size: 24px; }}
            .custom-header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        </style>
    </head>
    <body>
        <div id="swagger-ui">
            <div class="custom-header">
                <h1>🎙️ Spanish Audio Transcription API</h1>
                <p>Professional-grade Spanish audio transcription with economic term detection</p>
            </div>
        </div>
        <script src="{swagger_js_url}"></script>
        <script>
            const ui = SwaggerUIBundle({{
                url: '{openapi_url}',
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.presets.standalone
                ],
                layout: "BaseLayout",
                deepLinking: true,
                showExtensions: true,
                showCommonExtensions: true,
                tryItOutEnabled: true,
                requestInterceptor: function(request) {{
                    // Add custom headers or modify requests
                    request.headers['X-API-Client'] = 'swagger-ui';
                    return request;
                }},
                responseInterceptor: function(response) {{
                    // Handle responses
                    return response;
                }},
                onComplete: function() {{
                    // Add custom JavaScript after UI loads
                    console.log('Spanish Transcription API Documentation Loaded');
                }}
            }});

            // Add keyboard shortcuts
            document.addEventListener('keydown', function(e) {{
                if (e.ctrlKey && e.key === '/') {{
                    e.preventDefault();
                    // Focus on search/filter
                    const searchInput = document.querySelector('.swagger-ui input[placeholder*="Filter"]');
                    if (searchInput) searchInput.focus();
                }}
            }});
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


def get_custom_redoc_html(
    openapi_url: str = "/openapi.json",
    title: str = "Spanish Audio Transcription API",
    redoc_js_url: str = "https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
) -> HTMLResponse:
    """Generate custom ReDoc documentation."""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body {{ margin: 0; padding: 0; }}
            .custom-header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .custom-header h1 {{ margin: 0; font-size: 28px; font-weight: 300; }}
            .custom-header p {{ margin: 15px 0 0 0; opacity: 0.9; font-size: 16px; }}
            #redoc-container {{ margin-top: 0; }}
        </style>
    </head>
    <body>
        <div class="custom-header">
            <h1>🎙️ Spanish Audio Transcription API</h1>
            <p>Comprehensive API documentation for professional Spanish audio transcription</p>
        </div>
        <div id="redoc-container"></div>
        <script src="{redoc_js_url}"></script>
        <script>
            Redoc.init('{openapi_url}', {{
                theme: {{
                    colors: {{
                        primary: {{
                            main: '#667eea'
                        }}
                    }},
                    typography: {{
                        fontSize: '14px',
                        fontFamily: 'Roboto, sans-serif',
                        headings: {{
                            fontFamily: 'Montserrat, sans-serif'
                        }}
                    }}
                }},
                scrollYOffset: 0,
                hideDownloadButton: false,
                disableSearch: false,
                expandResponses: 'all',
                pathInMiddlePanel: true,
                untrustedSpec: false
            }}, document.getElementById('redoc-container'));
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)