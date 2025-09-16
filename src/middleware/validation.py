"""
Enhanced request validation middleware with security features.
"""
import re
import magic
import hashlib
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass
from fastapi import Request, HTTPException, status, UploadFile
from fastapi.responses import JSONResponse
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Request validation rule configuration."""
    max_size: Optional[int] = None
    allowed_content_types: Optional[List[str]] = None
    allowed_extensions: Optional[List[str]] = None
    max_files: Optional[int] = None
    required_fields: Optional[List[str]] = None
    forbidden_patterns: Optional[List[str]] = None


class SecurityValidator:
    """Enhanced security validation for requests and files."""

    def __init__(self):
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.max_filename_length = 255
        self.dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.msi', '.dll', '.sh', '.php', '.asp', '.jsp', '.py'
        }
        self.magic = magic.Magic(mime=True)

        # Malicious patterns for various attack types
        self.attack_patterns = {
            'sql_injection': [
                r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)",
                r"(?i)(exec\s*\(|sp_|xp_|cmdshell)",
                r"(?i)(\bor\b\s+\d+\s*=\s*\d+|\band\b\s+\d+\s*=\s*\d+)",
                r"(?i)(';\s*(drop|delete|insert|update|alter|create))",
            ],
            'xss': [
                r"(?i)(<script[^>]*>|</script>)",
                r"(?i)(javascript:|vbscript:|onload=|onerror=|onclick=)",
                r"(?i)(<iframe|<object|<embed|<link)",
                r"(?i)(expression\s*\(|@import|url\s*\()",
            ],
            'path_traversal': [
                r"(\.\./|\.\.\|\.\.%2f|\.\.%5c)",
                r"(%2e%2e%2f|%2e%2e%5c|%252e%252e%252f)",
                r"(\.\.\\|\.\.\/|\.\.%255c)",
            ],
            'command_injection': [
                r"(?i)(;|\||&|\$\(|\`|>\s*&|<\s*&)",
                r"(?i)(\bnc\b|\btelnet\b|\bssh\b|\bftp\b)",
                r"(?i)(\bwget\b|\bcurl\b|\bpowershell\b|\bbash\b)",
            ],
            'ldap_injection': [
                r"(\*\)|\|\)|&\)|\)\()",
                r"(\*\(|\|\(|&\(|\(\*)",
            ],
            'xml_injection': [
                r"(?i)(<!entity|<!element|<!attlist|<!notation)",
                r"(?i)(&\w+;|&#\d+;|&#x[0-9a-f]+;)",
            ]
        }

        # Content type validation
        self.content_type_rules = {
            '/upload': {
                'allowed': ['multipart/form-data'],
                'forbidden': ['text/html', 'application/javascript']
            },
            '/api/v1/auth': {
                'allowed': ['application/json'],
                'forbidden': ['multipart/form-data', 'text/html']
            }
        }

    def validate_filename(self, filename: str) -> tuple[bool, str]:
        """Validate uploaded filename for security."""
        if not filename:
            return False, "Empty filename"

        if len(filename) > self.max_filename_length:
            return False, f"Filename too long (max {self.max_filename_length} chars)"

        # Check for dangerous extensions
        lower_filename = filename.lower()
        for ext in self.dangerous_extensions:
            if lower_filename.endswith(ext):
                return False, f"Dangerous file extension: {ext}"

        # Check for directory traversal in filename
        if '..' in filename or '/' in filename or '\\' in filename:
            return False, "Invalid characters in filename"

        # Check for null bytes and control characters
        if '\x00' in filename or any(ord(c) < 32 for c in filename if c not in '\t\n\r'):
            return False, "Invalid characters in filename"

        return True, "Valid filename"

    def validate_file_content(self, file_content: bytes, expected_type: str = None) -> tuple[bool, str]:
        """Validate file content using magic numbers."""
        if not file_content:
            return False, "Empty file content"

        try:
            # Detect actual MIME type
            detected_type = self.magic.from_buffer(file_content)

            # Check for MP3 files specifically
            if expected_type == "audio/mpeg":
                if not detected_type.startswith('audio/'):
                    return False, f"File is not audio: {detected_type}"

                # Check for MP3 magic bytes
                if not (file_content.startswith(b'ID3') or
                       file_content.startswith(b'\xff\xfb') or
                       file_content.startswith(b'\xff\xf3') or
                       file_content.startswith(b'\xff\xf2')):
                    return False, "File does not appear to be a valid MP3"

            # Check for executable content in any file
            executable_types = [
                'application/x-executable',
                'application/x-msdos-program',
                'application/x-msdownload',
                'application/x-dosexec'
            ]

            if any(exec_type in detected_type for exec_type in executable_types):
                return False, f"Executable file detected: {detected_type}"

            # Check for script content
            script_patterns = [b'<?php', b'<script', b'#!/bin/', b'#!/usr/bin/']
            for pattern in script_patterns:
                if pattern in file_content[:1024]:  # Check first 1KB
                    return False, "Script content detected in file"

            return True, f"Valid file content: {detected_type}"

        except Exception as e:
            logger.error(f"Error validating file content: {e}")
            return False, "File content validation failed"

    def scan_for_attacks(self, content: str, attack_types: List[str] = None) -> Dict[str, List[str]]:
        """Scan content for various attack patterns."""
        if attack_types is None:
            attack_types = list(self.attack_patterns.keys())

        findings = {}

        for attack_type in attack_types:
            if attack_type not in self.attack_patterns:
                continue

            matches = []
            for pattern in self.attack_patterns[attack_type]:
                try:
                    if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                        matches.append(pattern)
                except re.error as e:
                    logger.error(f"Regex error in pattern {pattern}: {e}")

            if matches:
                findings[attack_type] = matches

        return findings

    def validate_json_structure(self, json_data: dict, max_depth: int = 10, max_keys: int = 100) -> tuple[bool, str]:
        """Validate JSON structure for security."""

        def count_depth(obj, current_depth=0):
            if current_depth > max_depth:
                return current_depth

            if isinstance(obj, dict):
                if len(obj) > max_keys:
                    return float('inf')  # Too many keys
                return max(count_depth(v, current_depth + 1) for v in obj.values()) if obj else current_depth
            elif isinstance(obj, list):
                if len(obj) > max_keys:
                    return float('inf')  # Too many items
                return max(count_depth(item, current_depth + 1) for item in obj) if obj else current_depth
            else:
                return current_depth

        try:
            depth = count_depth(json_data)

            if depth > max_depth:
                return False, f"JSON too deeply nested (max depth: {max_depth})"

            if depth == float('inf'):
                return False, f"Too many keys/items in JSON (max: {max_keys})"

            return True, "Valid JSON structure"

        except Exception as e:
            return False, f"JSON validation error: {e}"

    async def validate_request_headers(self, request: Request) -> tuple[bool, str]:
        """Validate request headers for security."""
        headers = request.headers

        # Check for suspicious user agents
        user_agent = headers.get('user-agent', '').lower()
        suspicious_agents = ['sqlmap', 'nikto', 'nmap', 'burp', 'zap']
        if any(agent in user_agent for agent in suspicious_agents):
            return False, "Suspicious user agent detected"

        # Check for unusual header combinations
        if 'x-forwarded-for' in headers and 'x-real-ip' in headers:
            xff_ips = headers['x-forwarded-for'].split(',')
            if len(xff_ips) > 10:  # Too many proxy hops
                return False, "Suspicious proxy chain detected"

        # Check for oversized headers
        for name, value in headers.items():
            if len(value) > 8192:  # 8KB limit per header
                return False, f"Header {name} too large"

        return True, "Valid headers"

    async def validate_upload_file(self, file: UploadFile) -> tuple[bool, str]:
        """Comprehensive file upload validation."""

        # Validate filename
        filename_valid, filename_msg = self.validate_filename(file.filename)
        if not filename_valid:
            return False, f"Filename validation failed: {filename_msg}"

        # Read file content (limit to avoid memory issues)
        max_read_size = 10 * 1024 * 1024  # 10MB for validation
        file_content = await file.read(max_read_size)

        # Reset file position
        await file.seek(0)

        # Validate file size
        if len(file_content) > self.max_file_size:
            return False, f"File too large (max {self.max_file_size // (1024*1024)}MB)"

        # Validate content type vs actual content
        expected_type = file.content_type or "audio/mpeg"
        content_valid, content_msg = self.validate_file_content(file_content, expected_type)
        if not content_valid:
            return False, f"Content validation failed: {content_msg}"

        return True, "File validation passed"


class RequestValidationMiddleware:
    """Main request validation middleware."""

    def __init__(self):
        self.security_validator = SecurityValidator()
        self.validation_rules = {}
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default validation rules."""

        # Upload endpoint rules
        self.validation_rules['/upload'] = ValidationRule(
            max_size=50 * 1024 * 1024,  # 50MB
            allowed_content_types=['multipart/form-data'],
            allowed_extensions=['.mp3'],
            max_files=1,
            required_fields=['file']
        )

        # Auth endpoint rules
        self.validation_rules['/api/v1/auth/login'] = ValidationRule(
            max_size=1024,  # 1KB
            allowed_content_types=['application/json'],
            required_fields=['username', 'password'],
            forbidden_patterns=['<script', 'javascript:']
        )

        self.validation_rules['/api/v1/auth/register'] = ValidationRule(
            max_size=2048,  # 2KB
            allowed_content_types=['application/json'],
            required_fields=['username', 'email', 'password'],
            forbidden_patterns=['<script', 'javascript:', 'drop table']
        )

    async def validate_request(self, request: Request) -> tuple[bool, str]:
        """Main request validation function."""

        # Validate headers
        headers_valid, headers_msg = await self.security_validator.validate_request_headers(request)
        if not headers_valid:
            return False, headers_msg

        # Get validation rules for this endpoint
        path = request.url.path
        rules = None

        # Find matching rule (exact match or prefix match)
        if path in self.validation_rules:
            rules = self.validation_rules[path]
        else:
            # Check for prefix matches
            for rule_path, rule in self.validation_rules.items():
                if path.startswith(rule_path.rstrip('*')):
                    rules = rule
                    break

        if not rules:
            return True, "No specific validation rules"

        # Validate content type
        content_type = request.headers.get('content-type', '')
        if rules.allowed_content_types:
            if not any(allowed in content_type for allowed in rules.allowed_content_types):
                return False, f"Invalid content type: {content_type}"

        # Validate request size
        content_length = request.headers.get('content-length')
        if content_length and rules.max_size:
            if int(content_length) > rules.max_size:
                return False, f"Request too large: {content_length} > {rules.max_size}"

        return True, "Request validation passed"

    async def validate_form_data(self, request: Request, rules: ValidationRule) -> tuple[bool, str]:
        """Validate multipart form data."""
        try:
            form = await request.form()

            # Check required fields
            if rules.required_fields:
                missing_fields = [field for field in rules.required_fields if field not in form]
                if missing_fields:
                    return False, f"Missing required fields: {missing_fields}"

            # Validate files
            file_count = 0
            for key, value in form.items():
                if hasattr(value, 'read'):  # It's a file
                    file_count += 1

                    if rules.max_files and file_count > rules.max_files:
                        return False, f"Too many files (max {rules.max_files})"

                    # Validate the file
                    file_valid, file_msg = await self.security_validator.validate_upload_file(value)
                    if not file_valid:
                        return False, file_msg

            return True, "Form data validation passed"

        except Exception as e:
            logger.error(f"Error validating form data: {e}")
            return False, "Form data validation failed"

    async def validate_json_data(self, request: Request, rules: ValidationRule) -> tuple[bool, str]:
        """Validate JSON request body."""
        try:
            body = await request.body()
            if not body:
                return True, "Empty JSON body"

            # Parse JSON
            json_data = json.loads(body)

            # Validate JSON structure
            structure_valid, structure_msg = self.security_validator.validate_json_structure(json_data)
            if not structure_valid:
                return False, structure_msg

            # Check required fields
            if rules.required_fields and isinstance(json_data, dict):
                missing_fields = [field for field in rules.required_fields if field not in json_data]
                if missing_fields:
                    return False, f"Missing required fields: {missing_fields}"

            # Scan for attack patterns
            json_str = json.dumps(json_data)
            if rules.forbidden_patterns:
                for pattern in rules.forbidden_patterns:
                    if re.search(pattern, json_str, re.IGNORECASE):
                        return False, f"Forbidden pattern detected: {pattern}"

            # Full security scan
            attack_findings = self.security_validator.scan_for_attacks(json_str)
            if attack_findings:
                return False, f"Security violations detected: {list(attack_findings.keys())}"

            return True, "JSON validation passed"

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            logger.error(f"Error validating JSON: {e}")
            return False, "JSON validation failed"


# Global validator instance
request_validator = RequestValidationMiddleware()


async def validation_middleware(request: Request, call_next):
    """Request validation middleware for FastAPI."""

    # Skip validation for certain endpoints
    skip_paths = ['/health', '/docs', '/openapi.json', '/redoc']
    if request.url.path in skip_paths:
        return await call_next(request)

    # Validate request
    valid, message = await request_validator.validate_request(request)
    if not valid:
        logger.warning(f"Request validation failed for {request.url.path}: {message}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": "Request validation failed",
                "error": message
            }
        )

    # Process the request
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )