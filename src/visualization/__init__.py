"""
Data visualization components for Finance Tracker.

This package provides interactive dashboards and charts for treasury
and repo market data analysis using Plotly and Matplotlib with
FastAPI web interface integration.
"""

from .dashboard import DashboardGenerator
from .charts import ChartFactory
from .plotly_charts import PlotlyChartGenerator
from .matplotlib_charts import MatplotlibChartGenerator

__all__ = [
    "DashboardGenerator",
    "ChartFactory",
    "PlotlyChartGenerator",
    "MatplotlibChartGenerator",
]
