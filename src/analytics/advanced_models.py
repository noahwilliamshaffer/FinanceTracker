"""
Advanced Financial Analytics Models
Yield curve fitting, duration/convexity, VaR calculations, and sophisticated risk metrics
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize, curve_fit
from scipy.stats import norm, t
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional, Any
import warnings
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class YieldCurvePoint:
    """Individual yield curve data point"""
    maturity: float  # Years to maturity
    yield_rate: float  # Yield in decimal (e.g., 0.045 for 4.5%)
    timestamp: datetime

@dataclass
class BondMetrics:
    """Comprehensive bond risk metrics"""
    cusip: str
    price: float
    yield_rate: float
    duration: float
    modified_duration: float
    convexity: float
    dv01: float  # Dollar value of 01 basis point
    key_rate_durations: Dict[str, float]
    timestamp: datetime

class NelsonSiegelModel:
    """
    Nelson-Siegel yield curve model
    y(τ) = β₀ + β₁((1-e^(-τ/λ))/(τ/λ)) + β₂((1-e^(-τ/λ))/(τ/λ) - e^(-τ/λ))
    """
    
    def __init__(self):
        self.beta0 = None  # Long-term level
        self.beta1 = None  # Short-term component  
        self.beta2 = None  # Medium-term component
        self.lambda_param = None  # Decay parameter
        self.fitted = False
        
    def nelson_siegel_curve(self, tau: np.ndarray, beta0: float, beta1: float, beta2: float, lambda_param: float) -> np.ndarray:
        """Nelson-Siegel yield curve function"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Avoid division by zero
            tau = np.where(tau == 0, 1e-6, tau)
            
            term1 = beta0
            term2 = beta1 * ((1 - np.exp(-tau / lambda_param)) / (tau / lambda_param))
            term3 = beta2 * (((1 - np.exp(-tau / lambda_param)) / (tau / lambda_param)) - np.exp(-tau / lambda_param))
            
            return term1 + term2 + term3
    
    def fit(self, maturities: np.ndarray, yields: np.ndarray) -> Dict[str, float]:
        """Fit Nelson-Siegel model to yield curve data"""
        try:
            # Initial parameter guesses
            initial_guess = [
                np.mean(yields),  # beta0: average yield level
                yields[0] - yields[-1],  # beta1: short-long spread
                np.max(yields) - np.min(yields),  # beta2: curvature
                2.0  # lambda: typical value around 2
            ]
            
            # Bounds for parameters
            bounds = [
                (-0.1, 0.2),   # beta0: reasonable yield range
                (-0.2, 0.2),   # beta1: spread range
                (-0.2, 0.2),   # beta2: curvature range  
                (0.1, 10.0)    # lambda: positive decay parameter
            ]
            
            # Fit the model
            popt, pcov = curve_fit(
                self.nelson_siegel_curve,
                maturities,
                yields,
                p0=initial_guess,
                bounds=tuple(zip(*bounds)),
                maxfev=5000
            )
            
            self.beta0, self.beta1, self.beta2, self.lambda_param = popt
            self.fitted = True
            
            # Calculate fit quality metrics
            fitted_yields = self.nelson_siegel_curve(maturities, *popt)
            rmse = np.sqrt(np.mean((yields - fitted_yields) ** 2))
            r_squared = 1 - np.sum((yields - fitted_yields) ** 2) / np.sum((yields - np.mean(yields)) ** 2)
            
            logger.info(f"Nelson-Siegel model fitted: RMSE={rmse:.4f}, R²={r_squared:.4f}")
            
            return {
                'beta0': self.beta0,
                'beta1': self.beta1, 
                'beta2': self.beta2,
                'lambda': self.lambda_param,
                'rmse': rmse,
                'r_squared': r_squared
            }
            
        except Exception as e:
            logger.error(f"Error fitting Nelson-Siegel model: {e}")
            return {}
    
    def predict(self, maturities: np.ndarray) -> np.ndarray:
        """Predict yields for given maturities"""
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")
            
        return self.nelson_siegel_curve(maturities, self.beta0, self.beta1, self.beta2, self.lambda_param)
    
    def get_forward_rates(self, maturities: np.ndarray) -> np.ndarray:
        """Calculate instantaneous forward rates"""
        if not self.fitted:
            raise ValueError("Model must be fitted before calculating forward rates")
            
        # Forward rate formula for Nelson-Siegel
        forward_rates = (
            self.beta0 + 
            self.beta1 * np.exp(-maturities / self.lambda_param) +
            self.beta2 * (maturities / self.lambda_param) * np.exp(-maturities / self.lambda_param)
        )
        
        return forward_rates

