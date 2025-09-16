"""
Advanced rate limiting middleware for API protection.
"""
import time
import json
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    requests: int  # Max requests
    window: int    # Time window in seconds
    key_func: Optional[str] = None  # Key function for grouping requests
    skip_successful: bool = False   # Skip counting successful requests
    skip_failed: bool = False       # Skip counting failed requests


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    last_refill: float
    requests: deque = field(default_factory=deque)


class AdvancedRateLimiter:
    """
    Advanced rate limiter with multiple algorithms and features:
    - Token bucket algorithm for smooth rate limiting
    - Sliding window for precise control
    - IP-based and user-based limiting
    - Configurable rules per endpoint
    - Request size validation
    - Automatic cleanup of old entries
    """

    def __init__(self):
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.rules: Dict[str, List[RateLimitRule]] = {}
        self.blocked_ips: Dict[str, float] = {}  # IP -> unblock_time
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)

        # Default rules
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default rate limiting rules."""
        # Global IP-based limits
        self.add_rule("global_ip", RateLimitRule(
            requests=1000,
            window=3600,  # 1000 requests per hour per IP
            key_func="ip"
        ))

        # User-based limits
        self.add_rule("user_general", RateLimitRule(
            requests=100,
            window=3600,  # 100 requests per hour per user
            key_func="user"
        ))

        # Upload endpoint specific limits
        self.add_rule("upload", RateLimitRule(
            requests=10,
            window=3600,  # 10 uploads per hour
            key_func="user"
        ))

        # Authentication endpoints
        self.add_rule("auth", RateLimitRule(
            requests=5,
            window=300,  # 5 auth attempts per 5 minutes
            key_func="ip"
        ))

        # Aggressive limits for failed attempts
        self.add_rule("failed_auth", RateLimitRule(
            requests=3,
            window=900,  # 3 failed attempts per 15 minutes
            key_func="ip",
            skip_successful=True
        ))

    def add_rule(self, name: str, rule: RateLimitRule):
        """Add a rate limiting rule."""
        if name not in self.rules:
            self.rules[name] = []
        self.rules[name].append(rule)

    def _get_key(self, request: Request, rule: RateLimitRule, user_id: Optional[int] = None) -> str:
        """Generate key for rate limiting based on rule."""
        if rule.key_func == "ip":
            # Get real IP from headers (considering proxies)
            ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            if not ip:
                ip = request.headers.get("X-Real-IP", "")
            if not ip:
                ip = request.client.host if request.client else "unknown"
            return f"ip_{ip}"

        elif rule.key_func == "user" and user_id:
            return f"user_{user_id}"

        elif rule.key_func == "endpoint":
            return f"endpoint_{request.url.path}"

        else:
            # Fallback to IP
            ip = request.client.host if request.client else "unknown"
            return f"ip_{ip}"

    def _get_bucket(self, key: str, rule: RateLimitRule) -> RateLimitBucket:
        """Get or create rate limiting bucket."""
        bucket_key = f"{key}_{rule.requests}_{rule.window}"

        if bucket_key not in self.buckets:
            self.buckets[bucket_key] = RateLimitBucket(
                capacity=rule.requests,
                tokens=rule.requests,
                last_refill=time.time(),
                requests=deque()
            )

        return self.buckets[bucket_key]

    def _refill_bucket(self, bucket: RateLimitBucket, rule: RateLimitRule):
        """Refill tokens in the bucket based on elapsed time."""
        now = time.time()
        elapsed = now - bucket.last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * (rule.requests / rule.window)
        bucket.tokens = min(bucket.capacity, bucket.tokens + tokens_to_add)
        bucket.last_refill = now

        # Clean old requests from sliding window
        cutoff = now - rule.window
        while bucket.requests and bucket.requests[0] < cutoff:
            bucket.requests.popleft()

    def _is_blocked_ip(self, ip: str) -> bool:
        """Check if IP is temporarily blocked."""
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                return True
            else:
                del self.blocked_ips[ip]
        return False

    def _block_ip_temporarily(self, ip: str, duration: int = 3600):
        """Temporarily block an IP address."""
        self.blocked_ips[ip] = time.time() + duration
        logger.warning(f"Temporarily blocked IP {ip} for {duration} seconds")

    def _detect_suspicious_pattern(self, request: Request, user_id: Optional[int] = None) -> bool:
        """Detect suspicious request patterns."""
        ip = request.client.host if request.client else "unknown"

        # Check for rapid requests from same IP
        pattern_key = f"pattern_{ip}"
        self.suspicious_patterns[pattern_key] += 1

        # Block if too many rapid requests
        if self.suspicious_patterns[pattern_key] > 50:  # 50 requests in tracking period
            self._block_ip_temporarily(ip, 1800)  # Block for 30 minutes
            return True

        return False

    async def check_rate_limit(
        self,
        request: Request,
        rules: List[str],
        user_id: Optional[int] = None,
        is_success: bool = True
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request should be rate limited.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        ip = request.client.host if request.client else "unknown"

        # Check if IP is blocked
        if self._is_blocked_ip(ip):
            return False, {
                "error": "IP temporarily blocked",
                "retry_after": int(self.blocked_ips.get(ip, 0) - time.time())
            }

        # Check for suspicious patterns
        if self._detect_suspicious_pattern(request, user_id):
            return False, {
                "error": "Suspicious activity detected",
                "retry_after": 1800
            }

        rate_limit_info = {}

        # Check each rule
        for rule_name in rules:
            if rule_name not in self.rules:
                continue

            for rule in self.rules[rule_name]:
                # Skip counting based on success/failure if configured
                if not is_success and rule.skip_failed:
                    continue
                if is_success and rule.skip_successful:
                    continue

                key = self._get_key(request, rule, user_id)
                bucket = self._get_bucket(key, rule)

                # Refill bucket
                self._refill_bucket(bucket, rule)

                # Check token bucket
                if bucket.tokens < 1:
                    # Also check sliding window for precision
                    if len(bucket.requests) >= rule.requests:
                        retry_after = rule.window - (time.time() - bucket.requests[0])
                        return False, {
                            "error": f"Rate limit exceeded for {rule_name}",
                            "limit": rule.requests,
                            "window": rule.window,
                            "retry_after": max(1, int(retry_after))
                        }

                # Consume token and add request to sliding window
                bucket.tokens -= 1
                bucket.requests.append(time.time())

                # Update rate limit info for headers
                remaining = int(bucket.tokens)
                reset_time = int(time.time() + rule.window)

                rate_limit_info.update({
                    f"X-RateLimit-Limit-{rule_name}": rule.requests,
                    f"X-RateLimit-Remaining-{rule_name}": remaining,
                    f"X-RateLimit-Reset-{rule_name}": reset_time
                })

        return True, rate_limit_info

    def cleanup_old_entries(self):
        """Clean up old entries to prevent memory leaks."""
        current_time = time.time()

        # Clean old buckets (older than 1 hour)
        old_buckets = [
            key for key, bucket in self.buckets.items()
            if current_time - bucket.last_refill > 3600
        ]
        for key in old_buckets:
            del self.buckets[key]

        # Clean old blocked IPs
        expired_blocks = [
            ip for ip, unblock_time in self.blocked_ips.items()
            if current_time > unblock_time
        ]
        for ip in expired_blocks:
            del self.blocked_ips[ip]

        # Clean old suspicious patterns (reset hourly)
        if len(self.suspicious_patterns) > 1000:
            self.suspicious_patterns.clear()


class RequestValidator:
    """Request validation for size, content type, and malicious patterns."""

    def __init__(self):
        self.max_request_size = 50 * 1024 * 1024  # 50MB
        self.max_json_size = 1024 * 1024  # 1MB for JSON
        self.max_form_fields = 100
        self.blocked_patterns = [
            # SQL injection patterns
            r"(?i)(union\s+select|drop\s+table|delete\s+from)",
            # XSS patterns
            r"(?i)(<script|javascript:|onload=|onerror=)",
            # Path traversal
            r"(\.\./|\.\.\|\.\.%2f)",
            # Command injection
            r"(?i)(;|\||&|\$\(|\`)",
        ]

    async def validate_request_size(self, request: Request) -> bool:
        """Validate request size."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            return False
        return True

    async def validate_content_type(self, request: Request) -> bool:
        """Validate content type for specific endpoints."""
        content_type = request.headers.get("content-type", "")
        path = request.url.path

        # Upload endpoint should only accept multipart/form-data
        if path.endswith("/upload") and not content_type.startswith("multipart/form-data"):
            return False

        return True

    async def scan_for_malicious_patterns(self, content: str) -> bool:
        """Scan content for malicious patterns."""
        import re

        for pattern in self.blocked_patterns:
            if re.search(pattern, content):
                return False
        return True


