"""
Unit tests for Pydantic data models.

Tests validation logic, data transformation, and business rules
for Treasury, Repo, and Scoring data models.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from pydantic import ValidationError

from src.models.treasury import TreasuryData, TreasuryPrice
from src.models.repo import RepoData, RepoSpread
from src.models.scoring import ScoreData, ScoreWeights


class TestTreasuryModels:
    """Test cases for Treasury data models."""
    
    def test_treasury_price_valid_data(self):
        """Test TreasuryPrice with valid data."""
        price = TreasuryPrice(
            cusip="912828XG8",
            price_date=date.today(),
            bval_price=Decimal("99.5000"),
            internal_price=Decimal("99.4500"),
            day_over_day_change=Decimal("-0.0500")
        )
        
        assert price.cusip == "912828XG8"
        assert price.bval_price == Decimal("99.5000")
        assert price.internal_price == Decimal("99.4500")
        assert price.day_over_day_change == Decimal("-0.0500")
        assert isinstance(price.created_at, datetime)
    
    def test_treasury_price_cusip_validation(self):
        """Test CUSIP validation in TreasuryPrice."""
        # Valid CUSIP
        price = TreasuryPrice(
            cusip="912828XG8",
            price_date=date.today(),
            bval_price=Decimal("99.5000")
        )
        assert price.cusip == "912828XG8"
        
        # Invalid CUSIP length
        with pytest.raises(ValidationError) as exc_info:
            TreasuryPrice(
                cusip="12345",  # Too short
                price_date=date.today(),
                bval_price=Decimal("99.5000")
            )
        assert "CUSIP must be 9 characters" in str(exc_info.value)
        
        # CUSIP should be uppercase
        price = TreasuryPrice(
            cusip="912828xg8",  # lowercase
            price_date=date.today(),
            bval_price=Decimal("99.5000")
        )
        assert price.cusip == "912828XG8"  # Should be converted to uppercase
    
    def test_treasury_price_negative_prices(self):
        """Test validation of negative prices."""
        with pytest.raises(ValidationError) as exc_info:
            TreasuryPrice(
                cusip="912828XG8",
                price_date=date.today(),
                bval_price=Decimal("-1.0000")  # Negative price
            )
        assert "Prices must be positive" in str(exc_info.value)
    
    def test_treasury_data_valid_data(self):
        """Test TreasuryData with valid data."""
        treasury = TreasuryData(
            cusip="912828XG8",
            maturity_date=date(2034, 2, 15),
            coupon_rate=Decimal("0.0425"),
            issue_date=date(2024, 2, 15),
            security_type="Treasury Note"
        )
        
        assert treasury.cusip == "912828XG8"
        assert treasury.maturity_date == date(2034, 2, 15)
        assert treasury.coupon_rate == Decimal("0.0425")
        assert treasury.security_type == "Treasury Note"
    
    def test_treasury_data_coupon_validation(self):
        """Test coupon rate validation."""
        # Valid coupon rate
        treasury = TreasuryData(
            cusip="912828XG8",
            maturity_date=date(2034, 2, 15),
            coupon_rate=Decimal("0.0425")  # 4.25%
        )
        assert treasury.coupon_rate == Decimal("0.0425")
        
        # Invalid coupon rate (too high)
        with pytest.raises(ValidationError) as exc_info:
            TreasuryData(
                cusip="912828XG8",
                maturity_date=date(2034, 2, 15),
                coupon_rate=Decimal("1.5")  # 150%
            )
        assert "Coupon rate must be between 0 and 1" in str(exc_info.value)
        
        # Invalid coupon rate (negative)
        with pytest.raises(ValidationError) as exc_info:
            TreasuryData(
                cusip="912828XG8",
                maturity_date=date(2034, 2, 15),
                coupon_rate=Decimal("-0.01")  # Negative
            )
        assert "Coupon rate must be between 0 and 1" in str(exc_info.value)


class TestRepoModels:
    """Test cases for Repo data models."""
    
    def test_repo_spread_valid_data(self):
        """Test RepoSpread with valid data."""
        spread = RepoSpread(
            cusip="912828XG8",
            spread_date=date.today(),
            term_days=7,
            repo_rate=Decimal("0.0525"),
            treasury_rate=Decimal("0.0500"),
            spread_bps=Decimal("25.0"),
            volume=Decimal("1000000.00"),
            trade_count=15
        )
        
        assert spread.cusip == "912828XG8"
        assert spread.term_days == 7
        assert spread.repo_rate == Decimal("0.0525")
        assert spread.treasury_rate == Decimal("0.0500")
        assert spread.spread_bps == Decimal("25.0")
        assert spread.volume == Decimal("1000000.00")
        assert spread.trade_count == 15
    
    def test_repo_spread_term_validation(self):
        """Test term days validation."""
        # Valid term
        spread = RepoSpread(
            cusip="912828XG8",
            spread_date=date.today(),
            term_days=30,
            repo_rate=Decimal("0.0525"),
            treasury_rate=Decimal("0.0500"),
            spread_bps=Decimal("25.0")
        )
        assert spread.term_days == 30
        
        # Invalid term (zero)
        with pytest.raises(ValidationError) as exc_info:
            RepoSpread(
                cusip="912828XG8",
                spread_date=date.today(),
                term_days=0,
                repo_rate=Decimal("0.0525"),
                treasury_rate=Decimal("0.0500"),
                spread_bps=Decimal("25.0")
            )
        assert "Term days must be positive" in str(exc_info.value)
        
        # Invalid term (negative)
        with pytest.raises(ValidationError) as exc_info:
            RepoSpread(
                cusip="912828XG8",
                spread_date=date.today(),
                term_days=-1,
                repo_rate=Decimal("0.0525"),
                treasury_rate=Decimal("0.0500"),
                spread_bps=Decimal("25.0")
            )
        assert "Term days must be positive" in str(exc_info.value)
    
    def test_repo_spread_rate_validation(self):
        """Test rate validation."""
        # Rates too high
        with pytest.raises(ValidationError) as exc_info:
            RepoSpread(
                cusip="912828XG8",
                spread_date=date.today(),
                term_days=7,
                repo_rate=Decimal("0.75"),  # 75%
                treasury_rate=Decimal("0.0500"),
                spread_bps=Decimal("25.0")
            )
        assert "Rates must be between -1% and 50%" in str(exc_info.value)
    
    def test_repo_data_calculate_avg_spread(self):
        """Test average spread calculation."""
        repo = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            overnight_spread=Decimal("10.0"),
            one_week_spread=Decimal("15.0"),
            one_month_spread=Decimal("20.0"),
            three_month_spread=Decimal("25.0")
        )
        
        avg_spread = repo.calculate_avg_spread()
        expected_avg = (10.0 + 15.0 + 20.0 + 25.0) / 4
        assert float(avg_spread) == expected_avg
    
    def test_repo_data_partial_spreads(self):
        """Test average calculation with partial spread data."""
        repo = RepoData(
            cusip="912828XG8",
            data_date=date.today(),
            overnight_spread=Decimal("10.0"),
            one_week_spread=Decimal("15.0"),
            # Missing one_month_spread and three_month_spread
        )
        
        avg_spread = repo.calculate_avg_spread()
        expected_avg = (10.0 + 15.0) / 2
        assert float(avg_spread) == expected_avg
    
    def test_repo_data_no_spreads(self):
        """Test average calculation with no spread data."""
        repo = RepoData(
            cusip="912828XG8",
            data_date=date.today()
            # No spread data provided
        )
        
        avg_spread = repo.calculate_avg_spread()
        assert avg_spread is None


class TestScoringModels:
    """Test cases for Scoring data models."""
    
    def test_score_weights_valid_data(self):
        """Test ScoreWeights with valid data."""
        weights = ScoreWeights(
            repo_spread_weight=Decimal("0.4"),
            bval_divergence_weight=Decimal("0.3"),
            volume_weight=Decimal("0.2"),
            volatility_weight=Decimal("0.1")
        )
        
        assert weights.repo_spread_weight == Decimal("0.4")
        assert weights.bval_divergence_weight == Decimal("0.3")
        assert weights.volume_weight == Decimal("0.2")
        assert weights.volatility_weight == Decimal("0.1")
        assert weights.validate_total_weights()
    
    def test_score_weights_validation(self):
        """Test weight validation."""
        # Weight too high
        with pytest.raises(ValidationError) as exc_info:
            ScoreWeights(
                repo_spread_weight=Decimal("1.5"),  # > 1.0
                bval_divergence_weight=Decimal("0.3"),
                volume_weight=Decimal("0.2"),
                volatility_weight=Decimal("0.1")
            )
        assert "Weights must be between 0.0 and 1.0" in str(exc_info.value)
        
        # Negative weight
        with pytest.raises(ValidationError) as exc_info:
            ScoreWeights(
                repo_spread_weight=Decimal("-0.1"),  # Negative
                bval_divergence_weight=Decimal("0.3"),
                volume_weight=Decimal("0.2"),
                volatility_weight=Decimal("0.1")
            )
        assert "Weights must be between 0.0 and 1.0" in str(exc_info.value)
    
    def test_score_weights_normalization(self):
        """Test weight normalization."""
        weights = ScoreWeights(
            repo_spread_weight=Decimal("0.8"),  # Total = 1.6 (needs normalization)
            bval_divergence_weight=Decimal("0.4"),
            volume_weight=Decimal("0.3"),
            volatility_weight=Decimal("0.1")
        )
        
        # Original weights don't sum to 1.0
        assert not weights.validate_total_weights()
        
        # Normalize weights
        normalized = weights.normalize_weights()
        assert normalized.validate_total_weights()
        
        # Check proportions are preserved
        total = 0.8 + 0.4 + 0.3 + 0.1  # 1.6
        assert float(normalized.repo_spread_weight) == pytest.approx(0.8 / total)
        assert float(normalized.bval_divergence_weight) == pytest.approx(0.4 / total)
        assert float(normalized.volume_weight) == pytest.approx(0.3 / total)
        assert float(normalized.volatility_weight) == pytest.approx(0.1 / total)
    
    def test_score_data_valid_data(self):
        """Test ScoreData with valid data."""
        score = ScoreData(
            cusip="912828XG8",
            score_date=date.today(),
            repo_spread_score=Decimal("75.0"),
            bval_divergence_score=Decimal("65.0"),
            volume_score=Decimal("80.0"),
            volatility_score=Decimal("70.0"),
            composite_score=Decimal("72.5"),
            confidence_score=Decimal("85.0")
        )
        
        assert score.cusip == "912828XG8"
        assert score.repo_spread_score == Decimal("75.0")
        assert score.composite_score == Decimal("72.5")
        assert score.confidence_score == Decimal("85.0")
    
    def test_score_data_score_validation(self):
        """Test score range validation."""
        # Valid scores
        score = ScoreData(
            cusip="912828XG8",
            score_date=date.today(),
            composite_score=Decimal("75.0")
        )
        assert score.composite_score == Decimal("75.0")
        
        # Score too high
        with pytest.raises(ValidationError) as exc_info:
            ScoreData(
                cusip="912828XG8",
                score_date=date.today(),
                composite_score=Decimal("150.0")  # > 100
            )
        assert "Scores must be between 0 and 100" in str(exc_info.value)
        
        # Negative score
        with pytest.raises(ValidationError) as exc_info:
            ScoreData(
                cusip="912828XG8",
                score_date=date.today(),
                composite_score=Decimal("-10.0")  # < 0
            )
        assert "Scores must be between 0 and 100" in str(exc_info.value)
    
    def test_score_data_risk_category(self):
        """Test risk category classification."""
        # High Opportunity
        score = ScoreData(
            cusip="912828XG8",
            score_date=date.today(),
            composite_score=Decimal("85.0")
        )
        assert score.get_risk_category() == "High Opportunity"
        
        # Medium Opportunity
        score.composite_score = Decimal("65.0")
        assert score.get_risk_category() == "Medium Opportunity"
        
        # Low Opportunity
        score.composite_score = Decimal("45.0")
        assert score.get_risk_category() == "Low Opportunity"
        
        # Avoid
        score.composite_score = Decimal("25.0")
        assert score.get_risk_category() == "Avoid"
        
        # Unknown (no score)
        score.composite_score = None
        assert score.get_risk_category() == "Unknown"
    
    def test_score_data_confidence_category(self):
        """Test confidence category classification."""
        score = ScoreData(
            cusip="912828XG8",
            score_date=date.today(),
            confidence_score=Decimal("80.0")
        )
        assert score.get_confidence_category() == "High"
        
        score.confidence_score = Decimal("60.0")
        assert score.get_confidence_category() == "Medium"
        
        score.confidence_score = Decimal("40.0")
        assert score.get_confidence_category() == "Low"
        
        score.confidence_score = None
        assert score.get_confidence_category() == "Unknown"


class TestModelSerialization:
    """Test JSON serialization of models."""
    
    def test_treasury_price_serialization(self):
        """Test TreasuryPrice JSON serialization."""
        price = TreasuryPrice(
            cusip="912828XG8",
            price_date=date.today(),
            bval_price=Decimal("99.5000"),
            internal_price=Decimal("99.4500")
        )
        
        # Should serialize without errors
        json_data = price.dict()
        assert json_data['cusip'] == "912828XG8"
        assert json_data['bval_price'] == Decimal("99.5000")
        
        # Should be JSON encodable with custom encoder
        import json
        json_str = json.dumps(json_data, default=str)
        assert "912828XG8" in json_str
    
    def test_score_data_serialization(self):
        """Test ScoreData JSON serialization with metadata."""
        score = ScoreData(
            cusip="912828XG8",
            score_date=date.today(),
            composite_score=Decimal("75.0"),
            weights_used={
                'repo_spread_weight': 0.4,
                'bval_divergence_weight': 0.3,
                'volume_weight': 0.2,
                'volatility_weight': 0.1
            }
        )
        
        json_data = score.dict()
        assert json_data['cusip'] == "912828XG8"
        assert json_data['composite_score'] == Decimal("75.0")
        assert json_data['weights_used']['repo_spread_weight'] == 0.4
