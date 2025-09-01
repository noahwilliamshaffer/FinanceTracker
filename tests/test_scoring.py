"""
Unit tests for scoring algorithms and signal calculations.

Tests the core scoring logic, signal calculators, and weight
configuration functionality.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
import statistics

from src.scoring.scoring import ScoreCalculator, load_scoring_config
from src.scoring.signals import (
    RepoSpreadSignal, PriceDivergenceSignal, 
    VolumeSignal, VolatilitySignal
)
from src.models.treasury import TreasuryData, TreasuryPrice
from src.models.repo import RepoData, RepoSpread
from src.models.scoring import ScoreWeights, ScoreData


class TestScoreCalculator:
    """Test cases for the main ScoreCalculator class."""
    
    def test_score_calculator_initialization(self):
        """Test ScoreCalculator initialization with default weights."""
        calculator = ScoreCalculator()
        
        assert calculator.weights is not None
        assert calculator.weights.validate_total_weights()
        assert calculator.repo_signal is not None
        assert calculator.divergence_signal is not None
        assert calculator.volume_signal is not None
        assert calculator.volatility_signal is not None
    
    def test_score_calculator_custom_weights(self):
        """Test ScoreCalculator with custom weights."""
        custom_weights = ScoreWeights(
            repo_spread_weight=Decimal("0.5"),
            bval_divergence_weight=Decimal("0.3"),
            volume_weight=Decimal("0.15"),
            volatility_weight=Decimal("0.05")
        )
        
        calculator = ScoreCalculator(custom_weights)
        assert calculator.weights == custom_weights
        assert calculator.weights.validate_total_weights()
    
    def test_calculate_score_complete_data(self):
        """Test score calculation with complete data."""
        calculator = ScoreCalculator()
        
        # Create test data
        treasury_data = TreasuryData(
            cusip="912828XG8",
            maturity_date=date(2034, 2, 15),
            coupon_rate=Decimal("0.0425"),
            current_price=TreasuryPrice(
                cusip="912828XG8",
                price_date=date.today(),
                bval_price=Decimal("99.5000"),
                internal_price=Decimal("99.4500")
            )
        )
        
        repo_data = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            overnight_spread=Decimal("0.0010"),  # 10 bps
            one_week_spread=Decimal("0.0015"),   # 15 bps
            avg_spread=Decimal("0.0012"),        # 12 bps
            total_volume=Decimal("2000000")      # $2M
        )
        
        # Create historical prices for volatility
        historical_prices = []
        base_price = Decimal("99.5000")
        for i in range(10):
            price_date = date.today() - timedelta(days=i)
            price_variation = Decimal(str((i % 3 - 1) * 0.01))  # Small variations
            historical_prices.append(TreasuryPrice(
                cusip="912828XG8",
                price_date=price_date,
                bval_price=base_price + price_variation,
                internal_price=base_price + price_variation - Decimal("0.005")
            ))
        
        # Calculate score
        score_data = calculator.calculate_score(
            cusip="912828XG8",
            treasury_data=treasury_data,
            repo_data=repo_data,
            historical_prices=historical_prices
        )
        
        # Verify results
        assert score_data.cusip == "912828XG8"
        assert score_data.score_date == date.today()
        assert score_data.composite_score is not None
        assert 0 <= score_data.composite_score <= 100
        assert score_data.confidence_score is not None
        assert score_data.weights_used is not None
        
        # Individual scores should be calculated
        assert score_data.repo_spread_score is not None
        assert score_data.bval_divergence_score is not None
        assert score_data.volume_score is not None
        assert score_data.volatility_score is not None
    
    def test_calculate_score_partial_data(self):
        """Test score calculation with partial data."""
        calculator = ScoreCalculator()
        
        # Treasury data without pricing
        treasury_data = TreasuryData(
            cusip="912828XG8",
            maturity_date=date(2034, 2, 15),
            coupon_rate=Decimal("0.0425")
            # No current_price
        )
        
        # Repo data with limited spreads
        repo_data = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            overnight_spread=Decimal("0.0010")
            # No other spreads or volume
        )
        
        score_data = calculator.calculate_score(
            cusip="912828XG8",
            treasury_data=treasury_data,
            repo_data=repo_data
        )
        
        # Should still calculate score with available data
        assert score_data.cusip == "912828XG8"
        assert score_data.composite_score is not None
        
        # Some scores may be None due to missing data
        assert score_data.bval_divergence_score is None  # No pricing data
        assert score_data.volatility_score is None       # No historical data
    
    def test_calculate_score_no_data(self):
        """Test score calculation with minimal data."""
        calculator = ScoreCalculator()
        
        treasury_data = TreasuryData(
            cusip="912828XG8",
            maturity_date=date(2034, 2, 15),
            coupon_rate=Decimal("0.0425")
        )
        
        score_data = calculator.calculate_score(
            cusip="912828XG8",
            treasury_data=treasury_data
        )
        
        # Should return score data even with minimal input
        assert score_data.cusip == "912828XG8"
        # Composite score may be None if no signals available
        # Confidence should be low
        assert score_data.confidence_score is not None
        assert score_data.confidence_score < 50  # Low confidence


class TestRepoSpreadSignal:
    """Test cases for repo spread signal calculation."""
    
    def test_repo_spread_signal_calculation(self):
        """Test basic repo spread signal calculation."""
        weights = ScoreWeights()
        signal = RepoSpreadSignal(weights)
        
        repo_data = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            avg_spread=Decimal("0.0015"),  # 15 bps
            total_volume=Decimal("1000000")
        )
        
        score = signal.calculate_score(repo_data)
        
        assert score is not None
        assert 0 <= score <= 100
        assert isinstance(score, Decimal)
    
    def test_repo_spread_high_spread(self):
        """Test repo spread signal with high spread."""
        weights = ScoreWeights(significant_spread_threshold=Decimal("5.0"))
        signal = RepoSpreadSignal(weights)
        
        repo_data = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            avg_spread=Decimal("0.0020"),  # 20 bps (high)
            total_volume=Decimal("5000000")  # High volume
        )
        
        score = signal.calculate_score(repo_data)
        
        # High spread should result in higher score
        assert score is not None
        assert score > 50  # Should be above average
    
    def test_repo_spread_consistency_bonus(self):
        """Test consistency bonus calculation."""
        weights = ScoreWeights()
        signal = RepoSpreadSignal(weights)
        
        # Consistent spreads across terms
        consistent_repo = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            overnight_spread=Decimal("0.0015"),
            one_week_spread=Decimal("0.0015"),
            one_month_spread=Decimal("0.0015"),
            three_month_spread=Decimal("0.0015"),
            avg_spread=Decimal("0.0015")
        )
        
        # Inconsistent spreads
        inconsistent_repo = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            overnight_spread=Decimal("0.0005"),
            one_week_spread=Decimal("0.0025"),
            one_month_spread=Decimal("0.0010"),
            three_month_spread=Decimal("0.0030"),
            avg_spread=Decimal("0.0015")
        )
        
        consistent_score = signal.calculate_score(consistent_repo)
        inconsistent_score = signal.calculate_score(inconsistent_repo)
        
        # Consistent spreads should get higher score
        assert consistent_score > inconsistent_score
    
    def test_repo_spread_no_data(self):
        """Test repo spread signal with no spread data."""
        weights = ScoreWeights()
        signal = RepoSpreadSignal(weights)
        
        repo_data = RepoData(
            cusip="912828XG8",
            data_date=date.today()
            # No spread data
        )
        
        score = signal.calculate_score(repo_data)
        assert score is None


class TestPriceDivergenceSignal:
    """Test cases for price divergence signal calculation."""
    
    def test_price_divergence_calculation(self):
        """Test basic price divergence calculation."""
        weights = ScoreWeights()
        signal = PriceDivergenceSignal(weights)
        
        price_data = TreasuryPrice(
            cusip="912828XG8",
            price_date=date.today(),
            bval_price=Decimal("99.5000"),
            internal_price=Decimal("99.4500")  # 0.05 divergence
        )
        
        score = signal.calculate_score(price_data)
        
        assert score is not None
        assert 0 <= score <= 100
        assert isinstance(score, Decimal)
    
    def test_large_divergence(self):
        """Test signal with large price divergence."""
        weights = ScoreWeights(significant_divergence_threshold=Decimal("0.25"))
        signal = PriceDivergenceSignal(weights)
        
        price_data = TreasuryPrice(
            cusip="912828XG8",
            price_date=date.today(),
            bval_price=Decimal("99.5000"),
            internal_price=Decimal("99.0000")  # 0.50 divergence (large)
        )
        
        score = signal.calculate_score(price_data)
        
        # Large divergence should result in high score
        assert score is not None
        assert score > 80  # Should be high opportunity
    
    def test_no_divergence(self):
        """Test signal with no price divergence."""
        weights = ScoreWeights()
        signal = PriceDivergenceSignal(weights)
        
        price_data = TreasuryPrice(
            cusip="912828XG8",
            price_date=date.today(),
            bval_price=Decimal("99.5000"),
            internal_price=Decimal("99.5000")  # No divergence
        )
        
        score = signal.calculate_score(price_data)
        
        # No divergence should result in low score
        assert score is not None
        assert score == 0  # No opportunity
    
    def test_missing_price_data(self):
        """Test signal with missing price data."""
        weights = ScoreWeights()
        signal = PriceDivergenceSignal(weights)
        
        price_data = TreasuryPrice(
            cusip="912828XG8",
            price_date=date.today(),
            bval_price=Decimal("99.5000")
            # Missing internal_price
        )
        
        score = signal.calculate_score(price_data)
        assert score is None


class TestVolumeSignal:
    """Test cases for volume signal calculation."""
    
    def test_volume_signal_calculation(self):
        """Test basic volume signal calculation."""
        weights = ScoreWeights()
        signal = VolumeSignal(weights)
        
        repo_data = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            total_volume=Decimal("2000000")  # $2M
        )
        
        score = signal.calculate_score(repo_data)
        
        assert score is not None
        assert 0 <= score <= 100
        assert isinstance(score, Decimal)
    
    def test_high_volume_score(self):
        """Test volume signal with high volume."""
        weights = ScoreWeights()
        signal = VolumeSignal(weights)
        
        high_volume_repo = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            total_volume=Decimal("10000000")  # $10M (high)
        )
        
        low_volume_repo = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            total_volume=Decimal("100000")  # $100K (low)
        )
        
        high_score = signal.calculate_score(high_volume_repo)
        low_score = signal.calculate_score(low_volume_repo)
        
        # High volume should get higher score
        assert high_score > low_score
        assert high_score > 80  # Should be in excellent range
        assert low_score < 50   # Should be in poor range
    
    def test_no_volume_data(self):
        """Test volume signal with no volume data."""
        weights = ScoreWeights()
        signal = VolumeSignal(weights)
        
        repo_data = RepoData(
            cusip="912828XG8",
            data_date=date.today()
            # No volume data
        )
        
        score = signal.calculate_score(repo_data)
        assert score is None


class TestVolatilitySignal:
    """Test cases for volatility signal calculation."""
    
    def test_volatility_signal_calculation(self):
        """Test basic volatility signal calculation."""
        weights = ScoreWeights()
        signal = VolatilitySignal(weights)
        
        # Create historical prices with moderate volatility
        historical_prices = []
        base_price = 99.5
        for i in range(10):
            price_variation = (i % 3 - 1) * 0.01  # Small variations
            historical_prices.append(TreasuryPrice(
                cusip="912828XG8",
                price_date=date.today() - timedelta(days=i),
                bval_price=Decimal(str(base_price + price_variation))
            ))
        
        score = signal.calculate_score(historical_prices)
        
        assert score is not None
        assert 0 <= score <= 100
        assert isinstance(score, Decimal)
    
    def test_low_volatility_high_score(self):
        """Test that low volatility results in high score."""
        weights = ScoreWeights()
        signal = VolatilitySignal(weights)
        
        # Low volatility prices (very stable)
        stable_prices = []
        for i in range(10):
            stable_prices.append(TreasuryPrice(
                cusip="912828XG8",
                price_date=date.today() - timedelta(days=i),
                bval_price=Decimal("99.5000")  # No variation
            ))
        
        # High volatility prices
        volatile_prices = []
        base_price = 99.5
        for i in range(10):
            price_variation = (i % 2) * 0.5  # Large variations
            volatile_prices.append(TreasuryPrice(
                cusip="912828XG8",
                price_date=date.today() - timedelta(days=i),
                bval_price=Decimal(str(base_price + price_variation))
            ))
        
        stable_score = signal.calculate_score(stable_prices)
        volatile_score = signal.calculate_score(volatile_prices)
        
        # Stable prices should get higher score
        assert stable_score > volatile_score
        assert stable_score > 90  # Very high score for no volatility
        assert volatile_score < 30  # Low score for high volatility
    
    def test_insufficient_data(self):
        """Test volatility signal with insufficient data."""
        weights = ScoreWeights()
        signal = VolatilitySignal(weights)
        
        # Only one price point
        single_price = [TreasuryPrice(
            cusip="912828XG8",
            price_date=date.today(),
            bval_price=Decimal("99.5000")
        )]
        
        score = signal.calculate_score(single_price)
        assert score is None
        
        # Empty list
        score = signal.calculate_score([])
        assert score is None
    
    def test_trend_consistency_bonus(self):
        """Test trend consistency bonus calculation."""
        weights = ScoreWeights()
        signal = VolatilitySignal(weights)
        
        # Consistent upward trend
        trending_prices = []
        for i in range(10):
            price = 99.0 + (i * 0.01)  # Steady increase
            trending_prices.append(TreasuryPrice(
                cusip="912828XG8",
                price_date=date.today() - timedelta(days=9-i),
                bval_price=Decimal(str(price))
            ))
        
        # Random price movements
        random_prices = []
        prices = [99.0, 99.1, 98.9, 99.2, 98.8, 99.3, 98.7, 99.4, 98.6, 99.5]
        for i, price in enumerate(prices):
            random_prices.append(TreasuryPrice(
                cusip="912828XG8",
                price_date=date.today() - timedelta(days=9-i),
                bval_price=Decimal(str(price))
            ))
        
        trending_score = signal.calculate_score(trending_prices)
        random_score = signal.calculate_score(random_prices)
        
        # Trending prices should get bonus for consistency
        assert trending_score > random_score


class TestScoringConfiguration:
    """Test cases for scoring configuration loading."""
    
    @patch('src.scoring.scoring.Path')
    @patch('builtins.open')
    @patch('yaml.safe_load')
    def test_load_scoring_config_success(self, mock_yaml, mock_open, mock_path):
        """Test successful configuration loading."""
        # Mock file system
        mock_path.return_value.exists.return_value = True
        
        # Mock YAML content
        mock_yaml.return_value = {
            'scoring_weights': {
                'repo_spread_weight': 0.4,
                'bval_divergence_weight': 0.3,
                'volume_weight': 0.2,
                'volatility_weight': 0.1,
                'lookback_days': 30
            }
        }
        
        weights = load_scoring_config()
        
        assert weights.repo_spread_weight == Decimal('0.4')
        assert weights.bval_divergence_weight == Decimal('0.3')
        assert weights.volume_weight == Decimal('0.2')
        assert weights.volatility_weight == Decimal('0.1')
        assert weights.lookback_days == 30
    
    @patch('src.scoring.scoring.Path')
    def test_load_scoring_config_file_not_found(self, mock_path):
        """Test configuration loading when file doesn't exist."""
        # Mock file doesn't exist
        mock_path.return_value.exists.return_value = False
        
        weights = load_scoring_config()
        
        # Should return default weights
        assert isinstance(weights, ScoreWeights)
        assert weights.validate_total_weights()
    
    def test_load_scoring_config_custom_path(self):
        """Test configuration loading with custom path."""
        with pytest.raises(FileNotFoundError):
            load_scoring_config("/nonexistent/path/config.yaml")
