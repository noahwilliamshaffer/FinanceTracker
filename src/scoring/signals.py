"""
Individual signal calculation modules for market analysis.

This module contains specialized classes for calculating individual market
signals that feed into the composite scoring algorithm. Each signal class
focuses on a specific aspect of market behavior and pricing dynamics.
"""

import statistics
from typing import List, Optional
from decimal import Decimal
from abc import ABC, abstractmethod
import structlog

from ..models.scoring import ScoreWeights
from ..models.treasury import TreasuryPrice
from ..models.repo import RepoData

# Initialize structured logger for signal calculations
logger = structlog.get_logger(__name__)


class SignalCalculator(ABC):
    """
    Abstract base class for individual signal calculators.
    
    All signal calculators should inherit from this class and implement
    the calculate_score method to return a score between 0-100.
    """
    
    def __init__(self, weights: ScoreWeights):
        """Initialize with scoring weights configuration."""
        self.weights = weights
    
    @abstractmethod
    def calculate_score(self, data) -> Optional[Decimal]:
        """
        Calculate signal score from input data.
        
        Args:
            data: Input data specific to the signal type
            
        Returns:
            Decimal: Score between 0-100, or None if calculation not possible
        """
        pass


class RepoSpreadSignal(SignalCalculator):
    """
    Calculates scores based on repo spread analysis.
    
    Repo spreads indicate funding cost advantages - wider spreads suggest
    better opportunities to profit from financing cost differentials.
    The score considers both absolute spread levels and relative positioning
    versus historical norms.
    """
    
    def calculate_score(self, repo_data: RepoData) -> Optional[Decimal]:
        """
        Calculate repo spread signal score.
        
        The scoring algorithm considers:
        - Absolute spread level (wider = higher score)
        - Spread consistency across terms (more consistent = higher score)
        - Volume support (higher volume = higher confidence)
        
        Args:
            repo_data: Repo market data containing spread information
            
        Returns:
            Decimal: Score 0-100, where higher scores indicate more attractive spreads
        """
        if repo_data.avg_spread is None:
            logger.debug("No average spread data available", cusip=repo_data.cusip)
            return None
        
        avg_spread_bps = float(repo_data.avg_spread) * 10000  # Convert to basis points
        
        logger.debug(
            "Calculating repo spread score",
            cusip=repo_data.cusip,
            avg_spread_bps=avg_spread_bps
        )
        
        # Base score from absolute spread level
        # Spreads above threshold get higher scores
        threshold_bps = float(self.weights.significant_spread_threshold)
        
        if avg_spread_bps <= 0:
            base_score = 0
        elif avg_spread_bps >= threshold_bps * 2:
            base_score = 100
        else:
            # Linear scaling from 0 to threshold*2
            base_score = min(100, (avg_spread_bps / (threshold_bps * 2)) * 100)
        
        # Consistency bonus: reward securities with spreads across multiple terms
        consistency_bonus = self._calculate_spread_consistency(repo_data)
        
        # Volume confidence adjustment
        volume_adjustment = self._calculate_volume_confidence(repo_data)
        
        # Combine components
        final_score = base_score * (1 + consistency_bonus * 0.1) * volume_adjustment
        final_score = min(100, max(0, final_score))
        
        logger.debug(
            "Repo spread score calculated",
            cusip=repo_data.cusip,
            base_score=base_score,
            consistency_bonus=consistency_bonus,
            volume_adjustment=volume_adjustment,
            final_score=final_score
        )
        
        return Decimal(str(final_score))
    
    def _calculate_spread_consistency(self, repo_data: RepoData) -> float:
        """
        Calculate bonus for consistent spreads across different terms.
        
        Returns:
            float: Consistency bonus factor (0.0 to 1.0)
        """
        spreads = [
            repo_data.overnight_spread,
            repo_data.one_week_spread,
            repo_data.one_month_spread,
            repo_data.three_month_spread
        ]
        
        valid_spreads = [float(s) for s in spreads if s is not None]
        
        if len(valid_spreads) <= 1:
            return 0.0
        
        # Higher consistency (lower standard deviation) gets higher bonus
        try:
            spread_std = statistics.stdev(valid_spreads)
            avg_spread = statistics.mean(valid_spreads)
            
            if avg_spread == 0:
                return 0.0
            
            # Coefficient of variation - lower is more consistent
            cv = spread_std / abs(avg_spread)
            
            # Convert to bonus (lower CV = higher bonus)
            consistency_bonus = max(0, 1 - cv * 2)  # Scale CV to 0-1 range
            
            return consistency_bonus
            
        except statistics.StatisticsError:
            return 0.0


    def _calculate_volume_confidence(self, repo_data: RepoData) -> float:
        """
        Calculate confidence adjustment based on trading volume.
        
        Returns:
            float: Volume confidence factor (0.5 to 1.0)
        """
        if repo_data.total_volume is None:
            return 0.8  # Moderate confidence when volume unknown
        
        volume = float(repo_data.total_volume)
        
        # Volume thresholds (these could be made configurable)
        high_volume_threshold = 1000000  # $1M
        low_volume_threshold = 100000    # $100K
        
        if volume >= high_volume_threshold:
            return 1.0  # Full confidence
        elif volume >= low_volume_threshold:
            # Linear scaling between thresholds
            ratio = (volume - low_volume_threshold) / (high_volume_threshold - low_volume_threshold)
            return 0.8 + (ratio * 0.2)  # Scale from 0.8 to 1.0
        else:
            return 0.5  # Low confidence for low volume


