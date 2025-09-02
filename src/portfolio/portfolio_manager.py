"""
Portfolio Management and P&L Attribution System
Comprehensive position tracking, performance analytics, and risk attribution
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from decimal import Decimal, ROUND_HALF_UP
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PositionType(Enum):
    """Position types"""
    LONG = "long"
    SHORT = "short"

class TradeType(Enum):
    """Trade types"""
    BUY = "buy"
    SELL = "sell"

class AssetClass(Enum):
    """Asset classes"""
    TREASURY = "treasury"
    CORPORATE = "corporate"
    AGENCY = "agency"
    REPO = "repo"

@dataclass
class Trade:
    """Individual trade record"""
    trade_id: str
    cusip: str
    trade_type: TradeType
    quantity: float  # Face value in millions
    price: float
    trade_date: datetime
    settlement_date: datetime
    trader: str
    counterparty: str
    commission: float = 0.0
    accrued_interest: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Position:
    """Portfolio position"""
    cusip: str
    security_name: str
    asset_class: AssetClass
    quantity: float  # Face value in millions
    average_price: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    realized_pnl: float
    duration: float
    convexity: float
    yield_rate: float
    maturity_date: datetime
    coupon_rate: float
    last_updated: datetime
    position_type: PositionType = PositionType.LONG

@dataclass
class PortfolioSummary:
    """Portfolio summary metrics"""
    total_market_value: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    total_pnl: float
    portfolio_duration: float
    portfolio_convexity: float
    portfolio_yield: float
    var_95: float
    var_99: float
    beta_to_benchmark: float
    tracking_error: float
    sharpe_ratio: float
    max_drawdown: float
    positions_count: int
    last_updated: datetime

class PositionManager:
    """Manages individual positions and trade processing"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        
    def add_trade(self, trade: Trade) -> None:
        """Add a new trade and update positions"""
        try:
            self.trades.append(trade)
            self._update_position_from_trade(trade)
            logger.info(f"Trade added: {trade.trade_id} - {trade.trade_type.value} {trade.quantity}MM {trade.cusip}")
            
        except Exception as e:
            logger.error(f"Error adding trade: {e}")
    
    def _update_position_from_trade(self, trade: Trade) -> None:
        """Update position based on new trade"""
        cusip = trade.cusip
        
        if cusip not in self.positions:
            # Create new position
            self.positions[cusip] = Position(
                cusip=cusip,
                security_name=trade.metadata.get('security_name', f'Security {cusip}'),
                asset_class=AssetClass(trade.metadata.get('asset_class', 'treasury')),
                quantity=0.0,
                average_price=0.0,
                current_price=trade.price,
                market_value=0.0,
                cost_basis=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                duration=trade.metadata.get('duration', 5.0),
                convexity=trade.metadata.get('convexity', 25.0),
                yield_rate=trade.metadata.get('yield', 0.04),
                maturity_date=trade.metadata.get('maturity_date', datetime.now() + timedelta(days=3650)),
                coupon_rate=trade.metadata.get('coupon_rate', 0.04),
                last_updated=datetime.now()
            )
        
        position = self.positions[cusip]
        
        # Calculate trade impact
        trade_quantity = trade.quantity if trade.trade_type == TradeType.BUY else -trade.quantity
        trade_cost = trade.quantity * trade.price + trade.commission + trade.accrued_interest
        
        if trade.trade_type == TradeType.SELL:
            # Calculate realized P&L for sells
            if position.quantity > 0:  # Have existing long position
                sell_cost_basis = (trade.quantity / position.quantity) * position.cost_basis
                realized_pnl = trade_cost - sell_cost_basis
                position.realized_pnl += realized_pnl
                logger.info(f"Realized P&L: ${realized_pnl:,.2f} on {trade.cusip}")
        
        # Update position quantities and cost basis
        if position.quantity + trade_quantity == 0:
            # Position closed out
            position.quantity = 0
            position.average_price = 0
            position.cost_basis = 0
        elif (position.quantity > 0 and trade_quantity > 0) or (position.quantity < 0 and trade_quantity < 0):
            # Adding to existing position
            total_cost = position.cost_basis + trade_cost
            total_quantity = position.quantity + trade_quantity
            position.average_price = total_cost / abs(total_quantity) if total_quantity != 0 else 0
            position.quantity = total_quantity
            position.cost_basis = total_cost
        else:
            # Reducing position or changing direction
            position.quantity += trade_quantity
            if position.quantity != 0:
                position.cost_basis = position.quantity * position.average_price
            else:
                position.cost_basis = 0
                position.average_price = 0
        
        # Update position type
        position.position_type = PositionType.LONG if position.quantity >= 0 else PositionType.SHORT
        position.last_updated = datetime.now()
        
        # Update market values
        self._update_position_market_values(cusip)
    
    def _update_position_market_values(self, cusip: str) -> None:
        """Update market values for a position"""
        if cusip not in self.positions:
            return
            
        position = self.positions[cusip]
        
        # Calculate market value
        position.market_value = abs(position.quantity) * position.current_price
        
        # Calculate unrealized P&L
        if position.quantity != 0:
            position.unrealized_pnl = position.market_value - position.cost_basis
        else:
            position.unrealized_pnl = 0
    
    def update_market_prices(self, price_updates: Dict[str, float]) -> None:
        """Update current market prices for positions"""
        for cusip, price in price_updates.items():
            if cusip in self.positions:
                self.positions[cusip].current_price = price
                self.positions[cusip].last_updated = datetime.now()
                self._update_position_market_values(cusip)
    
    def get_position(self, cusip: str) -> Optional[Position]:
        """Get position for a specific CUSIP"""
        return self.positions.get(cusip)
    
    def get_all_positions(self, include_zero: bool = False) -> List[Position]:
        """Get all positions"""
        positions = list(self.positions.values())
        
        if not include_zero:
            positions = [p for p in positions if p.quantity != 0]
            
        return sorted(positions, key=lambda x: abs(x.market_value), reverse=True)

