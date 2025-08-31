"""Repo market data models using Pydantic for validation."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, validator


class RepoSpread(BaseModel):
    """Repo spread data for a specific security and term."""
    
    cusip: str = Field(..., description="CUSIP identifier")
    spread_date: date = Field(..., description="Spread calculation date")
    term_days: int = Field(..., description="Repo term in days")
    repo_rate: Decimal = Field(..., description="Repo rate as decimal")
    treasury_rate: Decimal = Field(..., description="Corresponding Treasury rate")
    spread_bps: Decimal = Field(..., description="Spread in basis points")
    volume: Optional[Decimal] = Field(None, description="Trading volume")
    trade_count: Optional[int] = Field(None, description="Number of trades")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('cusip')
    def validate_cusip(cls, v):
        """Validate CUSIP format (9 characters)."""
        if len(v) != 9:
            raise ValueError('CUSIP must be 9 characters')
        return v.upper()
    
    @validator('term_days')
    def validate_term_days(cls, v):
        """Validate repo term is positive."""
        if v <= 0:
            raise ValueError('Term days must be positive')
        return v
    
    @validator('repo_rate', 'treasury_rate')
    def validate_rates(cls, v):
        """Validate rates are reasonable (between -1% and 50%)."""
        if v < -0.01 or v > 0.5:
            raise ValueError('Rates must be between -1% and 50%')
        return v
    
    @validator('volume')
    def validate_volume(cls, v):
        """Validate volume is positive when provided."""
        if v is not None and v <= 0:
            raise ValueError('Volume must be positive')
        return v
    
    @validator('trade_count')
    def validate_trade_count(cls, v):
        """Validate trade count is positive when provided."""
        if v is not None and v <= 0:
            raise ValueError('Trade count must be positive')
        return v


class RepoData(BaseModel):
    """Aggregated repo market data for a security."""
    
    cusip: str = Field(..., description="CUSIP identifier")
    data_date: date = Field(..., description="Data date")
    overnight_spread: Optional[Decimal] = Field(None, description="Overnight repo spread")
    one_week_spread: Optional[Decimal] = Field(None, description="1-week repo spread")
    one_month_spread: Optional[Decimal] = Field(None, description="1-month repo spread")
    three_month_spread: Optional[Decimal] = Field(None, description="3-month repo spread")
    avg_spread: Optional[Decimal] = Field(None, description="Average spread across terms")
    total_volume: Optional[Decimal] = Field(None, description="Total daily volume")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('cusip')
    def validate_cusip(cls, v):
        """Validate CUSIP format (9 characters)."""
        if len(v) != 9:
            raise ValueError('CUSIP must be 9 characters')
        return v.upper()
    
    def calculate_avg_spread(self) -> Optional[Decimal]:
        """Calculate average spread from available term spreads."""
        spreads = [
            self.overnight_spread,
            self.one_week_spread, 
            self.one_month_spread,
            self.three_month_spread
        ]
        valid_spreads = [s for s in spreads if s is not None]
        
        if not valid_spreads:
            return None
        
        return sum(valid_spreads) / len(valid_spreads)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
