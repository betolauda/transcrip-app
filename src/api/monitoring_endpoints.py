"""
API endpoints for monitoring and analytics data.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from ..auth.dependencies import get_current_active_user, require_admin
from ..auth.models import User
from ..middleware.monitoring import api_monitor, get_monitoring_data
from ..middleware.rate_limiting import rate_limiter

router = APIRouter(prefix="/monitoring", tags=["Monitoring & Analytics"])


@router.get("/health-detailed")
async def detailed_health_check(
    current_user: User = Depends(get_current_active_user)
):
    """Detailed health check with system metrics."""
    try:
        # Get basic performance metrics
        metrics = api_monitor.get_performance_metrics()

        # System health indicators
        health_status = "healthy"
        warnings = []

        # Check error rate
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 10:  # More than 10% errors
            health_status = "degraded"
            warnings.append(f"High error rate: {error_rate}%")

        # Check average response time
        avg_response_time = metrics.get('avg_response_time', 0)
        if avg_response_time > 2.0:  # Slower than 2 seconds
            health_status = "degraded"
            warnings.append(f"Slow response time: {avg_response_time}s")

        # Check recent activity
        recent_requests = metrics.get('recent_hour', {}).get('requests', 0)

        return {
            "status": health_status,
            "timestamp": datetime.now().isoformat(),
            "version": "1.1.0",
            "authenticated": True,
            "user": current_user.username,
            "warnings": warnings,
            "metrics": {
                "error_rate": error_rate,
                "avg_response_time": avg_response_time,
                "recent_requests": recent_requests,
                "uptime_hours": 1  # Placeholder - would track actual uptime
            }
        }

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/stats/performance")
async def get_performance_stats(
    current_user: User = Depends(require_admin)
):
    """Get detailed performance statistics (admin only)."""
    try:
        return api_monitor.get_performance_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance stats: {e}"
        )


@router.get("/stats/endpoints")
async def get_endpoint_analytics(
    current_user: User = Depends(require_admin)
):
    """Get endpoint usage analytics (admin only)."""
    try:
        return api_monitor.get_endpoint_analytics()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint analytics: {e}"
        )


@router.get("/stats/users")
async def get_user_analytics(
    current_user: User = Depends(require_admin)
):
    """Get user behavior analytics (admin only)."""
    try:
        return api_monitor.get_user_analytics()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user analytics: {e}"
        )


@router.get("/stats/security")
async def get_security_summary(
    current_user: User = Depends(require_admin)
):
    """Get security events summary (admin only)."""
    try:
        return api_monitor.get_security_summary()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get security summary: {e}"
        )


@router.get("/stats/rate-limiting")
async def get_rate_limiting_stats(
    current_user: User = Depends(require_admin)
):
    """Get rate limiting statistics (admin only)."""
    try:
        # Get rate limiter internal state
        stats = {
            "active_buckets": len(rate_limiter.buckets),
            "blocked_ips": len(rate_limiter.blocked_ips),
            "suspicious_patterns": len(rate_limiter.suspicious_patterns),
            "blocked_ip_list": list(rate_limiter.blocked_ips.keys()),
            "suspicious_activity": dict(rate_limiter.suspicious_patterns.most_common(10))
        }
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rate limiting stats: {e}"
        )


@router.get("/export")
async def export_complete_metrics(
    format: str = Query("json", description="Export format: json or csv"),
    hours: Optional[int] = Query(24, description="Hours of data to export"),
    current_user: User = Depends(require_admin)
):
    """Export complete monitoring metrics (admin only)."""
    try:
        if format not in ["json", "csv"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format must be 'json' or 'csv'"
            )

        # Get comprehensive metrics
        metrics = get_monitoring_data()

        if format == "json":
            return metrics
        else:
            # For CSV export, we'd need to flatten the data structure
            # This is a simplified version
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            writer.writerow(["Metric", "Value"])

            # Write basic stats
            summary = metrics.get("summary", {})
            for key, value in summary.items():
                writer.writerow([f"summary_{key}", value])

            # Write performance metrics
            performance = metrics.get("performance", {})
            for key, value in performance.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        writer.writerow([f"performance_{key}_{sub_key}", sub_value])
                else:
                    writer.writerow([f"performance_{key}", value])

            csv_content = output.getvalue()
            output.close()

            return JSONResponse(
                content={"csv_data": csv_content},
                headers={"Content-Type": "application/json"}
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export metrics: {e}"
        )


@router.post("/alerts/configure")
async def configure_alerts(
    alert_config: Dict[str, Any],
    current_user: User = Depends(require_admin)
):
    """Configure monitoring alerts (admin only)."""
    try:
        # This would configure alerting thresholds
        # For now, just return the configuration
        supported_alerts = {
            "error_rate_threshold": "Percentage threshold for error rate alerts",
            "response_time_threshold": "Response time threshold in seconds",
            "request_rate_threshold": "Requests per minute threshold",
            "failed_auth_threshold": "Failed authentication attempts threshold"
        }

        configured = {}
        for key, value in alert_config.items():
            if key in supported_alerts:
                configured[key] = value

        return {
            "message": "Alert configuration updated",
            "configured_alerts": configured,
            "available_alerts": supported_alerts
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure alerts: {e}"
        )


@router.get("/dashboard")
async def get_monitoring_dashboard(
    current_user: User = Depends(require_admin)
):
    """Get data for monitoring dashboard (admin only)."""
    try:
        # Compile dashboard data
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": api_monitor.get_performance_metrics(),
            "top_endpoints": dict(list(api_monitor.get_endpoint_analytics().items())[:10]),
            "recent_errors": [
                {
                    "path": req.path,
                    "status_code": req.status_code,
                    "timestamp": datetime.fromtimestamp(req.timestamp).isoformat(),
                    "response_time": req.response_time
                }
                for req in api_monitor.error_requests[-10:]  # Last 10 errors
            ],
            "slow_requests": [
                {
                    "path": req.path,
                    "response_time": req.response_time,
                    "timestamp": datetime.fromtimestamp(req.timestamp).isoformat()
                }
                for req in api_monitor.slow_requests[-10:]  # Last 10 slow requests
            ],
            "security_events": api_monitor.get_security_summary(),
            "rate_limiting": {
                "active_buckets": len(rate_limiter.buckets),
                "blocked_ips": len(rate_limiter.blocked_ips)
            }
        }

        return dashboard_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {e}"
        )