class PnLAttributor:
    """P&L Attribution Analysis"""
    
    def __init__(self):
        self.attribution_factors = [
            'carry_pnl',      # Carry/theta P&L
            'price_pnl',      # Clean price movement
            'curve_pnl',      # Yield curve movement
            'spread_pnl',     # Credit/option spread movement
            'fx_pnl',         # FX impact (if applicable)
            'other_pnl'       # Residual/unexplained
        ]
    
    def calculate_daily_attribution(self, positions: List[Position], 
                                  previous_positions: List[Position],
                                  market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate daily P&L attribution"""
        try:
            attribution = {factor: 0.0 for factor in self.attribution_factors}
            
            # Create position lookup
            prev_positions_dict = {p.cusip: p for p in previous_positions}
            
            for position in positions:
                cusip = position.cusip
                prev_position = prev_positions_dict.get(cusip)
                
                if prev_position:
                    # Calculate attribution for existing position
                    pos_attribution = self._calculate_position_attribution(
                        position, prev_position, market_data.get(cusip, {})
                    )
                    
                    # Aggregate attribution
                    for factor in self.attribution_factors:
                        attribution[factor] += pos_attribution.get(factor, 0.0)
            
            return attribution
            
        except Exception as e:
            logger.error(f"Error calculating P&L attribution: {e}")
            return {factor: 0.0 for factor in self.attribution_factors}
    
    def _calculate_position_attribution(self, current_pos: Position, 
                                      previous_pos: Position,
                                      market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate P&L attribution for a single position"""
        attribution = {}
        
        # Total P&L change
        total_pnl_change = current_pos.unrealized_pnl - previous_pos.unrealized_pnl
        
        # Carry P&L (time decay, accrued interest)
        days_passed = (current_pos.last_updated - previous_pos.last_updated).days
        carry_pnl = (current_pos.coupon_rate / 365) * days_passed * abs(current_pos.quantity) * 1000000
        attribution['carry_pnl'] = carry_pnl
        
        # Price P&L (clean price movement)
        price_change = current_pos.current_price - previous_pos.current_price
        price_pnl = price_change * abs(current_pos.quantity) * 1000000
        attribution['price_pnl'] = price_pnl
        
        # Curve P&L (duration-adjusted yield movement)
        yield_change = market_data.get('yield_change', 0.0)
        curve_pnl = -current_pos.duration * yield_change * current_pos.market_value * 1000000
        attribution['curve_pnl'] = curve_pnl
        
        # Spread P&L (credit spread movement)
        spread_change = market_data.get('spread_change', 0.0)
        spread_pnl = -spread_change * current_pos.market_value * 1000000
        attribution['spread_pnl'] = spread_pnl
        
        # FX P&L (assume USD for now)
        attribution['fx_pnl'] = 0.0
        
        # Other/Residual P&L
        explained_pnl = sum(attribution.values())
        attribution['other_pnl'] = total_pnl_change - explained_pnl
        
        return attribution

class RiskMetrics:
    """Portfolio risk metrics calculation"""
    
    @staticmethod
    def calculate_portfolio_duration(positions: List[Position]) -> float:
        """Calculate portfolio duration"""
        try:
            total_market_value = sum(abs(p.market_value) for p in positions)
            
            if total_market_value == 0:
                return 0.0
                
            weighted_duration = sum(
                p.duration * abs(p.market_value) for p in positions
            )
            
            return weighted_duration / total_market_value
            
        except Exception as e:
            logger.error(f"Error calculating portfolio duration: {e}")
            return 0.0
    
    @staticmethod
    def calculate_portfolio_convexity(positions: List[Position]) -> float:
        """Calculate portfolio convexity"""
        try:
            total_market_value = sum(abs(p.market_value) for p in positions)
            
            if total_market_value == 0:
                return 0.0
                
            weighted_convexity = sum(
                p.convexity * abs(p.market_value) for p in positions
            )
            
            return weighted_convexity / total_market_value
            
        except Exception as e:
            logger.error(f"Error calculating portfolio convexity: {e}")
            return 0.0
    
    @staticmethod
    def calculate_portfolio_yield(positions: List[Position]) -> float:
        """Calculate portfolio yield"""
        try:
            total_market_value = sum(abs(p.market_value) for p in positions)
            
            if total_market_value == 0:
                return 0.0
                
            weighted_yield = sum(
                p.yield_rate * abs(p.market_value) for p in positions
            )
            
            return weighted_yield / total_market_value
            
        except Exception as e:
            logger.error(f"Error calculating portfolio yield: {e}")
            return 0.0
    
    @staticmethod
    def calculate_var(pnl_history: List[float], confidence_level: float = 0.95) -> float:
        """Calculate Value at Risk"""
        if len(pnl_history) < 30:
            return 0.0
            
        sorted_pnl = sorted(pnl_history)
        var_index = int((1 - confidence_level) * len(sorted_pnl))
        
        return abs(sorted_pnl[var_index]) if var_index < len(sorted_pnl) else 0.0

class PortfolioManager:
    """Main portfolio management system"""
    
    def __init__(self):
        self.position_manager = PositionManager()
        self.pnl_attributor = PnLAttributor()
        self.pnl_history: List[float] = []
        self.daily_attribution_history: List[Dict[str, float]] = []
        
    def add_trade(self, trade: Trade) -> None:
        """Add a trade to the portfolio"""
        self.position_manager.add_trade(trade)
    
    def update_market_data(self, market_data: Dict[str, Any]) -> None:
        """Update market data and recalculate positions"""
        # Extract price updates
        price_updates = {}
        for cusip, data in market_data.items():
            if isinstance(data, dict) and 'price' in data:
                price_updates[cusip] = data['price']
            elif isinstance(data, (int, float)):
                price_updates[cusip] = data
        
        if price_updates:
            self.position_manager.update_market_prices(price_updates)
    
    def get_portfolio_summary(self) -> PortfolioSummary:
        """Get comprehensive portfolio summary"""
        try:
            positions = self.position_manager.get_all_positions()
            
            # Calculate totals
            total_market_value = sum(p.market_value for p in positions)
            total_cost_basis = sum(p.cost_basis for p in positions)
            total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
            total_realized_pnl = sum(p.realized_pnl for p in positions)
            total_pnl = total_unrealized_pnl + total_realized_pnl
            
            # Calculate risk metrics
            portfolio_duration = RiskMetrics.calculate_portfolio_duration(positions)
            portfolio_convexity = RiskMetrics.calculate_portfolio_convexity(positions)
            portfolio_yield = RiskMetrics.calculate_portfolio_yield(positions)
            
            # Calculate VaR
            var_95 = RiskMetrics.calculate_var(self.pnl_history, 0.95)
            var_99 = RiskMetrics.calculate_var(self.pnl_history, 0.99)
            
            # Calculate performance metrics (simplified)
            beta_to_benchmark = self._calculate_beta()
            tracking_error = self._calculate_tracking_error()
            sharpe_ratio = self._calculate_sharpe_ratio()
            max_drawdown = self._calculate_max_drawdown()
            
            return PortfolioSummary(
                total_market_value=total_market_value,
                total_cost_basis=total_cost_basis,
                total_unrealized_pnl=total_unrealized_pnl,
                total_realized_pnl=total_realized_pnl,
                total_pnl=total_pnl,
                portfolio_duration=portfolio_duration,
                portfolio_convexity=portfolio_convexity,
                portfolio_yield=portfolio_yield,
                var_95=var_95,
                var_99=var_99,
                beta_to_benchmark=beta_to_benchmark,
                tracking_error=tracking_error,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                positions_count=len(positions),
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error calculating portfolio summary: {e}")
            return None
    
    def calculate_daily_pnl_attribution(self, previous_positions: List[Position],
                                      market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate daily P&L attribution"""
        current_positions = self.position_manager.get_all_positions(include_zero=True)
        attribution = self.pnl_attributor.calculate_daily_attribution(
            current_positions, previous_positions, market_data
        )
        
        # Store attribution history
        attribution['date'] = datetime.now().isoformat()
        self.daily_attribution_history.append(attribution)
        
        # Keep only last 252 days (1 year)
        if len(self.daily_attribution_history) > 252:
            self.daily_attribution_history = self.daily_attribution_history[-252:]
        
        return attribution
    
    def get_position_breakdown(self) -> Dict[str, Any]:
        """Get detailed position breakdown"""
        positions = self.position_manager.get_all_positions()
        
        # Breakdown by asset class
        asset_class_breakdown = {}
        for asset_class in AssetClass:
            class_positions = [p for p in positions if p.asset_class == asset_class]
            if class_positions:
                asset_class_breakdown[asset_class.value] = {
                    'count': len(class_positions),
                    'market_value': sum(p.market_value for p in class_positions),
                    'unrealized_pnl': sum(p.unrealized_pnl for p in class_positions),
                    'avg_duration': sum(p.duration * abs(p.market_value) for p in class_positions) / 
                                  sum(abs(p.market_value) for p in class_positions) if class_positions else 0
                }
        
        # Top positions by market value
        top_positions = sorted(positions, key=lambda x: abs(x.market_value), reverse=True)[:10]
        
        # Maturity breakdown
        maturity_buckets = {
            '0-1Y': [],
            '1-3Y': [],
            '3-5Y': [],
            '5-10Y': [],
            '10Y+': []
        }
        
        for position in positions:
            years_to_maturity = (position.maturity_date - datetime.now()).days / 365.25
            
            if years_to_maturity <= 1:
                maturity_buckets['0-1Y'].append(position)
            elif years_to_maturity <= 3:
                maturity_buckets['1-3Y'].append(position)
            elif years_to_maturity <= 5:
                maturity_buckets['3-5Y'].append(position)
            elif years_to_maturity <= 10:
                maturity_buckets['5-10Y'].append(position)
            else:
                maturity_buckets['10Y+'].append(position)
        
        maturity_breakdown = {}
        for bucket, bucket_positions in maturity_buckets.items():
            if bucket_positions:
                maturity_breakdown[bucket] = {
                    'count': len(bucket_positions),
                    'market_value': sum(p.market_value for p in bucket_positions),
                    'percentage': sum(abs(p.market_value) for p in bucket_positions) / 
                                sum(abs(p.market_value) for p in positions) * 100 if positions else 0
                }
        
        return {
            'asset_class_breakdown': asset_class_breakdown,
            'top_positions': [
                {
                    'cusip': p.cusip,
                    'security_name': p.security_name,
                    'market_value': p.market_value,
                    'unrealized_pnl': p.unrealized_pnl,
                    'percentage': abs(p.market_value) / sum(abs(pos.market_value) for pos in positions) * 100
                }
                for p in top_positions
            ],
            'maturity_breakdown': maturity_breakdown
        }
    
    def _calculate_beta(self) -> float:
        """Calculate portfolio beta to benchmark (simplified)"""
        # In production, this would calculate against a real benchmark
        return 0.85  # Mock value
    
    def _calculate_tracking_error(self) -> float:
        """Calculate tracking error (simplified)"""
        # In production, this would use benchmark returns
        return 0.02  # Mock value (2%)
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio (simplified)"""
        if len(self.pnl_history) < 30:
            return 0.0
            
        returns = np.array(self.pnl_history)
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Assume 2% risk-free rate
        risk_free_rate = 0.02 / 252  # Daily
        
        if std_return == 0:
            return 0.0
            
        return (avg_return - risk_free_rate) / std_return * np.sqrt(252)
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        if len(self.pnl_history) < 2:
            return 0.0
            
        cumulative_returns = np.cumsum(self.pnl_history)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = cumulative_returns - running_max
        
        return abs(np.min(drawdown))
    
    def export_positions_to_dict(self) -> List[Dict[str, Any]]:
        """Export positions to dictionary format"""
        positions = self.position_manager.get_all_positions()
        
        return [
            {
                'cusip': p.cusip,
                'security_name': p.security_name,
                'asset_class': p.asset_class.value,
                'quantity': p.quantity,
                'average_price': p.average_price,
                'current_price': p.current_price,
                'market_value': p.market_value,
                'cost_basis': p.cost_basis,
                'unrealized_pnl': p.unrealized_pnl,
                'realized_pnl': p.realized_pnl,
                'duration': p.duration,
                'convexity': p.convexity,
                'yield_rate': p.yield_rate,
                'maturity_date': p.maturity_date.isoformat(),
                'coupon_rate': p.coupon_rate,
                'position_type': p.position_type.value,
                'last_updated': p.last_updated.isoformat()
            }
            for p in positions
        ]

# Example usage and testing
if __name__ == "__main__":
    # Create portfolio manager
    portfolio = PortfolioManager()
    
    # Add sample trades
    trades = [
        Trade(
            trade_id="T001",
            cusip="912828XG8",
            trade_type=TradeType.BUY,
            quantity=10.0,  # $10MM
            price=99.5,
            trade_date=datetime.now() - timedelta(days=5),
            settlement_date=datetime.now() - timedelta(days=3),
            trader="John Doe",
            counterparty="Goldman Sachs",
            metadata={
                'security_name': '10Y Treasury Note',
                'asset_class': 'treasury',
                'duration': 8.5,
                'convexity': 75.0,
                'yield': 0.045,
                'coupon_rate': 0.04
            }
        ),
        Trade(
            trade_id="T002",
            cusip="912828YK0",
            trade_type=TradeType.BUY,
            quantity=5.0,  # $5MM
            price=101.2,
            trade_date=datetime.now() - timedelta(days=3),
            settlement_date=datetime.now() - timedelta(days=1),
            trader="Jane Smith",
            counterparty="JP Morgan",
            metadata={
                'security_name': '2Y Treasury Note',
                'asset_class': 'treasury',
                'duration': 1.9,
                'convexity': 3.5,
                'yield': 0.048,
                'coupon_rate': 0.045
            }
        )
    ]
    
    # Add trades to portfolio
    for trade in trades:
        portfolio.add_trade(trade)
    
    # Update market prices
    portfolio.update_market_data({
        '912828XG8': 100.1,  # Price up
        '912828YK0': 100.8   # Price down
    })
    
    # Get portfolio summary
    summary = portfolio.get_portfolio_summary()
    if summary:
        print("Portfolio Summary:")
        print(f"Total Market Value: ${summary.total_market_value:,.2f}")
        print(f"Total P&L: ${summary.total_pnl:,.2f}")
        print(f"Portfolio Duration: {summary.portfolio_duration:.2f}")
        print(f"Portfolio Yield: {summary.portfolio_yield:.2%}")
        print(f"Number of Positions: {summary.positions_count}")
    
    # Get position breakdown
    breakdown = portfolio.get_position_breakdown()
    print(f"\nAsset Class Breakdown: {json.dumps(breakdown['asset_class_breakdown'], indent=2)}")
    
    print("\nTop Positions:")
    for pos in breakdown['top_positions'][:3]:
        print(f"  {pos['security_name']}: ${pos['market_value']:,.2f} ({pos['percentage']:.1f}%)")