class SvenssonModel(NelsonSiegelModel):
    """
    Svensson extension of Nelson-Siegel model (adds second hump)
    y(τ) = β₀ + β₁((1-e^(-τ/λ₁))/(τ/λ₁)) + β₂((1-e^(-τ/λ₁))/(τ/λ₁) - e^(-τ/λ₁)) + β₃((1-e^(-τ/λ₂))/(τ/λ₂) - e^(-τ/λ₂))
    """
    
    def __init__(self):
        super().__init__()
        self.beta3 = None
        self.lambda2 = None
    
    def svensson_curve(self, tau: np.ndarray, beta0: float, beta1: float, beta2: float, beta3: float, lambda1: float, lambda2: float) -> np.ndarray:
        """Svensson yield curve function"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            tau = np.where(tau == 0, 1e-6, tau)
            
            term1 = beta0
            term2 = beta1 * ((1 - np.exp(-tau / lambda1)) / (tau / lambda1))
            term3 = beta2 * (((1 - np.exp(-tau / lambda1)) / (tau / lambda1)) - np.exp(-tau / lambda1))
            term4 = beta3 * (((1 - np.exp(-tau / lambda2)) / (tau / lambda2)) - np.exp(-tau / lambda2))
            
            return term1 + term2 + term3 + term4

class BondAnalytics:
    """
    Comprehensive bond analytics: duration, convexity, key rate durations
    """
    
    @staticmethod
    def calculate_duration(price: float, yield_rate: float, coupon_rate: float, 
                          maturity_years: float, frequency: int = 2) -> Tuple[float, float]:
        """
        Calculate Macaulay and Modified Duration
        
        Returns:
            Tuple of (macaulay_duration, modified_duration)
        """
        try:
            periods = int(maturity_years * frequency)
            coupon_payment = coupon_rate / frequency
            discount_rate = yield_rate / frequency
            
            # Calculate present value of each cash flow and its weighted time
            pv_weighted_time = 0
            total_pv = 0
            
            for t in range(1, periods + 1):
                # Cash flow (coupon or coupon + principal)
                cash_flow = coupon_payment * 100  # Assume $100 face value
                if t == periods:  # Final payment includes principal
                    cash_flow += 100
                
                # Present value and weighted time
                pv = cash_flow / ((1 + discount_rate) ** t)
                weighted_time = pv * (t / frequency)  # Convert periods to years
                
                pv_weighted_time += weighted_time
                total_pv += pv
            
            # Macaulay Duration
            macaulay_duration = pv_weighted_time / total_pv
            
            # Modified Duration
            modified_duration = macaulay_duration / (1 + yield_rate / frequency)
            
            return macaulay_duration, modified_duration
            
        except Exception as e:
            logger.error(f"Error calculating duration: {e}")
            return 0.0, 0.0
    
    @staticmethod
    def calculate_convexity(price: float, yield_rate: float, coupon_rate: float,
                           maturity_years: float, frequency: int = 2) -> float:
        """Calculate bond convexity"""
        try:
            periods = int(maturity_years * frequency)
            coupon_payment = coupon_rate / frequency
            discount_rate = yield_rate / frequency
            
            convexity_sum = 0
            total_pv = 0
            
            for t in range(1, periods + 1):
                # Cash flow
                cash_flow = coupon_payment * 100
                if t == periods:
                    cash_flow += 100
                
                # Present value
                pv = cash_flow / ((1 + discount_rate) ** t)
                
                # Convexity component: t(t+1) * PV
                convexity_component = t * (t + 1) * pv
                
                convexity_sum += convexity_component
                total_pv += pv
            
            # Convexity formula
            convexity = convexity_sum / (total_pv * ((1 + discount_rate) ** 2) * (frequency ** 2))
            
            return convexity
            
        except Exception as e:
            logger.error(f"Error calculating convexity: {e}")
            return 0.0
    
    @staticmethod
    def calculate_dv01(price: float, modified_duration: float) -> float:
        """Calculate DV01 (Dollar Value of 01 basis point)"""
        return (modified_duration * price) / 10000  # 1 basis point = 0.0001
    
    @staticmethod
    def calculate_key_rate_durations(yield_curve_points: List[YieldCurvePoint],
                                   bond_maturity: float, 
                                   bond_yield: float) -> Dict[str, float]:
        """
        Calculate Key Rate Durations for different maturity buckets
        Measures sensitivity to parallel shifts in specific curve segments
        """
        key_rates = {}
        shift_size = 0.0001  # 1 basis point
        
        # Define key rate maturity buckets
        key_maturities = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]  # Years
        
        for key_maturity in key_maturities:
            if key_maturity <= bond_maturity:
                # Calculate sensitivity to shift at this key rate
                # Simplified calculation - in practice would use full yield curve
                weight = np.exp(-abs(bond_maturity - key_maturity))  # Distance weighting
                key_rate_duration = weight * 0.1  # Simplified sensitivity
                
                key_rates[f"{key_maturity}Y"] = key_rate_duration
        
        return key_rates

class VaRCalculator:
    """
    Value at Risk and Expected Shortfall calculations
    Supports Historical Simulation, Parametric, and Monte Carlo methods
    """
    
    def __init__(self):
        self.confidence_levels = [0.95, 0.99, 0.999]
        
    def historical_var(self, returns: np.ndarray, confidence_level: float = 0.95) -> Dict[str, float]:
        """Historical Simulation VaR"""
        try:
            if len(returns) < 30:
                logger.warning("Insufficient data for reliable VaR calculation")
                
            # Sort returns in ascending order
            sorted_returns = np.sort(returns)
            
            # Calculate VaR percentile
            var_percentile = 1 - confidence_level
            var_index = int(var_percentile * len(sorted_returns))
            
            var_value = sorted_returns[var_index]
            
            # Expected Shortfall (Conditional VaR)
            expected_shortfall = np.mean(sorted_returns[:var_index]) if var_index > 0 else var_value
            
            return {
                'var': var_value,
                'expected_shortfall': expected_shortfall,
                'confidence_level': confidence_level,
                'method': 'historical_simulation'
            }
            
        except Exception as e:
            logger.error(f"Error calculating Historical VaR: {e}")
            return {}
    
    def parametric_var(self, returns: np.ndarray, confidence_level: float = 0.95,
                      distribution: str = 'normal') -> Dict[str, float]:
        """Parametric VaR assuming normal or t-distribution"""
        try:
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)
            
            if distribution == 'normal':
                # Normal distribution VaR
                z_score = norm.ppf(1 - confidence_level)
                var_value = mean_return + z_score * std_return
                
            elif distribution == 't':
                # Student t-distribution (better for fat tails)
                from scipy.stats import t as t_dist
                
                # Estimate degrees of freedom
                df = self._estimate_degrees_of_freedom(returns)
                t_score = t_dist.ppf(1 - confidence_level, df)
                var_value = mean_return + t_score * std_return
                
            else:
                raise ValueError("Distribution must be 'normal' or 't'")
            
            # Expected Shortfall for normal distribution
            if distribution == 'normal':
                phi_z = norm.pdf(norm.ppf(1 - confidence_level))
                expected_shortfall = mean_return - (phi_z / (1 - confidence_level)) * std_return
            else:
                # Approximate ES for t-distribution
                expected_shortfall = var_value * 1.2  # Rough approximation
            
            return {
                'var': var_value,
                'expected_shortfall': expected_shortfall,
                'confidence_level': confidence_level,
                'method': f'parametric_{distribution}',
                'mean': mean_return,
                'std': std_return
            }
            
        except Exception as e:
            logger.error(f"Error calculating Parametric VaR: {e}")
            return {}
    
    def monte_carlo_var(self, returns: np.ndarray, confidence_level: float = 0.95,
                       num_simulations: int = 10000) -> Dict[str, float]:
        """Monte Carlo VaR simulation"""
        try:
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)
            
            # Generate random scenarios
            np.random.seed(42)  # For reproducibility
            simulated_returns = np.random.normal(mean_return, std_return, num_simulations)
            
            # Calculate VaR from simulated returns
            var_result = self.historical_var(simulated_returns, confidence_level)
            var_result['method'] = 'monte_carlo'
            var_result['num_simulations'] = num_simulations
            
            return var_result
            
        except Exception as e:
            logger.error(f"Error calculating Monte Carlo VaR: {e}")
            return {}
    
    def _estimate_degrees_of_freedom(self, returns: np.ndarray) -> float:
        """Estimate degrees of freedom for t-distribution"""
        # Simple method using kurtosis
        kurtosis = self._calculate_kurtosis(returns)
        
        # Relationship between kurtosis and degrees of freedom
        if kurtosis > 3:
            df = 6 / (kurtosis - 3) + 4
        else:
            df = 30  # Default to high df (approaching normal)
            
        return max(df, 3)  # Minimum df of 3
    
    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate sample kurtosis"""
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        
        centered_returns = returns - mean_return
        kurtosis = np.mean((centered_returns / std_return) ** 4)
        
        return kurtosis