class PriceDivergenceSignal(SignalCalculator):
    """
    Calculates scores based on BVAL vs internal pricing divergence.
    
    Significant divergences between internal pricing models and external
    benchmarks like BVAL can indicate mispricing opportunities. The score
    considers both the magnitude of divergence and the direction.
    """
    
    def calculate_score(self, price_data: TreasuryPrice) -> Optional[Decimal]:
        """
        Calculate price divergence signal score.
        
        The scoring considers:
        - Magnitude of price difference (larger = higher score)
        - Direction that favors internal pricing model
        - Relative size of divergence vs security price
        
        Args:
            price_data: Treasury price data with BVAL and internal prices
            
        Returns:
            Decimal: Score 0-100, higher scores indicate greater opportunities
        """
        if price_data.bval_price is None or price_data.internal_price is None:
            logger.debug("Missing price data for divergence calculation", cusip=price_data.cusip)
            return None
        
        bval_price = float(price_data.bval_price)
        internal_price = float(price_data.internal_price)
        
        # Calculate absolute and relative divergence
        absolute_diff = abs(internal_price - bval_price)
        relative_diff = absolute_diff / bval_price if bval_price != 0 else 0
        
        logger.debug(
            "Calculating price divergence score",
            cusip=price_data.cusip,
            bval_price=bval_price,
            internal_price=internal_price,
            absolute_diff=absolute_diff,
            relative_diff=relative_diff
        )
        
        # Score based on relative divergence magnitude
        threshold = float(self.weights.significant_divergence_threshold)
        
        if relative_diff == 0:
            base_score = 0
        elif relative_diff >= threshold * 2:
            base_score = 100
        else:
            # Linear scaling up to 2x threshold
            base_score = (relative_diff / (threshold * 2)) * 100
        
        # Direction bonus: prefer when internal price is favorable
        # This could be enhanced with market-specific logic
        direction_bonus = 1.0
        if internal_price < bval_price:
            # Internal price is lower - potential buying opportunity
            direction_bonus = 1.1
        elif internal_price > bval_price:
            # Internal price is higher - potential selling opportunity  
            direction_bonus = 1.05
        
        final_score = base_score * direction_bonus
        final_score = min(100, max(0, final_score))
        
        logger.debug(
            "Price divergence score calculated",
            cusip=price_data.cusip,
            base_score=base_score,
            direction_bonus=direction_bonus,
            final_score=final_score
        )
        
        return Decimal(str(final_score))


