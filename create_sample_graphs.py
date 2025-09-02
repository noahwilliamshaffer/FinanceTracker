#!/usr/bin/env python3
"""
Sample Graph Generator for Finance Tracker
Demonstrates how to create professional financial charts with pandas and plotly
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import random

def create_sample_data():
    """Generate sample financial data using pandas"""
    
    # Create date range for last 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Sample CUSIPs (Treasury securities)
    cusips = [
        "912828XG8",  # 10Y Treasury Note
        "912828YK0",  # 2Y Treasury Note  
        "912810RZ3",  # 30Y Treasury Bond
        "912828ZH5",  # 5Y Treasury Note
    ]
    
    # Generate Treasury price data
    treasury_data = []
    for cusip in cusips:
        base_price = random.uniform(98.0, 102.0)  # Base price around par
        
        for i, date in enumerate(dates):
            # Add some realistic price movement
            price_change = np.random.normal(0, 0.1)  # Small daily changes
            current_price = base_price + (i * 0.01) + price_change
            
            # BVAL vs Internal pricing with some divergence
            bval_price = current_price + np.random.normal(0, 0.05)
            internal_price = current_price + np.random.normal(0, 0.08)
            
            treasury_data.append({
                'date': date,
                'cusip': cusip,
                'bval_price': round(bval_price, 4),
                'internal_price': round(internal_price, 4),
                'volume': random.randint(50000, 2000000),
                'repo_spread': abs(np.random.normal(0.0025, 0.0005))  # Repo spread in decimal
            })
    
    return pd.DataFrame(treasury_data)

def create_treasury_price_chart(df):
    """Create interactive treasury price time series chart"""
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Treasury Prices Over Time', 'BVAL vs Internal Price Divergence'),
        vertical_spacing=0.1,
        specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
    )
    
    # Top chart: Price trends by CUSIP
    for cusip in df['cusip'].unique():
        cusip_data = df[df['cusip'] == cusip]
        
        # BVAL prices
        fig.add_trace(
            go.Scatter(
                x=cusip_data['date'],
                y=cusip_data['bval_price'],
                name=f'{cusip} BVAL',
                line=dict(width=2),
                hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Price: $%{y:.4f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Internal prices  
        fig.add_trace(
            go.Scatter(
                x=cusip_data['date'],
                y=cusip_data['internal_price'],
                name=f'{cusip} Internal',
                line=dict(width=2, dash='dash'),
                hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Price: $%{y:.4f}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # Bottom chart: Price divergence heatmap
    for cusip in df['cusip'].unique():
        cusip_data = df[df['cusip'] == cusip]
        divergence = cusip_data['internal_price'] - cusip_data['bval_price']
        
        fig.add_trace(
            go.Scatter(
                x=cusip_data['date'],
                y=divergence,
                name=f'{cusip} Divergence',
                mode='lines+markers',
                marker=dict(size=4),
                hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Divergence: $%{y:.4f}<extra></extra>'
            ),
            row=2, col=1
        )
    
    # Add zero line for divergence
    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2, col=1)
    
    # Update layout
    fig.update_layout(
        title='Treasury Securities Analysis Dashboard',
        height=800,
        showlegend=True,
        hovermode='x unified',
        template='plotly_white'
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Price Divergence ($)", row=2, col=1)
    
    return fig

def create_repo_spread_analysis(df):
    """Create repo spread analysis with volume overlay"""
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Group by date and calculate average spread
    daily_spreads = df.groupby('date').agg({
        'repo_spread': 'mean',
        'volume': 'sum'
    }).reset_index()
    
    # Repo spread trend
    fig.add_trace(
        go.Scatter(
            x=daily_spreads['date'],
            y=daily_spreads['repo_spread'] * 10000,  # Convert to basis points
            name='Average Repo Spread (bps)',
            line=dict(color='blue', width=3),
            hovertemplate='Date: %{x}<br>Spread: %{y:.1f} bps<extra></extra>'
        ),
        secondary_y=False
    )
    
    # Volume bars
    fig.add_trace(
        go.Bar(
            x=daily_spreads['date'],
            y=daily_spreads['volume'],
            name='Total Volume',
            opacity=0.3,
            marker_color='lightblue',
            hovertemplate='Date: %{x}<br>Volume: $%{y:,.0f}<extra></extra>'
        ),
        secondary_y=True
    )
    
    # Add trend line
    z = np.polyfit(range(len(daily_spreads)), daily_spreads['repo_spread'] * 10000, 1)
    p = np.poly1d(z)
    fig.add_trace(
        go.Scatter(
            x=daily_spreads['date'],
            y=p(range(len(daily_spreads))),
            name='Trend Line',
            line=dict(color='red', width=2, dash='dash'),
            hovertemplate='Trend: %{y:.1f} bps<extra></extra>'
        ),
        secondary_y=False
    )
    
    # Update layout
    fig.update_layout(
        title='Repo Spread Analysis with Volume',
        height=600,
        hovermode='x unified',
        template='plotly_white'
    )
    
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Repo Spread (Basis Points)", secondary_y=False)
    fig.update_yaxes(title_text="Trading Volume ($)", secondary_y=True)
    
    return fig

def create_volatility_heatmap(df):
    """Create volatility heatmap by CUSIP and time period"""
    
    # Calculate rolling volatility (20-day window)
    df_vol = df.copy()
    df_vol = df_vol.sort_values(['cusip', 'date'])
    
    # Calculate daily returns and rolling volatility
    volatility_data = []
    for cusip in df_vol['cusip'].unique():
        cusip_data = df_vol[df_vol['cusip'] == cusip].copy()
        cusip_data['returns'] = cusip_data['bval_price'].pct_change()
        cusip_data['volatility'] = cusip_data['returns'].rolling(window=20).std() * np.sqrt(252)  # Annualized
        
        for _, row in cusip_data.iterrows():
            if not pd.isna(row['volatility']):
                volatility_data.append({
                    'cusip': cusip,
                    'date': row['date'],
                    'volatility': row['volatility'] * 100  # Convert to percentage
                })
    
    vol_df = pd.DataFrame(volatility_data)
    
    # Create pivot table for heatmap
    pivot_df = vol_df.pivot(index='cusip', columns='date', values='volatility')
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale='RdYlBu_r',
        hovertemplate='CUSIP: %{y}<br>Date: %{x}<br>Volatility: %{z:.2f}%<extra></extra>',
        colorbar=dict(title="Volatility (%)")
    ))
    
    fig.update_layout(
        title='Treasury Volatility Heatmap (20-Day Rolling)',
        height=400,
        xaxis_title="Date",
        yaxis_title="CUSIP",
        template='plotly_white'
    )
    
    return fig

def create_correlation_matrix(df):
    """Create correlation matrix of price movements"""
    
    # Pivot data to get prices by CUSIP
    price_pivot = df.pivot(index='date', columns='cusip', values='bval_price')
    
    # Calculate returns
    returns = price_pivot.pct_change().dropna()
    
    # Calculate correlation matrix
    corr_matrix = returns.corr()
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale='RdBu',
        zmin=-1,
        zmax=1,
        hovertemplate='%{y} vs %{x}<br>Correlation: %{z:.3f}<extra></extra>',
        colorbar=dict(title="Correlation")
    ))
    
    # Add correlation values as text
    for i in range(len(corr_matrix)):
        for j in range(len(corr_matrix.columns)):
            fig.add_annotation(
                x=j, y=i,
                text=f"{corr_matrix.iloc[i, j]:.3f}",
                showarrow=False,
                font=dict(color="white" if abs(corr_matrix.iloc[i, j]) > 0.5 else "black")
            )
    
    fig.update_layout(
        title='Treasury Returns Correlation Matrix',
        height=500,
        xaxis_title="CUSIP",
        yaxis_title="CUSIP",
        template='plotly_white'
    )
    
    return fig

def main():
    """Generate and save all sample charts"""
    print("🔄 Generating sample financial data with pandas...")
    
    # Create sample data
    df = create_sample_data()
    print(f"✅ Generated {len(df)} data points for {df['cusip'].nunique()} securities")
    print(f"📊 Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print()
    
    # Show data sample
    print("📋 Sample Data:")
    print(df.head(10).to_string(index=False))
    print()
    
    # Create charts
    print("📈 Creating Treasury Price Chart...")
    price_fig = create_treasury_price_chart(df)
    price_fig.write_html("treasury_prices.html")
    print("✅ Saved: treasury_prices.html")
    
    print("💰 Creating Repo Spread Analysis...")
    spread_fig = create_repo_spread_analysis(df)
    spread_fig.write_html("repo_spreads.html")
    print("✅ Saved: repo_spreads.html")
    
    print("🌡️ Creating Volatility Heatmap...")
    vol_fig = create_volatility_heatmap(df)
    vol_fig.write_html("volatility_heatmap.html")
    print("✅ Saved: volatility_heatmap.html")
    
    print("🔗 Creating Correlation Matrix...")
    corr_fig = create_correlation_matrix(df)
    corr_fig.write_html("correlation_matrix.html")
    print("✅ Saved: correlation_matrix.html")
    
    print()
    print("🎯 ALL GRAPHS CREATED SUCCESSFULLY!")
    print("📂 Open the HTML files in your browser to view interactive charts")
    print()
    print("📊 Data Statistics:")
    print(f"   • Securities: {df['cusip'].nunique()}")
    print(f"   • Time Period: {(df['date'].max() - df['date'].min()).days} days")
    print(f"   • Average Price: ${df['bval_price'].mean():.2f}")
    print(f"   • Average Spread: {df['repo_spread'].mean()*10000:.1f} bps")
    print(f"   • Total Volume: ${df['volume'].sum():,.0f}")

if __name__ == "__main__":
    main()