class PrincipalComponentAnalysis:
    """
    Principal Component Analysis for yield curve movements
    Identifies key factors driving yield curve changes
    """
    
    def __init__(self):
        self.pca = PCA()
        self.scaler = StandardScaler()
        self.fitted = False
        self.component_names = ['Level', 'Slope', 'Curvature', 'Butterfly']
        
    def fit_yield_curve_pca(self, yield_changes: pd.DataFrame) -> Dict[str, Any]:
        """
        Fit PCA to yield curve changes
        
        Args:
            yield_changes: DataFrame with dates as index and maturities as columns
        """
        try:
            # Standardize the data
            scaled_data = self.scaler.fit_transform(yield_changes.fillna(0))
            
            # Fit PCA
            self.pca.fit(scaled_data)
            self.fitted = True
            
            # Get explained variance ratios
            explained_variance = self.pca.explained_variance_ratio_
            cumulative_variance = np.cumsum(explained_variance)
            
            # Get principal components (loadings)
            components = self.pca.components_
            
            # Create results dictionary
            results = {
                'explained_variance_ratio': explained_variance,
                'cumulative_variance': cumulative_variance,
                'components': components,
                'feature_names': yield_changes.columns.tolist(),
                'n_components': len(explained_variance)
            }
            
            # Interpret first few components
            interpretation = self._interpret_components(components[:4], yield_changes.columns)
            results['interpretation'] = interpretation
            
            logger.info(f"PCA fitted: First 3 components explain {cumulative_variance[2]:.1%} of variance")
            
            return results
            
        except Exception as e:
            logger.error(f"Error fitting PCA: {e}")
            return {}
    
    def transform(self, yield_changes: pd.DataFrame) -> np.ndarray:
        """Transform yield changes to principal component space"""
        if not self.fitted:
            raise ValueError("PCA must be fitted before transformation")
            
        scaled_data = self.scaler.transform(yield_changes.fillna(0))
        return self.pca.transform(scaled_data)
    
    def _interpret_components(self, components: np.ndarray, maturity_labels: List[str]) -> Dict[str, str]:
        """Interpret the first few principal components"""
        interpretations = {}
        
        for i, component in enumerate(components):
            if i < len(self.component_names):
                name = self.component_names[i]
                
                # Analyze the loadings pattern
                if i == 0:  # Level factor
                    if np.all(component > 0) or np.all(component < 0):
                        interpretations[name] = "Parallel shift in yield curve (Level)"
                    else:
                        interpretations[name] = "Mixed level movement"
                        
                elif i == 1:  # Slope factor
                    if component[0] * component[-1] < 0:  # Opposite signs at ends
                        interpretations[name] = "Yield curve steepening/flattening (Slope)"
                    else:
                        interpretations[name] = "Non-standard slope movement"
                        
                elif i == 2:  # Curvature factor
                    mid_point = len(component) // 2
                    if component[mid_point] * component[0] < 0:
                        interpretations[name] = "Yield curve curvature change"
                    else:
                        interpretations[name] = "Non-standard curvature movement"
                        
                else:
                    interpretations[name] = f"Higher-order factor {i+1}"
        
        return interpretations

