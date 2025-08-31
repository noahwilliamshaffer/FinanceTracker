"""
Core scoring engine for evaluating treasury securities.

This module implements the main ScoreCalculator class that combines multiple
market signals to generate composite scores for investment decision making.
The scoring system is designed to identify arbitrage opportunities and
mispricing in the treasury market.
"""

import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date, datetime
import structlog

from ..models.scoring import ScoreData, ScoreWeights
from ..models.treasury import TreasuryData, TreasuryPrice
from ..models.repo import RepoData
from .signals import (
    RepoSpreadSignal,
    PriceDivergenceSignal,
    VolumeSignal,
    VolatilitySignal
)

# Initialize structured logger for better debugging and audit trails
logger = structlog.get_logger(__name__)


def load_scoring_config(config_path: Optional[str] = None) -> ScoreWeights:
    """
    Load scoring configuration from YAML file.
    
    Args:
        config_path: Path to YAML configuration file. If None, uses default config.
        
    Returns:
        ScoreWeights: Validated scoring weights configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is malformed
        ValueError: If weights are invalid
    """
    if config_path is None:
        # Default to config/scoring.yaml relative to project root
        config_path = Path(__file__).parent.parent.parent / "config" / "scoring.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        logger.warning(
            "Scoring config file not found, using defaults",
            config_path=str(config_path)
        )
        return ScoreWeights()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Extract scoring weights from config
        weights_config = config_data.get('scoring_weights', {})
        
        logger.info(
            "Loaded scoring configuration",
            config_path=str(config_path),
            weights_count=len(weights_config)
        )
        
        return ScoreWeights(**weights_config)
        
    except yaml.YAMLError as e:
        logger.error(
            "Failed to parse scoring config YAML",
            config_path=str(config_path),
            error=str(e)
        )
        raise
    except Exception as e:
        logger.error(
            "Failed to load scoring config",
            config_path=str(config_path),
            error=str(e)
        )
        raise