class VolumeSignal(SignalCalculator):
    """
    Calculates scores based on trading volume and liquidity indicators.
    
    Higher volume generally indicates better liquidity, making it easier
    to enter and exit positions. The score considers both absolute volume
    levels and volume trends.
    """
    
    def calculate_score(self, repo_data: RepoData) -> Optional[Decimal]:
        """
        Calculate volume signal score.
        
        Args:
            repo_data: Repo data containing volume information
            
        Returns:
            Decimal: Score 0-100, higher scores indicate better liquidity
        """
        if repo_data.total_volume is None:
            logger.debug("No volume data available", cusip=repo_data.cusip)
            return None
        
        volume = float(repo_data.total_volume)
        
        logger.debug(
            "Calculating volume score",
            cusip=repo_data.cusip,
            total_volume=volume
        )
        
        # Volume scoring thresholds (could be made configurable)
        excellent_volume = 5000000  # $5M
        good_volume = 1000000      # $1M
        fair_volume = 250000       # $250K
        poor_volume = 50000        # $50K
        
        if volume >= excellent_volume:
            score = 100
        elif volume >= good_volume:
            # Scale from 80 to 100
            ratio = (volume - good_volume) / (excellent_volume - good_volume)
            score = 80 + (ratio * 20)
        elif volume >= fair_volume:
            # Scale from 60 to 80
            ratio = (volume - fair_volume) / (good_volume - fair_volume)
            score = 60 + (ratio * 20)
        elif volume >= poor_volume:
            # Scale from 30 to 60
            ratio = (volume - poor_volume) / (fair_volume - poor_volume)
            score = 30 + (ratio * 30)
        else:
            # Scale from 0 to 30 for very low volume
            score = min(30, (volume / poor_volume) * 30)
        
        final_score = min(100, max(0, score))
        
        logger.debug(
            "Volume score calculated",
            cusip=repo_data.cusip,
            volume=volume,
            final_score=final_score
        )
        
        return Decimal(str(final_score))


class VolatilitySignal(SignalCalculator):
    """
    Calculates scores based on price volatility analysis.
    
    Lower volatility generally indicates more predictable price movements
    and reduced execution risk. The score considers recent price stability
    and trend consistency.
    """
    
    def calculate_score(self, historical_prices: List[TreasuryPrice]) -> Optional[Decimal]:
        """
        Calculate volatility signal score.
        
        Args:
            historical_prices: List of historical price data
            
        Returns:
            Decimal: Score 0-100, higher scores indicate lower volatility
        """
        if len(historical_prices) < 2:
            logger.debug("Insufficient price history for volatility calculation")
            return None
        
        # Extract prices for volatility calculation
        # Prefer BVAL prices, fall back to internal prices
        prices = []
        for price_data in historical_prices:
            if price_data.bval_price is not None:
                prices.append(float(price_data.bval_price))
            elif price_data.internal_price is not None:
                prices.append(float(price_data.internal_price))
        
        if len(prices) < 2:
            logger.debug("Insufficient valid prices for volatility calculation")
            return None
        
        logger.debug(
            "Calculating volatility score",
            price_count=len(prices),
            price_range=(min(prices), max(prices))
        )
        
        # Calculate price volatility metrics
        try:
            price_mean = statistics.mean(prices)
            price_std = statistics.stdev(prices)
            
            if price_mean == 0:
                return Decimal('50')  # Neutral score for zero prices
            
            # Coefficient of variation (volatility relative to price level)
            cv = price_std / abs(price_mean)
            
            # Convert CV to score (lower volatility = higher score)
            # Typical CV for treasuries might range from 0.01 to 0.1
            max_acceptable_cv = 0.05  # 5% CV as threshold
            
            if cv <= 0:
                score = 100
            elif cv >= max_acceptable_cv * 2:
                score = 0
            else:
                # Linear scaling - lower CV gets higher score
                score = 100 * (1 - cv / (max_acceptable_cv * 2))
            
            # Additional stability bonus for consistent trend
            trend_bonus = self._calculate_trend_consistency(prices)
            final_score = score * (1 + trend_bonus * 0.1)
            
            final_score = min(100, max(0, final_score))
            
            logger.debug(
                "Volatility score calculated",
                cv=cv,
                base_score=score,
                trend_bonus=trend_bonus,
                final_score=final_score
            )
            
            return Decimal(str(final_score))
            
        except statistics.StatisticsError as e:
            logger.warning("Statistics calculation error in volatility signal", error=str(e))
            return None
    
    def _calculate_trend_consistency(self, prices: List[float]) -> float:
        """
        Calculate bonus for consistent price trends.
        
        Args:
            prices: List of prices in chronological order
            
        Returns:
            float: Trend consistency bonus (0.0 to 1.0)
        """
        if len(prices) < 3:
            return 0.0
        
        # Calculate price changes
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        if not changes:
            return 0.0
        
        # Count directional consistency
        positive_changes = sum(1 for change in changes if change > 0)
        negative_changes = sum(1 for change in changes if change < 0)
        total_changes = len(changes)
        
        # Higher consistency when most changes are in same direction
        max_directional = max(positive_changes, negative_changes)
        consistency_ratio = max_directional / total_changes
        
        # Bonus for high directional consistency (> 70%)
        if consistency_ratio > 0.7:
            return (consistency_ratio - 0.7) / 0.3  # Scale 0.7-1.0 to 0.0-1.0
        else:
            return 0.0