class AdvancedAnalyticsEngine:
    """
    Main engine coordinating all advanced analytics
    """
    
    def __init__(self):
        self.nelson_siegel = NelsonSiegelModel()
        self.svensson = SvenssonModel()
        self.bond_analytics = BondAnalytics()
        self.var_calculator = VaRCalculator()
        self.pca_analyzer = PrincipalComponentAnalysis()
        
    def comprehensive_bond_analysis(self, cusip: str, price: float, yield_rate: float,
                                  coupon_rate: float, maturity_years: float) -> BondMetrics:
        """Perform comprehensive bond analysis"""
        try:
            # Calculate duration and convexity
            mac_duration, mod_duration = self.bond_analytics.calculate_duration(
                price, yield_rate, coupon_rate, maturity_years
            )
            
            convexity = self.bond_analytics.calculate_convexity(
                price, yield_rate, coupon_rate, maturity_years
            )
            
            # Calculate DV01
            dv01 = self.bond_analytics.calculate_dv01(price, mod_duration)
            
            # Mock key rate durations (would use real yield curve in production)
            mock_curve_points = [
                YieldCurvePoint(0.25, 0.01, datetime.now()),
                YieldCurvePoint(2.0, 0.02, datetime.now()),
                YieldCurvePoint(10.0, 0.04, datetime.now())
            ]
            
            key_rate_durations = self.bond_analytics.calculate_key_rate_durations(
                mock_curve_points, maturity_years, yield_rate
            )
            
            return BondMetrics(
                cusip=cusip,
                price=price,
                yield_rate=yield_rate,
                duration=mac_duration,
                modified_duration=mod_duration,
                convexity=convexity,
                dv01=dv01,
                key_rate_durations=key_rate_durations,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in comprehensive bond analysis: {e}")
            return None
    
    def fit_yield_curve(self, maturities: List[float], yields: List[float], 
                       model: str = 'nelson_siegel') -> Dict[str, Any]:
        """Fit yield curve model"""
        try:
            maturities_array = np.array(maturities)
            yields_array = np.array(yields)
            
            if model == 'nelson_siegel':
                return self.nelson_siegel.fit(maturities_array, yields_array)
            elif model == 'svensson':
                return self.svensson.fit(maturities_array, yields_array)
            else:
                raise ValueError("Model must be 'nelson_siegel' or 'svensson'")
                
        except Exception as e:
            logger.error(f"Error fitting yield curve: {e}")
            return {}
    
    def calculate_portfolio_var(self, returns: np.ndarray, method: str = 'historical',
                              confidence_level: float = 0.95) -> Dict[str, float]:
        """Calculate portfolio VaR using specified method"""
        try:
            if method == 'historical':
                return self.var_calculator.historical_var(returns, confidence_level)
            elif method == 'parametric':
                return self.var_calculator.parametric_var(returns, confidence_level)
            elif method == 'monte_carlo':
                return self.var_calculator.monte_carlo_var(returns, confidence_level)
            else:
                raise ValueError("Method must be 'historical', 'parametric', or 'monte_carlo'")
                
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return {}

# Example usage and testing
if __name__ == "__main__":
    # Test the analytics engine
    engine = AdvancedAnalyticsEngine()
    
    # Test bond analysis
    bond_metrics = engine.comprehensive_bond_analysis(
        cusip="912828XG8",
        price=99.5,
        yield_rate=0.045,
        coupon_rate=0.04,
        maturity_years=10.0
    )
    
    if bond_metrics:
        print(f"Bond Analysis Results:")
        print(f"Duration: {bond_metrics.duration:.2f}")
        print(f"Modified Duration: {bond_metrics.modified_duration:.2f}")
        print(f"Convexity: {bond_metrics.convexity:.2f}")
        print(f"DV01: ${bond_metrics.dv01:.2f}")
    
    # Test yield curve fitting
    maturities = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]
    yields = [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.042, 0.045, 0.044]
    
    curve_results = engine.fit_yield_curve(maturities, yields)
    if curve_results:
        print(f"\nYield Curve Fitting Results:")
        print(f"R²: {curve_results.get('r_squared', 0):.4f}")
        print(f"RMSE: {curve_results.get('rmse', 0):.4f}")
    
    # Test VaR calculation with mock returns
    mock_returns = np.random.normal(-0.001, 0.02, 252)  # 1 year of daily returns
    var_results = engine.calculate_portfolio_var(mock_returns, method='historical')
    
    if var_results:
        print(f"\nVaR Analysis Results:")
        print(f"95% VaR: {var_results.get('var', 0):.4f}")
        print(f"Expected Shortfall: {var_results.get('expected_shortfall', 0):.4f}")
