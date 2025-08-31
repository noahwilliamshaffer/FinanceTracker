"""
Scoring models for evaluating market signals and pricing divergences.

This module provides data models for internal scoring algorithms that weight
various market signals to generate composite scores for treasury securities.
The scoring system helps identify arbitrage opportunities and pricing anomalies
by analyzing repo spreads and internal vs external pricing divergences.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ScoreWeights(BaseModel):
    """
    Configuration model for scoring algorithm weights.
    
    This model defines the relative importance of different market signals
    in the composite scoring algorithm. Weights are normalized to sum to 1.0
    to ensure consistent scoring across different market conditions.
    """
    
    # Repo spread signal weights - measure funding cost advantages
    repo_spread_weight: Decimal = Field(
        default=Decimal('0.4'), 
        description="Weight for repo spread signal (0.0-1.0)"
    )
    
    # Pricing divergence weights - identify mispricing opportunities  
    bval_divergence_weight: Decimal = Field(
        default=Decimal('0.3'),
        description="Weight for BVAL vs internal price divergence (0.0-1.0)"
    )
    
    # Volume and liquidity weights - adjust for market depth
    volume_weight: Decimal = Field(
        default=Decimal('0.2'),
        description="Weight for trading volume signal (0.0-1.0)"
    )
    
    # Volatility and risk weights - account for price stability
    volatility_weight: Decimal = Field(
        default=Decimal('0.1'),
        description="Weight for price volatility signal (0.0-1.0)"
    )
    
    # Advanced scoring parameters
    lookback_days: int = Field(
        default=30,
        description="Number of days to look back for trend analysis"
    )
    
    # Threshold parameters for signal classification
    significant_spread_threshold: Decimal = Field(
        default=Decimal('5.0'),
        description="Threshold in basis points for significant repo spreads"
    )
    
    significant_divergence_threshold: Decimal = Field(
        default=Decimal('0.25'),
        description="Threshold in price points for significant BVAL divergence"
    )
    
    @validator('repo_spread_weight', 'bval_divergence_weight', 'volume_weight', 'volatility_weight')
    def validate_weight_range(cls, v):
        """Ensure all weights are between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError('Weights must be between 0.0 and 1.0')
        return v
    
    def validate_total_weights(self) -> bool:
        """
        Validate that all weights sum to approximately 1.0.
        
        Returns:
            bool: True if weights sum to 1.0 (within tolerance), False otherwise
        """
        total = (self.repo_spread_weight + self.bval_divergence_weight + 
                self.volume_weight + self.volatility_weight)
        return abs(float(total) - 1.0) < 0.001
    
    def normalize_weights(self) -> 'ScoreWeights':
        """
        Return a new ScoreWeights instance with normalized weights.
        
        This ensures weights sum to exactly 1.0 while preserving their
        relative proportions.
        """
        total = (self.repo_spread_weight + self.bval_divergence_weight + 
                self.volume_weight + self.volatility_weight)
        
        if total == 0:
            raise ValueError("Cannot normalize weights that sum to zero")
        
        return ScoreWeights(
            repo_spread_weight=self.repo_spread_weight / total,
            bval_divergence_weight=self.bval_divergence_weight / total,
            volume_weight=self.volume_weight / total,
            volatility_weight=self.volatility_weight / total,
            lookback_days=self.lookback_days,
            significant_spread_threshold=self.significant_spread_threshold,
            significant_divergence_threshold=self.significant_divergence_threshold
        )


class ScoreData(BaseModel):
    """
    Composite score data for a treasury security.
    
    This model contains the calculated scores and individual signal components
    that contribute to the overall investment/trading recommendation for a
    specific CUSIP on a given date.
    """
    
    cusip: str = Field(..., description="CUSIP identifier")
    score_date: date = Field(..., description="Date of score calculation")
    
    # Individual signal scores (0-100 scale)
    repo_spread_score: Optional[Decimal] = Field(
        None, 
        description="Repo spread signal score (0-100, higher = more attractive funding)"
    )
    
    bval_divergence_score: Optional[Decimal] = Field(
        None,
        description="BVAL divergence score (0-100, higher = greater mispricing opportunity)"
    )
    
    volume_score: Optional[Decimal] = Field(
        None,
        description="Volume/liquidity score (0-100, higher = more liquid)"
    )
    
    volatility_score: Optional[Decimal] = Field(
        None,
        description="Volatility score (0-100, higher = more stable/predictable)"
    )
    
    # Composite scores
    composite_score: Optional[Decimal] = Field(
        None,
        description="Weighted composite score (0-100, higher = more attractive)"
    )
    
    confidence_score: Optional[Decimal] = Field(
        None,
        description="Confidence in score accuracy (0-100, based on data quality)"
    )
    
    # Supporting data for score calculation
    repo_spread_bps: Optional[Decimal] = Field(
        None,
        description="Current repo spread in basis points"
    )
    
    bval_internal_diff: Optional[Decimal] = Field(
        None,
        description="Difference between BVAL and internal price"
    )
    
    daily_volume: Optional[Decimal] = Field(
        None,
        description="Daily trading volume"
    )
    
    price_volatility: Optional[Decimal] = Field(
        None,
        description="Recent price volatility (standard deviation)"
    )
    
    # Metadata
    weights_used: Optional[Dict[str, Any]] = Field(
        None,
        description="Scoring weights configuration used for calculation"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when score was calculated"
    )
    
    @validator('cusip')
    def validate_cusip(cls, v):
        """Validate CUSIP format (9 characters)."""
        if len(v) != 9:
            raise ValueError('CUSIP must be 9 characters')
        return v.upper()
    
    @validator('repo_spread_score', 'bval_divergence_score', 'volume_score', 
              'volatility_score', 'composite_score', 'confidence_score')
    def validate_score_range(cls, v):
        """Ensure all scores are between 0 and 100 when provided."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Scores must be between 0 and 100')
        return v
    
    def get_risk_category(self) -> str:
        """
        Categorize the investment based on composite score.
        
        Returns:
            str: Risk category ('High Opportunity', 'Medium Opportunity', 
                 'Low Opportunity', 'Avoid')
        """
        if self.composite_score is None:
            return "Unknown"
        
        score = float(self.composite_score)
        
        if score >= 80:
            return "High Opportunity"
        elif score >= 60:
            return "Medium Opportunity" 
        elif score >= 40:
            return "Low Opportunity"
        else:
            return "Avoid"
    
    def get_confidence_category(self) -> str:
        """
        Categorize the confidence level in the score.
        
        Returns:
            str: Confidence category ('High', 'Medium', 'Low')
        """
        if self.confidence_score is None:
            return "Unknown"
        
        confidence = float(self.confidence_score)
        
        if confidence >= 75:
            return "High"
        elif confidence >= 50:
            return "Medium"
        else:
            return "Low"
    
    class Config:
        """Pydantic configuration for JSON serialization."""
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
