"""
Plotly Chart Generation for Finance Tracker

This module creates interactive charts using Plotly for treasury prices,
repo spreads, and pricing divergence analysis with professional styling
and financial market conventions.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import structlog

# Initialize structured logger
logger = structlog.get_logger(__name__)


class PlotlyChartGenerator:
    """
    Generates interactive Plotly charts for financial data visualization.
    
    This class creates professional-grade financial charts with:
    - Time-series analysis for treasury prices
    - Repo spread trend analysis
    - BVAL vs internal pricing divergence charts
    - Multi-panel dashboards with synchronized axes
    - Interactive features like zoom, hover, and crossfilter
    - Professional financial styling and color schemes
    """
    
    def __init__(self):
        """Initialize the Plotly chart generator with default styling."""
        # Define professional color scheme for financial charts
        self.color_scheme = {
            'primary': '#1f77b4',      # Blue for primary data
            'secondary': '#ff7f0e',    # Orange for secondary data
            'success': '#2ca02c',      # Green for positive/gains
            'danger': '#d62728',       # Red for negative/losses
            'warning': '#ff7f0e',      # Orange for warnings
            'info': '#17a2b8',         # Teal for information
            'neutral': '#6c757d',      # Gray for neutral data
            'background': '#f8f9fa',   # Light gray background
            'grid': '#e9ecef',         # Light grid lines
            'text': '#212529'          # Dark text
        }
        
        # Default layout settings for financial charts
        self.default_layout = {
            'template': 'plotly_white',
            'font': {'family': 'Arial, sans-serif', 'size': 12},
            'title': {'font': {'size': 16, 'color': self.color_scheme['text']}},
            'showlegend': True,
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.15,
                'xanchor': 'center',
                'x': 0.5
            },
            'margin': {'l': 60, 'r': 30, 't': 80, 'b': 80},
            'hovermode': 'x unified'
        }
        
        logger.info("PlotlyChartGenerator initialized with professional styling")
    
    def create_treasury_price_timeseries(
        self,
        price_data: pd.DataFrame,
        cusip: str,
        title: Optional[str] = None,
        show_divergence: bool = True,
        height: int = 500
    ) -> go.Figure:
        """
        Create time-series chart for treasury prices with BVAL vs internal comparison.
        
        Args:
            price_data: DataFrame with columns: date, bval_price, internal_price, cusip
            cusip: CUSIP to filter and display
            title: Chart title (auto-generated if None)
            show_divergence: Whether to highlight price divergences
            height: Chart height in pixels
            
        Returns:
            go.Figure: Interactive Plotly figure
        """
        logger.info(
            "Creating treasury price time-series chart",
            cusip=cusip,
            data_points=len(price_data)
        )
        
        # Filter data for specific CUSIP
        cusip_data = price_data[price_data['cusip'] == cusip].copy()
        
        if cusip_data.empty:
            logger.warning("No data found for CUSIP", cusip=cusip)
            return self._create_empty_chart(f"No data available for CUSIP {cusip}")
        
        # Sort by date
        cusip_data = cusip_data.sort_values('price_date')
        
        # Create figure with secondary y-axis for divergence
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=['Treasury Prices', 'BVAL vs Internal Divergence'],
            row_heights=[0.7, 0.3] if show_divergence else [1.0]
        )
        
        # Add BVAL price line
        if 'bval_price' in cusip_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=cusip_data['price_date'],
                    y=cusip_data['bval_price'],
                    mode='lines+markers',
                    name='BVAL Price',
                    line=dict(color=self.color_scheme['primary'], width=2),
                    marker=dict(size=4),
                    hovertemplate='<b>BVAL Price</b><br>' +
                                'Date: %{x}<br>' +
                                'Price: $%{y:.4f}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # Add internal price line
        if 'internal_price' in cusip_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=cusip_data['price_date'],
                    y=cusip_data['internal_price'],
                    mode='lines+markers',
                    name='Internal Price',
                    line=dict(color=self.color_scheme['secondary'], width=2),
                    marker=dict(size=4),
                    hovertemplate='<b>Internal Price</b><br>' +
                                'Date: %{x}<br>' +
                                'Price: $%{y:.4f}<extra></extra>'
                ),
                row=1, col=1
            )
        
        # Add divergence subplot if requested
        if show_divergence and 'bval_price' in cusip_data.columns and 'internal_price' in cusip_data.columns:
            # Calculate price divergence
            cusip_data['price_divergence'] = cusip_data['internal_price'] - cusip_data['bval_price']
            
            # Color-code divergence (positive = green, negative = red)
            colors = [self.color_scheme['success'] if x >= 0 else self.color_scheme['danger'] 
                     for x in cusip_data['price_divergence']]
            
            fig.add_trace(
                go.Bar(
                    x=cusip_data['price_date'],
                    y=cusip_data['price_divergence'],
                    name='Price Divergence',
                    marker_color=colors,
                    hovertemplate='<b>Price Divergence</b><br>' +
                                'Date: %{x}<br>' +
                                'Divergence: $%{y:.4f}<br>' +
                                '<i>(Internal - BVAL)</i><extra></extra>'
                ),
                row=2, col=1
            )
            
            # Add zero line for reference
            fig.add_hline(
                y=0, line_dash="dash", line_color=self.color_scheme['neutral'],
                row=2, col=1, annotation_text="No Divergence"
            )
        
        # Update layout
        chart_title = title or f"Treasury Price Analysis - {cusip}"
        
        fig.update_layout(
            title={
                'text': chart_title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': self.color_scheme['text']}
            },
            height=height,
            **self.default_layout
        )
        
        # Update x-axes
        fig.update_xaxes(
            title_text="Date",
            gridcolor=self.color_scheme['grid'],
            row=2 if show_divergence else 1, col=1
        )
        
        # Update y-axes
        fig.update_yaxes(
            title_text="Price ($)",
            gridcolor=self.color_scheme['grid'],
            tickformat='.4f',
            row=1, col=1
        )
        
        if show_divergence:
            fig.update_yaxes(
                title_text="Divergence ($)",
                gridcolor=self.color_scheme['grid'],
                tickformat='.4f',
                row=2, col=1
            )
        
        logger.info(
            "Treasury price time-series chart created successfully",
            cusip=cusip,
            chart_height=height,
            show_divergence=show_divergence
        )
        
        return fig
    
    def create_repo_spread_analysis(
        self,
        repo_data: pd.DataFrame,
        cusips: Optional[List[str]] = None,
        title: Optional[str] = None,
        height: int = 600
    ) -> go.Figure:
        """
        Create multi-panel chart for repo spread analysis across terms and securities.
        
        Args:
            repo_data: DataFrame with repo spread data
            cusips: List of CUSIPs to include (all if None)
            title: Chart title
            height: Chart height in pixels
            
        Returns:
            go.Figure: Interactive Plotly figure with repo spread analysis
        """
        logger.info(
            "Creating repo spread analysis chart",
            data_points=len(repo_data),
            cusips=cusips
        )
        
        if repo_data.empty:
            return self._create_empty_chart("No repo spread data available")
        
        # Filter by CUSIPs if specified
        if cusips:
            repo_data = repo_data[repo_data['cusip'].isin(cusips)]
        
        # Create subplots for different spread terms
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Overnight Repo Spreads',
                '1-Week Repo Spreads', 
                '1-Month Repo Spreads',
                '3-Month Repo Spreads'
            ],
            shared_xaxes=True,
            vertical_spacing=0.12,
            horizontal_spacing=0.08
        )
        
        # Define spread columns and their positions
        spread_configs = [
            ('overnight_spread', 1, 1),
            ('one_week_spread', 1, 2),
            ('one_month_spread', 2, 1),
            ('three_month_spread', 2, 2)
        ]
        
        # Color palette for different CUSIPs
        colors = px.colors.qualitative.Set1
        cusip_colors = {}
        
        for i, (spread_col, row, col) in enumerate(spread_configs):
            if spread_col not in repo_data.columns:
                continue
            
            # Group by CUSIP and plot each separately
            for idx, cusip in enumerate(repo_data['cusip'].unique()):
                if cusip not in cusip_colors:
                    cusip_colors[cusip] = colors[idx % len(colors)]
                
                cusip_data = repo_data[repo_data['cusip'] == cusip].sort_values('data_date')
                
                if cusip_data[spread_col].notna().any():
                    fig.add_trace(
                        go.Scatter(
                            x=cusip_data['data_date'],
                            y=cusip_data[spread_col] * 10000,  # Convert to basis points
                            mode='lines+markers',
                            name=f"{cusip}" if i == 0 else None,  # Only show legend once
                            showlegend=i == 0,
                            line=dict(color=cusip_colors[cusip], width=2),
                            marker=dict(size=4),
                            hovertemplate=f'<b>{cusip}</b><br>' +
                                        'Date: %{x}<br>' +
                                        'Spread: %{y:.1f} bps<extra></extra>'
                        ),
                        row=row, col=col
                    )
        
        # Update layout
        chart_title = title or "Repo Spread Analysis Across Terms"
        
        fig.update_layout(
            title={
                'text': chart_title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': self.color_scheme['text']}
            },
            height=height,
            **self.default_layout
        )
        
        # Update all y-axes to show basis points
        for row in [1, 2]:
            for col in [1, 2]:
                fig.update_yaxes(
                    title_text="Spread (bps)",
                    gridcolor=self.color_scheme['grid'],
                    tickformat='.1f',
                    row=row, col=col
                )
        
        # Update bottom x-axes
        fig.update_xaxes(
            title_text="Date",
            gridcolor=self.color_scheme['grid'],
            row=2, col=1
        )
        fig.update_xaxes(
            title_text="Date",
            gridcolor=self.color_scheme['grid'],
            row=2, col=2
        )
        
        logger.info("Repo spread analysis chart created successfully")
        
        return fig
    
    def create_pricing_divergence_heatmap(
        self,
        price_data: pd.DataFrame,
        title: Optional[str] = None,
        height: int = 500
    ) -> go.Figure:
        """
        Create heatmap showing pricing divergences across CUSIPs and time.
        
        Args:
            price_data: DataFrame with pricing data
            title: Chart title
            height: Chart height in pixels
            
        Returns:
            go.Figure: Interactive heatmap of pricing divergences
        """
        logger.info(
            "Creating pricing divergence heatmap",
            data_points=len(price_data)
        )
        
        if price_data.empty or 'bval_price' not in price_data.columns or 'internal_price' not in price_data.columns:
            return self._create_empty_chart("Insufficient data for divergence heatmap")
        
        # Calculate divergence
        price_data = price_data.copy()
        price_data['divergence'] = price_data['internal_price'] - price_data['bval_price']
        
        # Create pivot table for heatmap
        heatmap_data = price_data.pivot_table(
            values='divergence',
            index='cusip',
            columns='price_date',
            aggfunc='mean'
        )
        
        if heatmap_data.empty:
            return self._create_empty_chart("No divergence data available for heatmap")
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='RdYlBu_r',  # Red for negative, Blue for positive
            zmid=0,  # Center colorscale at zero
            hovertemplate='<b>%{y}</b><br>' +
                         'Date: %{x}<br>' +
                         'Divergence: $%{z:.4f}<br>' +
                         '<i>(Internal - BVAL)</i><extra></extra>',
            colorbar=dict(
                title="Price Divergence ($)",
                titleside="right"
            )
        ))
        
        # Update layout
        chart_title = title or "BVAL vs Internal Pricing Divergence Heatmap"
        
        fig.update_layout(
            title={
                'text': chart_title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': self.color_scheme['text']}
            },
            xaxis_title="Date",
            yaxis_title="CUSIP",
            height=height,
            **self.default_layout
        )
        
        logger.info("Pricing divergence heatmap created successfully")
        
        return fig
    
    def create_score_distribution_chart(
        self,
        score_data: pd.DataFrame,
        score_column: str = 'composite_score',
        title: Optional[str] = None,
        height: int = 400
    ) -> go.Figure:
        """
        Create distribution chart for composite scores.
        
        Args:
            score_data: DataFrame with score data
            score_column: Column name for scores to analyze
            title: Chart title
            height: Chart height in pixels
            
        Returns:
            go.Figure: Score distribution histogram with statistics
        """
        logger.info(
            "Creating score distribution chart",
            score_column=score_column,
            data_points=len(score_data)
        )
        
        if score_data.empty or score_column not in score_data.columns:
            return self._create_empty_chart(f"No data available for {score_column}")
        
        scores = score_data[score_column].dropna()
        
        if scores.empty:
            return self._create_empty_chart(f"No valid scores in {score_column}")
        
        # Create histogram
        fig = go.Figure()
        
        fig.add_trace(
            go.Histogram(
                x=scores,
                nbinsx=30,
                name='Score Distribution',
                marker_color=self.color_scheme['primary'],
                opacity=0.7,
                hovertemplate='Score Range: %{x}<br>' +
                             'Count: %{y}<extra></extra>'
            )
        )
        
        # Add statistical reference lines
        mean_score = scores.mean()
        median_score = scores.median()
        
        fig.add_vline(
            x=mean_score,
            line_dash="dash",
            line_color=self.color_scheme['danger'],
            annotation_text=f"Mean: {mean_score:.1f}"
        )
        
        fig.add_vline(
            x=median_score,
            line_dash="dot",
            line_color=self.color_scheme['success'],
            annotation_text=f"Median: {median_score:.1f}"
        )
        
        # Update layout
        chart_title = title or f"Distribution of {score_column.replace('_', ' ').title()}"
        
        fig.update_layout(
            title={
                'text': chart_title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': self.color_scheme['text']}
            },
            xaxis_title="Score",
            yaxis_title="Frequency",
            height=height,
            **self.default_layout
        )
        
        logger.info("Score distribution chart created successfully")
        
        return fig
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """
        Create an empty chart with a message for cases with no data.
        
        Args:
            message: Message to display
            
        Returns:
            go.Figure: Empty chart with message
        """
        fig = go.Figure()
        
        fig.add_annotation(
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            text=message,
            showarrow=False,
            font=dict(size=16, color=self.color_scheme['neutral'])
        )
        
        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            **self.default_layout
        )
        
        return fig