# Global instances
rate_limiter = AdvancedRateLimiter()
request_validator = RequestValidator()


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware for FastAPI."""

    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        response = await call_next(request)
        return response

    # Validate request size first
    if not await request_validator.validate_request_size(request):
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": "Request too large"}
        )

    # Validate content type
    if not await request_validator.validate_content_type(request):
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"detail": "Unsupported media type"}
        )

    # Determine rate limiting rules based on endpoint
    rules = ["global_ip"]

    if request.url.path.startswith("/api/v1/auth"):
        rules.append("auth")
    elif request.url.path.endswith("/upload"):
        rules.append("upload")
    else:
        rules.append("user_general")

    # Check rate limits (before processing request)
    allowed, rate_info = await rate_limiter.check_rate_limit(request, rules)

    if not allowed:
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": rate_info.get("error", "Rate limit exceeded"),
                "retry_after": rate_info.get("retry_after", 60)
            }
        )
        if "retry_after" in rate_info:
            response.headers["Retry-After"] = str(rate_info["retry_after"])
        return response

    # Process request
    try:
        response = await call_next(request)
        is_success = 200 <= response.status_code < 400

        # Update rate limiting based on response (for failed auth tracking)
        if not is_success and request.url.path.startswith("/api/v1/auth"):
            await rate_limiter.check_rate_limit(
                request,
                ["failed_auth"],
                is_success=False
            )

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        is_success = False
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

    # Add rate limit headers
    for header, value in rate_info.items():
        if header.startswith("X-RateLimit"):
            response.headers[header] = str(value)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


def setup_periodic_cleanup():
    """Setup periodic cleanup of rate limiting data."""
    import asyncio
    import threading

    def cleanup_worker():
        while True:
            try:
                rate_limiter.cleanup_old_entries()
                time.sleep(3600)  # Cleanup every hour
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                time.sleep(60)  # Retry in 1 minute on error

    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    logger.info("Started rate limiting cleanup worker")