"""
API monitoring and analytics middleware for tracking usage and performance.
"""
import time
import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from fastapi import Request, Response
import logging

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    timestamp: float
    method: str
    path: str
    status_code: int
    response_time: float
    user_id: Optional[int] = None
    ip_address: str = ""
    user_agent: str = ""
    content_length: int = 0
    response_size: int = 0
    error_message: Optional[str] = None


@dataclass
class EndpointStats:
    """Statistics for an endpoint."""
    total_requests: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float('inf')
    total_response_time: float = 0.0
    last_accessed: Optional[datetime] = None


@dataclass
class UserStats:
    """Statistics for a user."""
    total_requests: int = 0
    upload_count: int = 0
    auth_attempts: int = 0
    failed_auth_attempts: int = 0
    last_active: Optional[datetime] = None
    endpoints_used: Dict[str, int] = None
    total_data_uploaded: int = 0

    def __post_init__(self):
        if self.endpoints_used is None:
            self.endpoints_used = {}


class APIMonitor:
    """
    Advanced API monitoring and analytics system.

    Features:
    - Real-time request metrics collection
    - Endpoint usage statistics
    - User behavior analytics
    - Performance monitoring
    - Error tracking and alerts
    - Rate limiting metrics
    - Security event logging
    """

    def __init__(self, max_history_hours: int = 24):
        self.max_history_hours = max_history_hours
        self.request_history: List[RequestMetrics] = []
        self.endpoint_stats: Dict[str, EndpointStats] = defaultdict(EndpointStats)
        self.user_stats: Dict[int, UserStats] = defaultdict(UserStats)
        self.error_patterns: Counter = Counter()
        self.security_events: List[Dict[str, Any]] = []

        # Performance tracking
        self.slow_requests: List[RequestMetrics] = []
        self.error_requests: List[RequestMetrics] = []

        # Real-time metrics
        self.current_hour_stats = {
            'requests': 0,
            'errors': 0,
            'avg_response_time': 0.0,
            'unique_users': set(),
            'endpoints_hit': set()
        }

        self.last_hour_reset = datetime.now()

    def _should_reset_hourly_stats(self) -> bool:
        """Check if hourly stats should be reset."""
        return datetime.now() - self.last_hour_reset >= timedelta(hours=1)

    def _reset_hourly_stats(self):
        """Reset hourly statistics."""
        self.current_hour_stats = {
            'requests': 0,
            'errors': 0,
            'avg_response_time': 0.0,
            'unique_users': set(),
            'endpoints_hit': set()
        }
        self.last_hour_reset = datetime.now()

    def _cleanup_old_data(self):
        """Remove old data to prevent memory growth."""
        cutoff_time = time.time() - (self.max_history_hours * 3600)

        # Clean request history
        self.request_history = [
            req for req in self.request_history
            if req.timestamp > cutoff_time
        ]

        # Clean slow requests
        self.slow_requests = [
            req for req in self.slow_requests
            if req.timestamp > cutoff_time
        ]

        # Clean error requests
        self.error_requests = [
            req for req in self.error_requests
            if req.timestamp > cutoff_time
        ]

        # Clean security events (keep 7 days)
        security_cutoff = time.time() - (7 * 24 * 3600)
        self.security_events = [
            event for event in self.security_events
            if event.get('timestamp', 0) > security_cutoff
        ]

    def record_request(self, metrics: RequestMetrics):
        """Record request metrics."""
        # Reset hourly stats if needed
        if self._should_reset_hourly_stats():
            self._reset_hourly_stats()

        # Add to history
        self.request_history.append(metrics)

        # Update endpoint stats
        endpoint_key = f"{metrics.method} {metrics.path}"
        stats = self.endpoint_stats[endpoint_key]

        stats.total_requests += 1
        stats.total_response_time += metrics.response_time
        stats.avg_response_time = stats.total_response_time / stats.total_requests
        stats.max_response_time = max(stats.max_response_time, metrics.response_time)
        stats.min_response_time = min(stats.min_response_time, metrics.response_time)
        stats.last_accessed = datetime.now()

        if 200 <= metrics.status_code < 400:
            stats.success_count += 1
        else:
            stats.error_count += 1

        # Update user stats
        if metrics.user_id:
            user_stats = self.user_stats[metrics.user_id]
            user_stats.total_requests += 1
            user_stats.last_active = datetime.now()

            if endpoint_key not in user_stats.endpoints_used:
                user_stats.endpoints_used[endpoint_key] = 0
            user_stats.endpoints_used[endpoint_key] += 1

            # Track uploads
            if 'upload' in metrics.path.lower():
                user_stats.upload_count += 1
                user_stats.total_data_uploaded += metrics.content_length

            # Track auth attempts
            if 'auth' in metrics.path.lower():
                user_stats.auth_attempts += 1
                if metrics.status_code >= 400:
                    user_stats.failed_auth_attempts += 1

        # Update hourly stats
        self.current_hour_stats['requests'] += 1
        if metrics.status_code >= 400:
            self.current_hour_stats['errors'] += 1
        if metrics.user_id:
            self.current_hour_stats['unique_users'].add(metrics.user_id)
        self.current_hour_stats['endpoints_hit'].add(endpoint_key)

        # Track performance issues
        if metrics.response_time > 2.0:  # Slow request threshold
            self.slow_requests.append(metrics)

        # Track errors
        if metrics.status_code >= 400:
            self.error_requests.append(metrics)

            # Count error patterns
            error_pattern = f"{metrics.status_code}:{metrics.path}"
            self.error_patterns[error_pattern] += 1

        # Cleanup old data periodically
        if len(self.request_history) % 1000 == 0:
            self._cleanup_old_data()

    def record_security_event(self, event_type: str, details: Dict[str, Any], ip_address: str = None):
        """Record security events for monitoring."""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'details': details,
            'ip_address': ip_address
        }
        self.security_events.append(event)

        logger.warning(f"Security event recorded: {event_type} from {ip_address}: {details}")

    def get_endpoint_analytics(self) -> Dict[str, Any]:
        """Get endpoint usage analytics."""
        return {
            endpoint: {
                'total_requests': stats.total_requests,
                'success_rate': (stats.success_count / stats.total_requests * 100) if stats.total_requests > 0 else 0,
                'avg_response_time': round(stats.avg_response_time, 3),
                'max_response_time': round(stats.max_response_time, 3),
                'min_response_time': round(stats.min_response_time, 3) if stats.min_response_time != float('inf') else 0,
                'last_accessed': stats.last_accessed.isoformat() if stats.last_accessed else None
            }
            for endpoint, stats in self.endpoint_stats.items()
        }

    def get_user_analytics(self) -> Dict[str, Any]:
        """Get user behavior analytics."""
        return {
            str(user_id): {
                'total_requests': stats.total_requests,
                'upload_count': stats.upload_count,
                'auth_attempts': stats.auth_attempts,
                'failed_auth_attempts': stats.failed_auth_attempts,
                'auth_success_rate': ((stats.auth_attempts - stats.failed_auth_attempts) / stats.auth_attempts * 100) if stats.auth_attempts > 0 else 0,
                'last_active': stats.last_active.isoformat() if stats.last_active else None,
                'top_endpoints': dict(Counter(stats.endpoints_used).most_common(5)),
                'total_data_uploaded_mb': round(stats.total_data_uploaded / (1024 * 1024), 2)
            }
            for user_id, stats in self.user_stats.items()
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        total_requests = len(self.request_history)
        if total_requests == 0:
            return {'message': 'No requests recorded'}

        # Calculate metrics
        response_times = [req.response_time for req in self.request_history]
        error_count = len(self.error_requests)
        slow_count = len(self.slow_requests)

        # Recent performance (last hour)
        one_hour_ago = time.time() - 3600
        recent_requests = [req for req in self.request_history if req.timestamp > one_hour_ago]
        recent_response_times = [req.response_time for req in recent_requests]

        return {
            'total_requests': total_requests,
            'error_rate': round((error_count / total_requests) * 100, 2),
            'slow_request_rate': round((slow_count / total_requests) * 100, 2),
            'avg_response_time': round(sum(response_times) / len(response_times), 3),
            'max_response_time': round(max(response_times), 3),
            'min_response_time': round(min(response_times), 3),
            'p95_response_time': round(sorted(response_times)[int(len(response_times) * 0.95)], 3) if response_times else 0,
            'recent_hour': {
                'requests': len(recent_requests),
                'avg_response_time': round(sum(recent_response_times) / len(recent_response_times), 3) if recent_response_times else 0,
                'unique_users': len(self.current_hour_stats['unique_users']),
                'endpoints_hit': len(self.current_hour_stats['endpoints_hit'])
            }
        }

    def get_security_summary(self) -> Dict[str, Any]:
        """Get security events summary."""
        # Group security events by type
        event_types = Counter(event['type'] for event in self.security_events)

        # Recent security events (last 24 hours)
        recent_cutoff = time.time() - (24 * 3600)
        recent_events = [event for event in self.security_events if event['timestamp'] > recent_cutoff]

        # Top error patterns
        top_errors = dict(self.error_patterns.most_common(10))

        return {
            'total_security_events': len(self.security_events),
            'recent_security_events': len(recent_events),
            'event_types': dict(event_types),
            'top_error_patterns': top_errors,
            'recent_events': recent_events[-10:] if recent_events else []  # Last 10 events
        }

    def export_metrics(self) -> Dict[str, Any]:
        """Export comprehensive metrics for reporting."""
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_requests': len(self.request_history),
                'total_users': len(self.user_stats),
                'total_endpoints': len(self.endpoint_stats),
                'data_collection_hours': self.max_history_hours
            },
            'performance': self.get_performance_metrics(),
            'endpoints': self.get_endpoint_analytics(),
            'users': self.get_user_analytics(),
            'security': self.get_security_summary()
        }


