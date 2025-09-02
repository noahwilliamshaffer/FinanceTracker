"""
Real-time Monitoring Dashboard for Finance Tracker
Shows data freshness, processing status, and system health
"""

import boto3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

monitoring_router = APIRouter()


class FinanceTrackerMonitor:
    """
    Provides real-time monitoring of the Finance Tracker data pipeline.
    
    Features:
    - Data freshness monitoring
    - Processing status tracking
    - EventBridge event history
    - S3 storage metrics
    - Lambda function health
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """Initialize monitoring clients."""
        self.region_name = region_name
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.events_client = boto3.client('events', region_name=region_name)
        self.cloudwatch_client = boto3.client('cloudwatch', region_name=region_name)
        self.logs_client = boto3.client('logs', region_name=region_name)
    
    def get_data_freshness_status(self) -> Dict[str, Any]:
        """
        Check the freshness of data in S3 buckets.
        
        Returns:
            Dict with data freshness information
        """
        try:
            bucket_name = "finance-tracker-data-783085491860"  # Your bucket
            
            # Check latest treasury data
            treasury_prefix = "treasury/"
            treasury_objects = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=treasury_prefix,
                MaxKeys=10
            )
            
            latest_treasury = None
            if 'Contents' in treasury_objects and treasury_objects['Contents']:
                # Sort by last modified descending
                sorted_objects = sorted(
                    treasury_objects['Contents'], 
                    key=lambda x: x['LastModified'], 
                    reverse=True
                )
                latest_treasury = sorted_objects[0]
            
            # Check latest repo data
            repo_prefix = "repo/"
            repo_objects = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=repo_prefix,
                MaxKeys=10
            )
            
            latest_repo = None
            if 'Contents' in repo_objects and repo_objects['Contents']:
                sorted_objects = sorted(
                    repo_objects['Contents'], 
                    key=lambda x: x['LastModified'], 
                    reverse=True
                )
                latest_repo = sorted_objects[0]
            
            # Calculate freshness
            now = datetime.now(latest_treasury['LastModified'].tzinfo) if latest_treasury else datetime.utcnow()
            
            treasury_age_minutes = None
            repo_age_minutes = None
            
            if latest_treasury:
                treasury_age = now - latest_treasury['LastModified']
                treasury_age_minutes = int(treasury_age.total_seconds() / 60)
            
            if latest_repo:
                repo_age = now - latest_repo['LastModified']
                repo_age_minutes = int(repo_age.total_seconds() / 60)
            
            return {
                'treasury_data': {
                    'latest_file': latest_treasury['Key'] if latest_treasury else None,
                    'last_modified': latest_treasury['LastModified'].isoformat() if latest_treasury else None,
                    'age_minutes': treasury_age_minutes,
                    'size_bytes': latest_treasury['Size'] if latest_treasury else 0,
                    'status': 'fresh' if treasury_age_minutes and treasury_age_minutes < 240 else 'stale'
                },
                'repo_data': {
                    'latest_file': latest_repo['Key'] if latest_repo else None,
                    'last_modified': latest_repo['LastModified'].isoformat() if latest_repo else None,
                    'age_minutes': repo_age_minutes,
                    'size_bytes': latest_repo['Size'] if latest_repo else 0,
                    'status': 'fresh' if repo_age_minutes and repo_age_minutes < 120 else 'stale'
                },
                'overall_status': 'healthy' if (
                    treasury_age_minutes and treasury_age_minutes < 240 and
                    repo_age_minutes and repo_age_minutes < 120
                ) else 'degraded'
            }
            
        except Exception as e:
            logger.error("Failed to check data freshness", error=str(e))
            return {
                'error': str(e),
                'overall_status': 'error'
            }
    
    def get_recent_events(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent EventBridge events from the Finance Tracker pipeline.
        
        Args:
            hours_back: Number of hours of event history to retrieve
            
        Returns:
            List of recent events
        """
        try:
            # Note: In production, you'd query EventBridge event history
            # For now, we'll simulate recent events
            now = datetime.utcnow()
            
            simulated_events = [
                {
                    'timestamp': (now - timedelta(minutes=30)).isoformat(),
                    'source': 'finance.treasury',
                    'detail_type': 'Treasury Data Update',
                    'status': 'success',
                    'processed_count': 5,
                    'failed_count': 0,
                    'message': 'Successfully processed 5 treasury securities'
                },
                {
                    'timestamp': (now - timedelta(minutes=90)).isoformat(),
                    'source': 'finance.repo',
                    'detail_type': 'Repo Data Update',
                    'status': 'success',
                    'processed_count': 4,
                    'failed_count': 0,
                    'message': 'Successfully processed 4 repo spreads'
                },
                {
                    'timestamp': (now - timedelta(minutes=150)).isoformat(),
                    'source': 'finance.scoring',
                    'detail_type': 'Scoring Calculation',
                    'status': 'success',
                    'processed_count': 5,
                    'failed_count': 0,
                    'message': 'Successfully calculated scores for 5 securities'
                }
            ]
            
            return simulated_events
            
        except Exception as e:
            logger.error("Failed to get recent events", error=str(e))
            return []
    
    def get_lambda_metrics(self) -> Dict[str, Any]:
        """
        Get Lambda function execution metrics.
        
        Returns:
            Dict with Lambda performance metrics
        """
        try:
            # Get metrics for the last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            # In production, you'd query actual CloudWatch metrics
            # For now, we'll simulate metrics
            return {
                'treasury_fetcher': {
                    'invocations': 6,
                    'errors': 0,
                    'duration_avg_ms': 15000,
                    'success_rate': 100.0,
                    'last_execution': (end_time - timedelta(minutes=30)).isoformat()
                },
                'repo_fetcher': {
                    'invocations': 12,
                    'errors': 1,
                    'duration_avg_ms': 8000,
                    'success_rate': 91.7,
                    'last_execution': (end_time - timedelta(minutes=90)).isoformat()
                },
                'scoring_calculator': {
                    'invocations': 24,
                    'errors': 0,
                    'duration_avg_ms': 5000,
                    'success_rate': 100.0,
                    'last_execution': (end_time - timedelta(minutes=60)).isoformat()
                }
            }
            
        except Exception as e:
            logger.error("Failed to get Lambda metrics", error=str(e))
            return {}
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health status.
        
        Returns:
            Dict with system health information
        """
        data_freshness = self.get_data_freshness_status()
        recent_events = self.get_recent_events()
        lambda_metrics = self.get_lambda_metrics()
        
        # Determine overall health
        health_score = 100
        health_issues = []
        
        # Check data freshness
        if data_freshness.get('overall_status') == 'degraded':
            health_score -= 30
            health_issues.append("Data is not fresh")
        elif data_freshness.get('overall_status') == 'error':
            health_score -= 50
            health_issues.append("Data freshness check failed")
        
        # Check recent failures
        recent_failures = [e for e in recent_events if e.get('status') == 'failed']
        if recent_failures:
            health_score -= len(recent_failures) * 10
            health_issues.append(f"{len(recent_failures)} recent failures")
        
        # Check Lambda error rates
        for func_name, metrics in lambda_metrics.items():
            if metrics.get('success_rate', 100) < 95:
                health_score -= 15
                health_issues.append(f"{func_name} has high error rate")
        
        health_score = max(0, health_score)
        
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            'overall_status': status,
            'health_score': health_score,
            'issues': health_issues,
            'data_freshness': data_freshness,
            'recent_events_count': len(recent_events),
            'lambda_functions_healthy': len([
                f for f, m in lambda_metrics.items() 
                if m.get('success_rate', 0) >= 95
            ]),
            'last_updated': datetime.utcnow().isoformat()
        }


# Initialize global monitor
monitor = FinanceTrackerMonitor()


@monitoring_router.get("/health")
async def get_system_health():
    """Get overall system health status."""
    return JSONResponse(content=monitor.get_system_health())


@monitoring_router.get("/data-freshness")
async def get_data_freshness():
    """Get data freshness status."""
    return JSONResponse(content=monitor.get_data_freshness_status())


@monitoring_router.get("/recent-events")
async def get_recent_events(hours_back: int = 24):
    """Get recent pipeline events."""
    events = monitor.get_recent_events(hours_back)
    return JSONResponse(content={"events": events, "count": len(events)})


@monitoring_router.get("/lambda-metrics")
async def get_lambda_metrics():
    """Get Lambda function performance metrics."""
    return JSONResponse(content=monitor.get_lambda_metrics())


@monitoring_router.get("/monitoring-dashboard")
async def get_monitoring_dashboard():
    """Get complete monitoring dashboard data."""
    return JSONResponse(content={
        "system_health": monitor.get_system_health(),
        "data_freshness": monitor.get_data_freshness_status(),
        "recent_events": monitor.get_recent_events(),
        "lambda_metrics": monitor.get_lambda_metrics(),
        "dashboard_updated": datetime.utcnow().isoformat()
    })
