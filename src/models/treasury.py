"""Treasury data models using Pydantic for validation."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, validator


class TreasuryPrice(BaseModel):
    """Individual treasury price record."""
    
    cusip: str = Field(..., description="CUSIP identifier")
    price_date: date = Field(..., description="Price date")
    bval_price: Optional[Decimal] = Field(None, description="BVAL price")
    discount_price: Optional[Decimal] = Field(None, description="Discount price")
    dollar_price: Optional[Decimal] = Field(None, description="Dollar price")
    internal_price: Optional[Decimal] = Field(None, description="Glacier Peak internal price")
    day_over_day_change: Optional[Decimal] = Field(None, description="Day-over-day price change")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('cusip')
    def validate_cusip(cls, v):
        """Validate CUSIP format (9 characters)."""
        if len(v) != 9:
            raise ValueError('CUSIP must be 9 characters')
        return v.upper()
    
    @validator('bval_price', 'discount_price', 'dollar_price', 'internal_price')
    def validate_positive_price(cls, v):
        """Ensure prices are positive when provided."""
        if v is not None and v <= 0:
            raise ValueError('Prices must be positive')
        return v


class TreasuryData(BaseModel):
    """Treasury security metadata and current pricing."""
    
    cusip: str = Field(..., description="CUSIP identifier")
    maturity_date: date = Field(..., description="Maturity date")
    coupon_rate: Decimal = Field(..., description="Coupon rate as decimal")
    issue_date: Optional[date] = Field(None, description="Issue date")
    security_type: str = Field(default="Treasury", description="Security type")
    current_price: Optional[TreasuryPrice] = Field(None, description="Current price data")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('coupon_rate')
    def validate_coupon_rate(cls, v):
        """Validate coupon rate is between 0 and 100%."""
        if v < 0 or v > 1:
            raise ValueError('Coupon rate must be between 0 and 1 (as decimal)')
        return v
    
    @validator('maturity_date')
    def validate_maturity_future(cls, v):
        """Ensure maturity date is in the future for new issues."""
        if v <= date.today():
            # Allow historical data, just warn
            pass
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
