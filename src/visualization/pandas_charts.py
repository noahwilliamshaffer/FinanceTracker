"""
Pandas-based Chart Generation for Finance Tracker
Integration with existing scoring models and data pipeline
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import structlog

from ..models.treasury import TreasuryData, TreasuryPrice
from ..models.repo import RepoData
from ..models.scoring import ScoreData
from ..scoring.scoring import ScoreCalculator

logger = structlog.get_logger(__name__)


class PandasChartGenerator:
    """
    Advanced pandas-based chart generator integrated with Finance Tracker models.
    
    This class creates production-ready financial visualizations using pandas
    for data manipulation and plotly for interactive charts.
    """
    
    def __init__(self):
        """Initialize the pandas chart generator."""
        self.score_calculator = ScoreCalculator()
        
    def create_scoring_dashboard(
        self, 
        treasury_data: List[TreasuryData],
        repo_data: List[RepoData],
        historical_prices: Dict[str, List[TreasuryPrice]]
    ) -> go.Figure:
        """
        Create comprehensive scoring dashboard using pandas analytics.
        
        Args:
            treasury_data: List of treasury security data
            repo_data: List of repo market data
            historical_prices: Historical price data by CUSIP
            
        Returns:
            go.Figure: Interactive scoring dashboard
        """
        logger.info("Creating scoring dashboard with pandas analytics")
        
        # Convert to pandas DataFrames for analysis
        treasury_df = pd.DataFrame([t.dict() for t in treasury_data])
        repo_df = pd.DataFrame([r.dict() for r in repo_data])
        
        # Calculate scores for each security
        scores_data = []
        for treasury in treasury_data:
            cusip = treasury.cusip
            repo = next((r for r in repo_data if r.cusip == cusip), None)
            hist_prices = historical_prices.get(cusip, [])
            
            try:
                score = self.score_calculator.calculate_score(
                    cusip=cusip,
                    treasury_data=treasury,
                    repo_data=repo,
                    historical_prices=hist_prices
                )
                scores_data.append(score.dict())
            except Exception as e:
                logger.warning(f"Score calculation failed for {cusip}", error=str(e))
        
        scores_df = pd.DataFrame(scores_data)
        
        # Create multi-panel dashboard
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Composite Scores by Security',
                'Signal Breakdown Analysis', 
                'Risk vs Opportunity Matrix',
                'Score Distribution'
            ),
            specs=[
                [{"type": "bar"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "histogram"}]
            ]
        )
        
        # Panel 1: Composite scores bar chart
        fig.add_trace(
            go.Bar(
                x=scores_df['cusip'],
                y=scores_df['composite_score'],
                name='Composite Score',
                marker_color=scores_df['composite_score'],
                colorscale='RdYlGn',
                hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}/100<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Panel 2: Signal breakdown radar/scatter
        for i, row in scores_df.iterrows():
            fig.add_trace(
                go.Scatter(
                    x=[row['repo_score']],
                    y=[row['divergence_score']],
                    mode='markers+text',
                    text=[row['cusip']],
                    textposition='top center',
                    marker=dict(
                        size=row['composite_score'],
                        sizemode='diameter',
                        sizeref=2,
                        color=row['volatility_score'],
                        colorscale='Viridis',
                        showscale=True
                    ),
                    name=row['cusip'],
                    hovertemplate='<b>%{text}</b><br>Repo: %{x:.1f}<br>Divergence: %{y:.1f}<br>Volatility: %{marker.color:.1f}<extra></extra>'
                ),
                row=1, col=2
            )
        
        # Panel 3: Risk vs Opportunity matrix
        fig.add_trace(
            go.Scatter(
                x=scores_df['volatility_score'],  # Risk proxy (higher volatility = higher risk)
                y=scores_df['composite_score'],   # Opportunity
                mode='markers+text',
                text=scores_df['cusip'],
                textposition='top center',
                marker=dict(
                    size=scores_df['volume_score'],
                    sizemode='diameter',
                    sizeref=2,
                    color='blue',
                    opacity=0.7
                ),
                name='Risk vs Opportunity',
                hovertemplate='<b>%{text}</b><br>Risk Score: %{x:.1f}<br>Opportunity: %{y:.1f}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # Panel 4: Score distribution histogram
        fig.add_trace(
            go.Histogram(
                x=scores_df['composite_score'],
                nbinsx=10,
                name='Score Distribution',
                marker_color='lightblue',
                opacity=0.7
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title='Finance Tracker - Scoring Dashboard',
            height=800,
            showlegend=False,
            template='plotly_white'
        )
        
        # Update axes
        fig.update_xaxes(title_text="CUSIP", row=1, col=1)
        fig.update_yaxes(title_text="Score", row=1, col=1)
        fig.update_xaxes(title_text="Repo Score", row=1, col=2)
        fig.update_yaxes(title_text="Divergence Score", row=1, col=2)
        fig.update_xaxes(title_text="Risk Score", row=2, col=1)
        fig.update_yaxes(title_text="Opportunity Score", row=2, col=1)
        fig.update_xaxes(title_text="Composite Score", row=2, col=2)
        fig.update_yaxes(title_text="Frequency", row=2, col=2)
        
        return fig
    
    def create_time_series_analysis(
        self,
        historical_prices: Dict[str, List[TreasuryPrice]],
        lookback_days: int = 90
    ) -> go.Figure:
        """
        Create advanced time series analysis with pandas.
        
        Args:
            historical_prices: Historical price data by CUSIP
            lookback_days: Number of days to analyze
            
        Returns:
            go.Figure: Time series analysis dashboard
        """
        logger.info("Creating time series analysis", lookback_days=lookback_days)
        
        # Convert to pandas DataFrame
        all_prices = []
        for cusip, prices in historical_prices.items():
            for price in prices:
                all_prices.append({
                    'cusip': cusip,
                    'date': price.price_date,
                    'bval_price': float(price.bval_price) if price.bval_price else None,
                    'internal_price': float(price.internal_price) if price.internal_price else None,
                    'discount_price': float(price.discount_price) if price.discount_price else None,
                    'dollar_price': float(price.dollar_price) if price.dollar_price else None
                })
        
        df = pd.DataFrame(all_prices)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(['cusip', 'date'])
        
        # Calculate technical indicators using pandas
        for cusip in df['cusip'].unique():
            mask = df['cusip'] == cusip
            cusip_data = df[mask].copy()
            
            # Moving averages
            cusip_data['ma_5'] = cusip_data['bval_price'].rolling(window=5).mean()
            cusip_data['ma_20'] = cusip_data['bval_price'].rolling(window=20).mean()
            
            # Bollinger Bands
            cusip_data['bb_std'] = cusip_data['bval_price'].rolling(window=20).std()
            cusip_data['bb_upper'] = cusip_data['ma_20'] + (2 * cusip_data['bb_std'])
            cusip_data['bb_lower'] = cusip_data['ma_20'] - (2 * cusip_data['bb_std'])
            
            # Price divergence
            cusip_data['divergence'] = cusip_data['internal_price'] - cusip_data['bval_price']
            cusip_data['divergence_pct'] = (cusip_data['divergence'] / cusip_data['bval_price']) * 100
            
            # Daily returns
            cusip_data['returns'] = cusip_data['bval_price'].pct_change()
            cusip_data['volatility'] = cusip_data['returns'].rolling(window=20).std() * np.sqrt(252)
            
            # Update main dataframe
            df.loc[mask, cusip_data.columns] = cusip_data
        
        # Create comprehensive chart
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                'Price Trends with Technical Indicators',
                'Price Divergence Analysis',
                'Rolling Volatility'
            ),
            vertical_spacing=0.08,
            row_heights=[0.5, 0.25, 0.25]
        )
        
        # Panel 1: Price trends with Bollinger Bands
        for cusip in df['cusip'].unique():
            cusip_data = df[df['cusip'] == cusip]
            
            # Main price line
            fig.add_trace(
                go.Scatter(
                    x=cusip_data['date'],
                    y=cusip_data['bval_price'],
                    name=f'{cusip} BVAL',
                    line=dict(width=2),
                    hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>Price: $%{y:.4f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Moving averages
            fig.add_trace(
                go.Scatter(
                    x=cusip_data['date'],
                    y=cusip_data['ma_20'],
                    name=f'{cusip} MA20',
                    line=dict(width=1, dash='dash'),
                    opacity=0.7,
                    hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>MA20: $%{y:.4f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Bollinger Bands
            fig.add_trace(
                go.Scatter(
                    x=cusip_data['date'],
                    y=cusip_data['bb_upper'],
                    fill=None,
                    mode='lines',
                    line=dict(width=0),
                    name=f'{cusip} BB Upper',
                    showlegend=False
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=cusip_data['date'],
                    y=cusip_data['bb_lower'],
                    fill='tonexty',
                    mode='lines',
                    line=dict(width=0),
                    name=f'{cusip} Bollinger Bands',
                    fillcolor='rgba(128,128,128,0.1)'
                ),
                row=1, col=1
            )
        
        # Panel 2: Price divergence
        for cusip in df['cusip'].unique():
            cusip_data = df[df['cusip'] == cusip]
            
            fig.add_trace(
                go.Scatter(
                    x=cusip_data['date'],
                    y=cusip_data['divergence_pct'],
                    name=f'{cusip} Divergence %',
                    mode='lines+markers',
                    marker=dict(size=3),
                    hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>Divergence: %{y:.3f}%<extra></extra>'
                ),
                row=2, col=1
            )
        
        # Add zero line for divergence
        fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2, col=1)
        
        # Panel 3: Rolling volatility
        for cusip in df['cusip'].unique():
            cusip_data = df[df['cusip'] == cusip]
            
            fig.add_trace(
                go.Scatter(
                    x=cusip_data['date'],
                    y=cusip_data['volatility'] * 100,  # Convert to percentage
                    name=f'{cusip} Volatility',
                    mode='lines',
                    line=dict(width=2),
                    hovertemplate='<b>%{fullData.name}</b><br>%{x}<br>Volatility: %{y:.2f}%<extra></extra>'
                ),
                row=3, col=1
            )
        
        # Update layout
        fig.update_layout(
            title='Advanced Time Series Analysis - Finance Tracker',
            height=1000,
            hovermode='x unified',
            template='plotly_white'
        )
        
        fig.update_xaxes(title_text="Date", row=3, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Divergence (%)", row=2, col=1)
        fig.update_yaxes(title_text="Volatility (%)", row=3, col=1)
        
        return fig
    
    def export_data_to_csv(
        self,
        treasury_data: List[TreasuryData],
        repo_data: List[RepoData],
        scores_data: List[ScoreData],
        output_path: str = "finance_tracker_export.csv"
    ) -> str:
        """
        Export all data to CSV using pandas for further analysis.
        
        Args:
            treasury_data: Treasury securities data
            repo_data: Repo market data
            scores_data: Scoring results
            output_path: Output CSV file path
            
        Returns:
            str: Path to exported CSV file
        """
        logger.info("Exporting data to CSV", output_path=output_path)
        
        # Convert all data to DataFrames
        treasury_df = pd.DataFrame([t.dict() for t in treasury_data])
        repo_df = pd.DataFrame([r.dict() for r in repo_data])
        scores_df = pd.DataFrame([s.dict() for s in scores_data])
        
        # Merge data on CUSIP
        merged_df = treasury_df.merge(repo_df, on='cusip', how='left', suffixes=('', '_repo'))
        merged_df = merged_df.merge(scores_df, on='cusip', how='left', suffixes=('', '_score'))
        
        # Add calculated fields
        merged_df['price_divergence_abs'] = abs(merged_df['internal_price'] - merged_df['bval_price'])
        merged_df['price_divergence_pct'] = (merged_df['price_divergence_abs'] / merged_df['bval_price']) * 100
        merged_df['export_timestamp'] = datetime.now()
        
        # Export to CSV
        merged_df.to_csv(output_path, index=False)
        
        logger.info("Data exported successfully", 
                   records=len(merged_df),
                   columns=len(merged_df.columns),
                   file_size=f"{merged_df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        
        return output_path
