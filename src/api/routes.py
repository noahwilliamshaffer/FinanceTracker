"""
API Routes for Finance Tracker

This module defines all API endpoints for treasury data, repo spreads,
scoring results, and dashboard functionality.
"""

from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd
import json
import structlog

from ..models.treasury import TreasuryData, TreasuryPrice
from ..models.repo import RepoData, RepoSpread
from ..models.scoring import ScoreData, ScoreWeights
from ..utils.s3_helper import S3DataManager
from ..visualization.plotly_charts import PlotlyChartGenerator

# Initialize structured logger
logger = structlog.get_logger(__name__)

# Initialize templates
templates = Jinja2Templates(directory="src/api/templates")

# Create routers
treasury_router = APIRouter()
repo_router = APIRouter()
scoring_router = APIRouter()
dashboard_router = APIRouter()


# Treasury Data Routes
@treasury_router.get("/prices", response_model=List[TreasuryPrice])
async def get_treasury_prices(
    cusip: Optional[str] = Query(None, description="Filter by CUSIP"),
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records")
):
    """
    Get treasury price data with optional filtering.
    
    Returns current and historical treasury prices with BVAL and internal pricing.
    """
    logger.info(
        "Treasury prices API request",
        cusip=cusip,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    try:
        # In a real implementation, this would query S3 or a database
        # For now, return sample data
        sample_data = _generate_sample_treasury_data(cusip, start_date, end_date, limit)
        
        logger.info(
            "Treasury prices returned successfully",
            record_count=len(sample_data)
        )
        
        return sample_data
        
    except Exception as e:
        logger.error("Failed to retrieve treasury prices", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve treasury prices")


@treasury_router.get("/securities")
async def get_treasury_securities():
    """Get list of available treasury securities."""
    try:
        # Sample treasury securities
        securities = [
            {
                "cusip": "912828XG8",
                "description": "10-Year Treasury Note",
                "maturity_date": "2034-02-15",
                "coupon_rate": 0.0425
            },
            {
                "cusip": "912828YK0", 
                "description": "2-Year Treasury Note",
                "maturity_date": "2026-01-31",
                "coupon_rate": 0.0475
            },
            {
                "cusip": "912810RZ3",
                "description": "30-Year Treasury Bond",
                "maturity_date": "2054-02-15", 
                "coupon_rate": 0.0450
            }
        ]
        
        return securities
        
    except Exception as e:
        logger.error("Failed to retrieve treasury securities", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve securities")


# Repo Data Routes
@repo_router.get("/spreads", response_model=List[RepoSpread])
async def get_repo_spreads(
    cusip: Optional[str] = Query(None, description="Filter by CUSIP"),
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    term_days: Optional[int] = Query(None, description="Filter by repo term in days")
):
    """Get repo spread data with optional filtering."""
    logger.info(
        "Repo spreads API request",
        cusip=cusip,
        start_date=start_date,
        end_date=end_date,
        term_days=term_days
    )
    
    try:
        sample_data = _generate_sample_repo_data(cusip, start_date, end_date, term_days)
        
        logger.info(
            "Repo spreads returned successfully",
            record_count=len(sample_data)
        )
        
        return sample_data
        
    except Exception as e:
        logger.error("Failed to retrieve repo spreads", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve repo spreads")


# Scoring Routes
@scoring_router.get("/scores", response_model=List[ScoreData])
async def get_scores(
    cusip: Optional[str] = Query(None, description="Filter by CUSIP"),
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum composite score")
):
    """Get composite scores with optional filtering."""
    logger.info(
        "Scores API request",
        cusip=cusip,
        start_date=start_date,
        end_date=end_date,
        min_score=min_score
    )
    
    try:
        sample_data = _generate_sample_score_data(cusip, start_date, end_date, min_score)
        
        logger.info(
            "Scores returned successfully",
            record_count=len(sample_data)
        )
        
        return sample_data
        
    except Exception as e:
        logger.error("Failed to retrieve scores", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve scores")


@scoring_router.get("/weights")
async def get_scoring_weights():
    """Get current scoring weights configuration."""
    try:
        # Load from configuration
        weights = ScoreWeights()  # Uses defaults from config
        
        return weights.dict()
        
    except Exception as e:
        logger.error("Failed to retrieve scoring weights", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve scoring weights")


# Dashboard Routes
@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "Finance Tracker Dashboard",
            "active_page": "dashboard"
        }
    )


@dashboard_router.get("/treasury", response_class=HTMLResponse)
async def treasury_dashboard(request: Request):
    """Treasury data dashboard."""
    return templates.TemplateResponse(
        "treasury_dashboard.html",
        {
            "request": request,
            "title": "Treasury Dashboard",
            "active_page": "treasury"
        }
    )


@dashboard_router.get("/repo", response_class=HTMLResponse) 
async def repo_dashboard(request: Request):
    """Repo spreads dashboard."""
    return templates.TemplateResponse(
        "repo_dashboard.html",
        {
            "request": request,
            "title": "Repo Spreads Dashboard", 
            "active_page": "repo"
        }
    )


@dashboard_router.get("/scoring", response_class=HTMLResponse)
async def scoring_dashboard(request: Request):
    """Scoring analysis dashboard."""
    return templates.TemplateResponse(
        "scoring_dashboard.html",
        {
            "request": request,
            "title": "Scoring Dashboard",
            "active_page": "scoring"
        }
    )


@dashboard_router.get("/charts/treasury-prices/{cusip}")
async def treasury_price_chart(cusip: str):
    """Generate treasury price chart for specific CUSIP."""
    try:
        # Generate sample data
        sample_data = _generate_sample_treasury_data(cusip, limit=30)
        
        if not sample_data:
            raise HTTPException(status_code=404, detail="No data found for CUSIP")
        
        # Convert to DataFrame
        df = pd.DataFrame([item.dict() for item in sample_data])
        
        # Generate chart
        chart_generator = PlotlyChartGenerator()
        fig = chart_generator.create_treasury_price_timeseries(
            df, cusip, title=f"Treasury Price Analysis - {cusip}"
        )
        
        # Return as JSON for frontend rendering
        return JSONResponse(content=fig.to_dict())
        
    except Exception as e:
        logger.error("Failed to generate treasury price chart", cusip=cusip, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate chart")


@dashboard_router.get("/charts/repo-spreads")
async def repo_spreads_chart(
    cusips: Optional[str] = Query(None, description="Comma-separated CUSIPs")
):
    """Generate repo spreads analysis chart."""
    try:
        cusip_list = cusips.split(",") if cusips else None
        
        # Generate sample repo data
        sample_data = []
        for cusip in (cusip_list or ["912828XG8", "912828YK0"]):
            sample_data.extend(_generate_sample_repo_data(cusip))
        
        if not sample_data:
            raise HTTPException(status_code=404, detail="No repo data found")
        
        # Convert to DataFrame
        df = pd.DataFrame([item.dict() for item in sample_data])
        
        # Generate chart
        chart_generator = PlotlyChartGenerator()
        fig = chart_generator.create_repo_spread_analysis(
            df, cusips=cusip_list, title="Repo Spread Analysis"
        )
        
        return JSONResponse(content=fig.to_dict())
        
    except Exception as e:
        logger.error("Failed to generate repo spreads chart", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate chart")


# Helper functions to generate sample data
def _generate_sample_treasury_data(
    cusip: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100
) -> List[TreasuryPrice]:
    """Generate sample treasury price data."""
    cusips = [cusip] if cusip else ["912828XG8", "912828YK0", "912810RZ3"]
    
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))
    
    sample_data = []
    
    for c in cusips:
        current_date = start_date
        base_price = 99.5
        
        while current_date <= end_date and len(sample_data) < limit:
            # Simulate price movement
            price_change = (hash(f"{c}{current_date}") % 100 - 50) / 10000
            bval_price = base_price + price_change
            internal_price = bval_price + (hash(f"internal{c}{current_date}") % 20 - 10) / 10000
            
            sample_data.append(TreasuryPrice(
                cusip=c,
                price_date=current_date,
                bval_price=bval_price,
                internal_price=internal_price,
                day_over_day_change=price_change
            ))
            
            current_date += timedelta(days=1)
            base_price = bval_price  # Use previous price as base
    
    return sample_data[:limit]


def _generate_sample_repo_data(
    cusip: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    term_days: Optional[int] = None
) -> List[RepoSpread]:
    """Generate sample repo spread data."""
    cusips = [cusip] if cusip else ["912828XG8", "912828YK0"]
    terms = [term_days] if term_days else [1, 7, 30, 90]
    
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=7))
    
    sample_data = []
    
    for c in cusips:
        for term in terms:
            current_date = start_date
            
            while current_date <= end_date:
                # Simulate repo rates and spreads
                base_repo_rate = 0.05  # 5% base rate
                treasury_rate = base_repo_rate - 0.001  # Slightly lower
                spread_bps = (hash(f"{c}{term}{current_date}") % 20) + 5  # 5-25 bps
                
                sample_data.append(RepoSpread(
                    cusip=c,
                    spread_date=current_date,
                    term_days=term,
                    repo_rate=base_repo_rate,
                    treasury_rate=treasury_rate,
                    spread_bps=spread_bps,
                    volume=1000000 + (hash(f"vol{c}{current_date}") % 5000000)
                ))
                
                current_date += timedelta(days=1)
    
    return sample_data


def _generate_sample_score_data(
    cusip: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_score: Optional[float] = None
) -> List[ScoreData]:
    """Generate sample score data."""
    cusips = [cusip] if cusip else ["912828XG8", "912828YK0", "912810RZ3"]
    
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=7))
    
    sample_data = []
    
    for c in cusips:
        current_date = start_date
        
        while current_date <= end_date:
            # Generate random but realistic scores
            base_score = 50 + (hash(f"{c}{current_date}") % 40)  # 50-90 range
            
            if min_score and base_score < min_score:
                current_date += timedelta(days=1)
                continue
            
            sample_data.append(ScoreData(
                cusip=c,
                score_date=current_date,
                repo_spread_score=base_score + (hash(f"repo{c}") % 20 - 10),
                bval_divergence_score=base_score + (hash(f"bval{c}") % 20 - 10),
                volume_score=base_score + (hash(f"vol{c}") % 20 - 10),
                volatility_score=base_score + (hash(f"vol{c}") % 20 - 10),
                composite_score=base_score,
                confidence_score=75 + (hash(f"conf{c}") % 20)
            ))
            
            current_date += timedelta(days=1)
    
    return sample_data