class ScoreCalculator:
    """
    Main scoring engine that combines multiple market signals.
    
    The ScoreCalculator evaluates treasury securities by analyzing:
    1. Repo spread signals - funding cost advantages
    2. Price divergence signals - mispricing opportunities  
    3. Volume signals - liquidity and market depth
    4. Volatility signals - price stability and risk
    
    Each signal is calculated independently, then combined using configurable
    weights to produce a composite score from 0-100.
    """
    
    def __init__(self, weights: Optional[ScoreWeights] = None):
        """
        Initialize the score calculator.
        
        Args:
            weights: Scoring weights configuration. If None, loads from default config.
        """
        self.weights = weights or load_scoring_config()
        
        # Normalize weights to ensure they sum to 1.0
        if not self.weights.validate_total_weights():
            logger.warning(
                "Scoring weights don't sum to 1.0, normalizing",
                original_total=float(sum([
                    self.weights.repo_spread_weight,
                    self.weights.bval_divergence_weight,
                    self.weights.volume_weight,
                    self.weights.volatility_weight
                ]))
            )
            self.weights = self.weights.normalize_weights()
        
        # Initialize individual signal calculators
        self.repo_signal = RepoSpreadSignal(self.weights)
        self.divergence_signal = PriceDivergenceSignal(self.weights)
        self.volume_signal = VolumeSignal(self.weights)
        self.volatility_signal = VolatilitySignal(self.weights)
        
        logger.info(
            "ScoreCalculator initialized",
            repo_weight=float(self.weights.repo_spread_weight),
            divergence_weight=float(self.weights.bval_divergence_weight),
            volume_weight=float(self.weights.volume_weight),
            volatility_weight=float(self.weights.volatility_weight)
        )
    
    def calculate_score(
        self,
        cusip: str,
        treasury_data: TreasuryData,
        repo_data: Optional[RepoData] = None,
        historical_prices: Optional[List[TreasuryPrice]] = None,
        score_date: Optional[date] = None
    ) -> ScoreData:
        """
        Calculate composite score for a treasury security.
        
        Args:
            cusip: CUSIP identifier for the security
            treasury_data: Current treasury security data including pricing
            repo_data: Repo market data for spread analysis
            historical_prices: Historical price data for volatility calculation
            score_date: Date for score calculation (defaults to today)
            
        Returns:
            ScoreData: Complete scoring results with individual signal scores
            
        Raises:
            ValueError: If required data is missing or invalid
        """
        if score_date is None:
            score_date = date.today()
        
        logger.info(
            "Calculating score for security",
            cusip=cusip,
            score_date=score_date.isoformat()
        )
        
        # Calculate individual signal scores
        repo_score = self._calculate_repo_score(repo_data)
        divergence_score = self._calculate_divergence_score(treasury_data)
        volume_score = self._calculate_volume_score(repo_data)
        volatility_score = self._calculate_volatility_score(historical_prices)
        
        # Calculate composite score using weighted average
        composite_score = self._calculate_composite_score(
            repo_score, divergence_score, volume_score, volatility_score
        )
        
        # Calculate confidence based on data availability and quality
        confidence_score = self._calculate_confidence_score(
            treasury_data, repo_data, historical_prices
        )
        
        # Extract supporting data for transparency
        supporting_data = self._extract_supporting_data(
            treasury_data, repo_data, historical_prices
        )
        
        score_data = ScoreData(
            cusip=cusip,
            score_date=score_date,
            repo_spread_score=repo_score,
            bval_divergence_score=divergence_score,
            volume_score=volume_score,
            volatility_score=volatility_score,
            composite_score=composite_score,
            confidence_score=confidence_score,
            weights_used=self._serialize_weights(),
            **supporting_data
        )
        
        logger.info(
            "Score calculation completed",
            cusip=cusip,
            composite_score=float(composite_score) if composite_score else None,
            confidence_score=float(confidence_score) if confidence_score else None
        )
        
        return score_data
    
    def _calculate_repo_score(self, repo_data: Optional[RepoData]) -> Optional[Decimal]:
        """
        Calculate repo spread signal score.
        
        Higher scores indicate more attractive repo financing terms.
        Score ranges from 0-100 based on spread relative to historical norms.
        """
        if repo_data is None or repo_data.avg_spread is None:
            return None
        
        return self.repo_signal.calculate_score(repo_data)
    
    def _calculate_divergence_score(self, treasury_data: TreasuryData) -> Optional[Decimal]:
        """
        Calculate BVAL vs internal price divergence score.
        
        Higher scores indicate greater mispricing opportunities where
        internal pricing differs significantly from BVAL benchmarks.
        """
        if (treasury_data.current_price is None or 
            treasury_data.current_price.bval_price is None or
            treasury_data.current_price.internal_price is None):
            return None
        
        return self.divergence_signal.calculate_score(treasury_data.current_price)
    
    def _calculate_volume_score(self, repo_data: Optional[RepoData]) -> Optional[Decimal]:
        """
        Calculate volume/liquidity signal score.
        
        Higher scores indicate better liquidity and market depth,
        making positions easier to enter and exit.
        """
        if repo_data is None or repo_data.total_volume is None:
            return None
        
        return self.volume_signal.calculate_score(repo_data)
    
    def _calculate_volatility_score(
        self, 
        historical_prices: Optional[List[TreasuryPrice]]
    ) -> Optional[Decimal]:
        """
        Calculate price volatility signal score.
        
        Higher scores indicate more stable/predictable price movements,
        reducing execution risk for trading strategies.
        """
        if not historical_prices or len(historical_prices) < 5:
            return None
        
        return self.volatility_signal.calculate_score(historical_prices)
    
    def _calculate_composite_score(
        self,
        repo_score: Optional[Decimal],
        divergence_score: Optional[Decimal], 
        volume_score: Optional[Decimal],
        volatility_score: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        Calculate weighted composite score from individual signals.
        
        Only includes signals that have valid scores in the weighted average.
        If no signals are available, returns None.
        """
        scores = []
        weights = []
        
        # Include each signal if it has a valid score
        if repo_score is not None:
            scores.append(repo_score)
            weights.append(self.weights.repo_spread_weight)
        
        if divergence_score is not None:
            scores.append(divergence_score)
            weights.append(self.weights.bval_divergence_weight)
        
        if volume_score is not None:
            scores.append(volume_score)
            weights.append(self.weights.volume_weight)
        
        if volatility_score is not None:
            scores.append(volatility_score)
            weights.append(self.weights.volatility_weight)
        
        if not scores:
            return None
        
        # Calculate weighted average, normalizing weights to sum to 1.0
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        composite = sum(s * w for s, w in zip(scores, normalized_weights))
        
        return Decimal(str(composite))
    
    def _calculate_confidence_score(
        self,
        treasury_data: TreasuryData,
        repo_data: Optional[RepoData],
        historical_prices: Optional[List[TreasuryPrice]]
    ) -> Decimal:
        """
        Calculate confidence score based on data quality and completeness.
        
        Higher confidence scores indicate more reliable composite scores
        based on complete, recent, and high-quality input data.
        """
        confidence_factors = []
        
        # Treasury data completeness (0-25 points)
        treasury_completeness = 0
        if treasury_data.current_price:
            if treasury_data.current_price.bval_price is not None:
                treasury_completeness += 8
            if treasury_data.current_price.internal_price is not None:
                treasury_completeness += 8
            if treasury_data.current_price.dollar_price is not None:
                treasury_completeness += 5
            if treasury_data.current_price.day_over_day_change is not None:
                treasury_completeness += 4
        confidence_factors.append(treasury_completeness)
        
        # Repo data availability (0-25 points)
        repo_completeness = 0
        if repo_data:
            if repo_data.avg_spread is not None:
                repo_completeness += 10
            if repo_data.total_volume is not None:
                repo_completeness += 10
            spread_count = sum(1 for spread in [
                repo_data.overnight_spread,
                repo_data.one_week_spread,
                repo_data.one_month_spread,
                repo_data.three_month_spread
            ] if spread is not None)
            repo_completeness += spread_count * 1.25  # Up to 5 points
        confidence_factors.append(repo_completeness)
        
        # Historical data depth (0-25 points)
        historical_completeness = 0
        if historical_prices:
            data_points = len(historical_prices)
            if data_points >= 30:
                historical_completeness = 25
            elif data_points >= 14:
                historical_completeness = 20
            elif data_points >= 7:
                historical_completeness = 15
            elif data_points >= 3:
                historical_completeness = 10
            else:
                historical_completeness = 5
        confidence_factors.append(historical_completeness)
        
        # Data freshness (0-25 points)
        freshness_score = 25  # Assume fresh data, could be enhanced with timestamp checks
        confidence_factors.append(freshness_score)
        
        total_confidence = sum(confidence_factors)
        return Decimal(str(min(100, total_confidence)))
    
    def _extract_supporting_data(
        self,
        treasury_data: TreasuryData,
        repo_data: Optional[RepoData],
        historical_prices: Optional[List[TreasuryPrice]]
    ) -> Dict[str, Any]:
        """Extract supporting data for transparency in score calculation."""
        supporting = {}
        
        # Repo spread data
        if repo_data and repo_data.avg_spread is not None:
            supporting['repo_spread_bps'] = repo_data.avg_spread * 10000  # Convert to bps
        
        # Price divergence data
        if (treasury_data.current_price and 
            treasury_data.current_price.bval_price and
            treasury_data.current_price.internal_price):
            supporting['bval_internal_diff'] = (
                treasury_data.current_price.internal_price - 
                treasury_data.current_price.bval_price
            )
        
        # Volume data
        if repo_data and repo_data.total_volume is not None:
            supporting['daily_volume'] = repo_data.total_volume
        
        # Volatility data
        if historical_prices and len(historical_prices) >= 2:
            prices = [float(p.bval_price or p.internal_price or 0) 
                     for p in historical_prices 
                     if p.bval_price or p.internal_price]
            if len(prices) >= 2:
                import statistics
                supporting['price_volatility'] = Decimal(str(statistics.stdev(prices)))
        
        return supporting
    
    def _serialize_weights(self) -> Dict[str, Any]:
        """Serialize current weights configuration for audit trail."""
        return {
            'repo_spread_weight': float(self.weights.repo_spread_weight),
            'bval_divergence_weight': float(self.weights.bval_divergence_weight),
            'volume_weight': float(self.weights.volume_weight),
            'volatility_weight': float(self.weights.volatility_weight),
            'lookback_days': self.weights.lookback_days,
            'significant_spread_threshold': float(self.weights.significant_spread_threshold),
            'significant_divergence_threshold': float(self.weights.significant_divergence_threshold)
        }