# Global monitor instance
api_monitor = APIMonitor()


async def monitoring_middleware(request: Request, call_next):
    """Monitoring middleware for FastAPI."""
    start_time = time.time()

    # Extract request info
    user_id = None
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    content_length = int(request.headers.get("content-length", 0))

    # Try to get user ID if authenticated
    try:
        # This is a simple way to check if user is authenticated
        # In practice, you might need to extract this differently
        auth_header = request.headers.get("authorization")
        if auth_header:
            # For this implementation, we'll set user_id later from the request state
            pass
    except Exception:
        pass

    error_message = None
    response = None

    try:
        # Process request
        response = await call_next(request)

        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error in monitoring middleware: {e}")
        # Create a 500 response for monitoring purposes
        from fastapi.responses import JSONResponse
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    # Calculate response time
    response_time = time.time() - start_time

    # Get response size
    response_size = 0
    if hasattr(response, 'body'):
        response_size = len(response.body)

    # Create metrics record
    metrics = RequestMetrics(
        timestamp=start_time,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code if response else 500,
        response_time=response_time,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        content_length=content_length,
        response_size=response_size,
        error_message=error_message
    )

    # Record metrics
    api_monitor.record_request(metrics)

    # Log slow requests
    if response_time > 2.0:
        logger.warning(f"Slow request detected: {request.method} {request.url.path} took {response_time:.2f}s")

    # Log errors
    if response and response.status_code >= 400:
        logger.warning(f"Error response: {response.status_code} for {request.method} {request.url.path}")

    return response


def get_monitoring_data() -> Dict[str, Any]:
    """Get current monitoring data."""
    return api_monitor.export_metrics()