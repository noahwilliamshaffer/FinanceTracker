"""
Finance Tracker - Mobile-Responsive Demo
Fully responsive dashboard optimized for mobile, tablet, and desktop
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import date, datetime, timedelta
import json

# Create FastAPI app
app = FastAPI(
    title="Finance Tracker - Mobile Demo",
    description="Mobile-responsive finance data pipeline dashboard",
    version="1.0.0"
)

# Mount static files to serve HTML charts
app.mount("/static", StaticFiles(directory="."), name="static")

# Sample data generators (same as demo.py)
def get_treasury_data():
    """Generate realistic treasury data."""
    cusips = ["912828XG8", "912828YK0", "912810RZ3"]
    securities = {
        "912828XG8": {"name": "10-Year Treasury Note", "maturity": "2034-02-15", "coupon": 4.25},
        "912828YK0": {"name": "2-Year Treasury Note", "maturity": "2026-01-31", "coupon": 4.75},
        "912810RZ3": {"name": "30-Year Treasury Bond", "maturity": "2054-02-15", "coupon": 4.50}
    }
    
    data = []
    for cusip in cusips:
        for i in range(7):
            price_date = date.today() - timedelta(days=i)
            base_price = 99.5 + (hash(cusip) % 100) / 1000
            variation = (i % 3 - 1) * 0.01
            
            data.append({
                "cusip": cusip,
                "security_name": securities[cusip]["name"],
                "maturity_date": securities[cusip]["maturity"],
                "coupon_rate": securities[cusip]["coupon"],
                "price_date": price_date.isoformat(),
                "bval_price": round(base_price + variation, 4),
                "internal_price": round(base_price + variation - 0.005, 4),
                "day_over_day_change": round(variation, 4),
                "price_divergence": round(-0.005, 4)
            })
    
    return data

def get_repo_data():
    """Generate realistic repo spread data."""
    terms = ["Overnight", "1 Week", "1 Month", "3 Month"]
    counterparties = ["Primary Dealers", "Banks", "Money Market Funds"]
    
    data = []
    for term in terms:
        for cp in counterparties:
            for i in range(5):
                trade_date = date.today() - timedelta(days=i)
                base_spread = 15 + len(term) * 2 + (hash(cp) % 10)
                variation = (i % 3 - 1) * 2
                
                data.append({
                    "trade_date": trade_date.isoformat(),
                    "term": term,
                    "counterparty": cp,
                    "spread_bps": round(base_spread + variation, 1),
                    "volume_mm": round(50 + (hash(f"{term}{cp}") % 100), 1),
                    "collateral_type": "Treasury"
                })
    
    return data

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Mobile-responsive main dashboard"""
    
    # CSS and JavaScript for mobile-responsive design
    css_js = """
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        :root {
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --card-shadow: 0 4px 15px rgba(0,0,0,0.1);
            --card-shadow-hover: 0 8px 25px rgba(0,0,0,0.15);
            --border-radius: 12px;
            --transition: all 0.3s ease;
        }
        
        body { 
            background: var(--primary-gradient); 
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            overflow-x: hidden;
        }
        
        /* Mobile-first responsive design */
        .main-container { 
            background: rgba(255,255,255,0.95); 
            border-radius: var(--border-radius); 
            box-shadow: var(--card-shadow);
            margin: 10px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        
        @media (min-width: 768px) {
            .main-container {
                margin: 20px;
                padding: 30px;
            }
        }
        
        /* Mobile-optimized metric cards */
        .metric-card { 
            background: linear-gradient(45deg, #f8f9fa, #e9ecef);
            border: none;
            border-radius: var(--border-radius);
            transition: var(--transition);
            box-shadow: var(--card-shadow);
            margin-bottom: 15px;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            cursor: pointer;
        }
        
        .metric-card:hover { 
            transform: translateY(-5px);
            box-shadow: var(--card-shadow-hover);
        }
        
        /* Responsive metric values */
        .metric-value { 
            font-size: 1.5rem; 
            font-weight: bold; 
            color: #2c3e50;
            line-height: 1.2;
        }
        
        @media (min-width: 576px) {
            .metric-value { font-size: 2rem; }
        }
        
        @media (min-width: 992px) {
            .metric-value { font-size: 2.2rem; }
        }
        
        .metric-label { 
            color: #6c757d; 
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }
        
        @media (min-width: 576px) {
            .metric-label { font-size: 0.9rem; }
        }
        
        /* Mobile-friendly status badges */
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 1px;
            display: inline-block;
            margin: 2px;
        }
        
        @media (min-width: 576px) {
            .status-badge {
                padding: 8px 16px;
                font-size: 0.8rem;
            }
        }
        
        /* Responsive chart cards */
        .chart-card {
            background: white;
            border-radius: var(--border-radius);
            box-shadow: var(--card-shadow);
            transition: var(--transition);
            margin-bottom: 20px;
        }
        
        .chart-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--card-shadow-hover);
        }
        
        .chart-header {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border-radius: var(--border-radius) var(--border-radius) 0 0 !important;
            padding: 12px 15px;
        }
        
        @media (min-width: 768px) {
            .chart-header {
                padding: 15px 20px;
            }
        }
        
        /* Mobile-optimized chart iframes */
        .chart-iframe {
            width: 100%;
            height: 300px;
            border: none;
            border-radius: 0 0 var(--border-radius) var(--border-radius);
        }
        
        @media (min-width: 576px) {
            .chart-iframe { height: 350px; }
        }
        
        @media (min-width: 768px) {
            .chart-iframe { height: 400px; }
        }
        
        @media (min-width: 1200px) {
            .chart-iframe { height: 450px; }
        }
        
        /* Mobile navigation */
        .navbar {
            background: linear-gradient(90deg, #2c3e50 0%, #34495e 100%);
            padding: 10px 15px;
        }
        
        .navbar-brand {
            color: white !important;
            font-weight: bold;
            font-size: 1.2rem;
        }
        
        @media (min-width: 576px) {
            .navbar-brand {
                font-size: 1.5rem;
            }
        }
        
        .navbar-toggler {
            border: none;
            padding: 4px 8px;
        }
        
        .navbar-toggler:focus {
            box-shadow: none;
        }
        
        .navbar-nav .nav-link {
            color: #bdc3c7 !important;
            padding: 8px 15px;
            border-radius: 8px;
            margin: 2px 0;
            transition: var(--transition);
        }
        
        .navbar-nav .nav-link:hover,
        .navbar-nav .nav-link.active {
            background: rgba(255,255,255,0.1);
            color: white !important;
        }
        
        /* Mobile-friendly alerts */
        .alert-custom {
            border: none;
            border-radius: 10px;
            padding: 12px 15px;
            margin-bottom: 15px;
            font-size: 0.9rem;
        }
        
        @media (min-width: 576px) {
            .alert-custom {
                padding: 15px 20px;
                font-size: 1rem;
            }
        }
        
        /* Mobile-optimized buttons */
        .btn-custom {
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
            transition: var(--transition);
            border: none;
            font-size: 0.9rem;
            margin: 2px;
        }
        
        @media (min-width: 576px) {
            .btn-custom {
                padding: 10px 20px;
                font-size: 1rem;
                margin: 5px;
            }
        }
        
        .btn-custom:hover {
            transform: translateY(-2px);
            box-shadow: var(--card-shadow);
        }
        
        /* Touch-friendly improvements */
        @media (hover: none) and (pointer: coarse) {
            .metric-card:hover,
            .chart-card:hover,
            .btn-custom:hover {
                transform: none;
            }
        }
        
        /* Mobile table responsiveness */
        .table-responsive {
            border-radius: var(--border-radius);
            box-shadow: var(--card-shadow);
            font-size: 0.9rem;
        }
        
        @media (min-width: 768px) {
            .table-responsive {
                font-size: 1rem;
            }
        }
        
        /* Mobile card stacking */
        @media (max-width: 767px) {
            .row > [class*="col-"] {
                margin-bottom: 15px;
            }
        }
        
        /* Loading states for mobile */
        .loading-placeholder {
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: loading 1.5s infinite;
            border-radius: var(--border-radius);
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        @keyframes loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        
        /* Accessibility improvements */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            .main-container {
                background: rgba(30,30,30,0.95);
                color: #fff;
            }
            
            .metric-card {
                background: linear-gradient(45deg, #2a2a2a, #3a3a3a);
                color: #fff;
            }
            
            .metric-value {
                color: #fff;
            }
        }
        
        /* PWA-style app bar */
        .app-bar {
            position: sticky;
            top: 0;
            z-index: 1020;
            backdrop-filter: blur(10px);
        }
    </style>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Touch gesture support for charts
            const chartIframes = document.querySelectorAll('.chart-iframe');
            chartIframes.forEach(iframe => {
                iframe.addEventListener('touchstart', function(e) {
                    e.stopPropagation();
                });
            });
            
            // Responsive chart resizing
            function resizeCharts() {
                chartIframes.forEach(iframe => {
                    const container = iframe.parentElement;
                    const containerWidth = container.offsetWidth;
                    
                    if (containerWidth < 576) {
                        iframe.style.height = '300px';
                    } else if (containerWidth < 768) {
                        iframe.style.height = '350px';
                    } else if (containerWidth < 1200) {
                        iframe.style.height = '400px';
                    } else {
                        iframe.style.height = '450px';
                    }
                });
            }
            
            let resizeTimer;
            window.addEventListener('resize', function() {
                clearTimeout(resizeTimer);
                resizeTimer = setTimeout(resizeCharts, 250);
            });
            
            resizeCharts();
            
            // Loading states for better mobile UX
            const cards = document.querySelectorAll('.metric-card, .chart-card');
            cards.forEach(card => {
                card.addEventListener('click', function() {
                    this.style.opacity = '0.7';
                    setTimeout(() => {
                        this.style.opacity = '1';
                    }, 150);
                });
            });
            
            // Prevent zoom on double tap for iOS
            let lastTouchEnd = 0;
            document.addEventListener('touchend', function(event) {
                const now = (new Date()).getTime();
                if (now - lastTouchEnd <= 300) {
                    event.preventDefault();
                }
                lastTouchEnd = now;
            }, false);
            
            // Add pull-to-refresh functionality
            let startY = 0;
            let currentY = 0;
            let pullDistance = 0;
            const threshold = 80;
            
            document.addEventListener('touchstart', function(e) {
                if (window.scrollY === 0) {
                    startY = e.touches[0].clientY;
                }
            });
            
            document.addEventListener('touchmove', function(e) {
                if (window.scrollY === 0 && startY) {
                    currentY = e.touches[0].clientY;
                    pullDistance = currentY - startY;
                    
                    if (pullDistance > 0 && pullDistance < threshold * 2) {
                        e.preventDefault();
                        document.body.style.transform = `translateY(${pullDistance * 0.5}px)`;
                        document.body.style.opacity = 1 - (pullDistance * 0.005);
                    }
                }
            });
            
            document.addEventListener('touchend', function(e) {
                if (pullDistance > threshold) {
                    // Trigger refresh
                    window.location.reload();
                } else {
                    // Reset
                    document.body.style.transform = '';
                    document.body.style.opacity = '';
                }
                startY = 0;
                pullDistance = 0;
            });
        });
        
        // Chart placeholder function for failed loads
        function showPlaceholder(iframe, chartName) {
            const placeholder = document.createElement('div');
            placeholder.className = 'loading-placeholder';
            placeholder.innerHTML = `
                <div class="text-center">
                    <i class="bi bi-bar-chart-line fs-1 text-muted"></i>
                    <p class="mt-2 text-muted">${chartName} Chart<br><small>Loading or unavailable</small></p>
                </div>
            `;
            
            iframe.parentNode.replaceChild(placeholder, iframe);
        }
    </script>
    """
    
    # Main HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        {css_js}
        <title>Finance Tracker - Mobile Dashboard</title>
        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#667eea">
        <link rel="apple-touch-icon" href="/icon-192x192.png">
    </head>
    <body>
        <!-- Mobile Navigation -->
        <nav class="navbar navbar-expand-lg app-bar">
            <div class="container-fluid">
                <a class="navbar-brand" href="/">
                    <i class="bi bi-graph-up"></i> Finance Tracker
                </a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <i class="bi bi-list text-white fs-4"></i>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item">
                            <a class="nav-link active" href="/">
                                <i class="bi bi-house"></i> Dashboard
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/visualizations">
                                <i class="bi bi-bar-chart-line"></i> Charts
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/monitoring">
                                <i class="bi bi-activity"></i> Monitoring
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/docs">
                                <i class="bi bi-book"></i> API
                            </a>
                        </li>
                    </ul>
                </div>
            </div>
        </nav>

        <div class="main-container">
            <!-- Header -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="text-center">
                        <h1 class="display-6 fw-bold text-primary mb-2">
                            <i class="bi bi-graph-up-arrow"></i> Finance Tracker
                        </h1>
                        <p class="lead text-muted">Real-time Treasury & Repo Market Analytics</p>
                        <div class="d-flex flex-wrap justify-content-center gap-2">
                            <span class="status-badge bg-success text-white">
                                <i class="bi bi-check-circle"></i> Live Data
                            </span>
                            <span class="status-badge bg-primary text-white">
                                <i class="bi bi-shield-check"></i> Secure
                            </span>
                            <span class="status-badge bg-info text-white">
                                <i class="bi bi-phone"></i> Mobile Ready
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Key Metrics Cards - Mobile Optimized -->
            <div class="row g-3 mb-4">
                <div class="col-6 col-sm-6 col-md-3">
                    <div class="card metric-card text-center h-100">
                        <div class="card-body d-flex flex-column justify-content-center">
                            <div class="metric-value text-success">$2.5M</div>
                            <div class="metric-label">Portfolio P&L</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-sm-6 col-md-3">
                    <div class="card metric-card text-center h-100">
                        <div class="card-body d-flex flex-column justify-content-center">
                            <div class="metric-value text-primary">24.8</div>
                            <div class="metric-label">Avg Spread (bps)</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-sm-6 col-md-3">
                    <div class="card metric-card text-center h-100">
                        <div class="card-body d-flex flex-column justify-content-center">
                            <div class="metric-value text-info">6.2</div>
                            <div class="metric-label">Duration</div>
                        </div>
                    </div>
                </div>
                <div class="col-6 col-sm-6 col-md-3">
                    <div class="card metric-card text-center h-100">
                        <div class="card-body d-flex flex-column justify-content-center">
                            <div class="metric-value text-warning">$850K</div>
                            <div class="metric-label">95% VaR</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Actions - Mobile Friendly -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-light">
                            <h5 class="card-title mb-0">
                                <i class="bi bi-lightning"></i> Quick Actions
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="row g-2">
                                <div class="col-6 col-sm-4 col-lg-2">
                                    <button class="btn btn-primary btn-custom w-100">
                                        <i class="bi bi-download"></i>
                                        <span class="d-none d-sm-inline"> Export</span>
                                    </button>
                                </div>
                                <div class="col-6 col-sm-4 col-lg-2">
                                    <button class="btn btn-success btn-custom w-100">
                                        <i class="bi bi-arrow-clockwise"></i>
                                        <span class="d-none d-sm-inline"> Refresh</span>
                                    </button>
                                </div>
                                <div class="col-6 col-sm-4 col-lg-2">
                                    <button class="btn btn-warning btn-custom w-100">
                                        <i class="bi bi-bell"></i>
                                        <span class="d-none d-sm-inline"> Alerts</span>
                                    </button>
                                </div>
                                <div class="col-6 col-sm-4 col-lg-2">
                                    <button class="btn btn-info btn-custom w-100">
                                        <i class="bi bi-gear"></i>
                                        <span class="d-none d-sm-inline"> Settings</span>
                                    </button>
                                </div>
                                <div class="col-6 col-sm-4 col-lg-2">
                                    <button class="btn btn-secondary btn-custom w-100">
                                        <i class="bi bi-question-circle"></i>
                                        <span class="d-none d-sm-inline"> Help</span>
                                    </button>
                                </div>
                                <div class="col-6 col-sm-4 col-lg-2">
                                    <button class="btn btn-dark btn-custom w-100">
                                        <i class="bi bi-fullscreen"></i>
                                        <span class="d-none d-sm-inline"> Expand</span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Interactive Charts - Mobile Responsive -->
            <div class="row g-3">
                <!-- Treasury Analysis Chart -->
                <div class="col-12">
                    <div class="card chart-card">
                        <div class="card-header chart-header">
                            <h5><i class="bi bi-graph-up"></i> Treasury Securities Analysis</h5>
                        </div>
                        <div class="card-body p-0">
                            <iframe src="/static/treasury_prices.html" class="chart-iframe" 
                                    onerror="showPlaceholder(this, 'Treasury Analysis')"></iframe>
                        </div>
                        <div class="card-footer">
                            <div class="d-flex flex-wrap gap-2">
                                <a href="/static/treasury_prices.html" target="_blank" class="btn btn-primary btn-sm btn-custom">
                                    <i class="bi bi-box-arrow-up-right"></i> Full View
                                </a>
                                <button class="btn btn-secondary btn-sm btn-custom">
                                    <i class="bi bi-download"></i> Export
                                </button>
                                <button class="btn btn-info btn-sm btn-custom">
                                    <i class="bi bi-share"></i> Share
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Repo Spreads Charts -->
                <div class="col-12 col-lg-6">
                    <div class="card chart-card">
                        <div class="card-header chart-header">
                            <h5><i class="bi bi-bar-chart"></i> Repo Spreads</h5>
                        </div>
                        <div class="card-body p-0">
                            <iframe src="/static/repo_spreads_simple.html" class="chart-iframe" 
                                    onerror="showPlaceholder(this, 'Repo Spreads')"></iframe>
                        </div>
                        <div class="card-footer">
                            <div class="d-flex flex-wrap gap-1">
                                <a href="/static/repo_spreads_simple.html" target="_blank" class="btn btn-primary btn-sm">
                                    <i class="bi bi-graph-up"></i> Simple
                                </a>
                                <a href="/static/repo_spreads_dashboard.html" target="_blank" class="btn btn-success btn-sm">
                                    <i class="bi bi-grid-3x3-gap"></i> Full
                                </a>
                                <a href="/static/repo_spreads_heatmap.html" target="_blank" class="btn btn-warning btn-sm">
                                    <i class="bi bi-thermometer-half"></i> Heat
                                </a>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Volatility Heatmap -->
                <div class="col-12 col-lg-6">
                    <div class="card chart-card">
                        <div class="card-header chart-header">
                            <h5><i class="bi bi-thermometer-half"></i> Volatility Heatmap</h5>
                        </div>
                        <div class="card-body p-0">
                            <iframe src="/static/volatility_heatmap.html" class="chart-iframe" 
                                    onerror="showPlaceholder(this, 'Volatility Heatmap')"></iframe>
                        </div>
                        <div class="card-footer">
                            <a href="/static/volatility_heatmap.html" target="_blank" class="btn btn-primary btn-sm btn-custom">
                                <i class="bi bi-box-arrow-up-right"></i> Full Chart
                            </a>
                        </div>
                    </div>
                </div>

                <!-- Correlation Matrix -->
                <div class="col-12">
                    <div class="card chart-card">
                        <div class="card-header chart-header">
                            <h5><i class="bi bi-diagram-2"></i> Correlation Matrix</h5>
                        </div>
                        <div class="card-body p-0">
                            <iframe src="/static/correlation_matrix.html" class="chart-iframe" 
                                    onerror="showPlaceholder(this, 'Correlation Matrix')"></iframe>
                        </div>
                        <div class="card-footer">
                            <a href="/static/correlation_matrix.html" target="_blank" class="btn btn-primary btn-sm btn-custom">
                                <i class="bi bi-box-arrow-up-right"></i> Full Chart
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Mobile-Optimized Data Tables -->
            <div class="row mt-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-light">
                            <h5 class="card-title mb-0">
                                <i class="bi bi-table"></i> Recent Treasury Data
                            </h5>
                        </div>
                        <div class="card-body p-0">
                            <div class="table-responsive">
                                <table class="table table-sm table-hover mb-0">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>CUSIP</th>
                                            <th class="d-none d-md-table-cell">Security</th>
                                            <th>Price</th>
                                            <th>Change</th>
                                            <th class="d-none d-sm-table-cell">Yield</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><small>912828XG8</small></td>
                                            <td class="d-none d-md-table-cell">10Y Note</td>
                                            <td>99.875</td>
                                            <td class="text-success">+0.125</td>
                                            <td class="d-none d-sm-table-cell">4.25%</td>
                                        </tr>
                                        <tr>
                                            <td><small>912828YK0</small></td>
                                            <td class="d-none d-md-table-cell">2Y Note</td>
                                            <td>101.250</td>
                                            <td class="text-danger">-0.050</td>
                                            <td class="d-none d-sm-table-cell">4.75%</td>
                                        </tr>
                                        <tr>
                                            <td><small>912810RZ3</small></td>
                                            <td class="d-none d-md-table-cell">30Y Bond</td>
                                            <td>98.500</td>
                                            <td class="text-success">+0.075</td>
                                            <td class="d-none d-sm-table-cell">4.50%</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="row mt-4">
                <div class="col-12">
                    <div class="text-center text-muted">
                        <small>
                            <i class="bi bi-shield-check"></i> Secure • 
                            <i class="bi bi-clock"></i> Real-time • 
                            <i class="bi bi-phone"></i> Mobile Optimized
                            <br>
                            Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC
                        </small>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

@app.get("/visualizations", response_class=HTMLResponse)
async def mobile_visualizations():
    """Mobile-optimized visualizations page"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Finance Tracker - Mobile Charts</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .chart-container { background: white; border-radius: 15px; margin: 10px; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            .chart-iframe { width: 100%; height: 350px; border: none; border-radius: 10px; }
            @media (min-width: 768px) { .chart-iframe { height: 450px; } }
            .back-btn { position: fixed; top: 15px; left: 15px; z-index: 1000; }
        </style>
    </head>
    <body>
        <a href="/" class="btn btn-primary back-btn">
            <i class="bi bi-arrow-left"></i> Back
        </a>
        
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <h1 class="text-center text-white mt-4 mb-4">
                        <i class="bi bi-bar-chart-line"></i> Interactive Charts
                    </h1>
                </div>
            </div>
            
            <!-- Charts optimized for mobile -->
            <div class="chart-container">
                <h3><i class="bi bi-graph-up"></i> Treasury Analysis</h3>
                <iframe src="/static/treasury_prices.html" class="chart-iframe"></iframe>
            </div>
            
            <div class="chart-container">
                <h3><i class="bi bi-bar-chart"></i> Repo Spreads Dashboard</h3>
                <iframe src="/static/repo_spreads_dashboard.html" class="chart-iframe"></iframe>
            </div>
            
            <div class="chart-container">
                <h3><i class="bi bi-thermometer-half"></i> Volatility Heatmap</h3>
                <iframe src="/static/volatility_heatmap.html" class="chart-iframe"></iframe>
            </div>
            
            <div class="chart-container">
                <h3><i class="bi bi-diagram-2"></i> Correlation Matrix</h3>
                <iframe src="/static/correlation_matrix.html" class="chart-iframe"></iframe>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/monitoring", response_class=HTMLResponse)
async def mobile_monitoring():
    """Mobile-optimized monitoring page"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Finance Tracker - Mobile Monitoring</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .monitor-card { background: white; border-radius: 15px; margin: 10px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            .status-indicator { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
            .status-online { background: #28a745; }
            .status-warning { background: #ffc107; }
            .status-offline { background: #dc3545; }
            .back-btn { position: fixed; top: 15px; left: 15px; z-index: 1000; }
        </style>
    </head>
    <body>
        <a href="/" class="btn btn-primary back-btn">
            <i class="bi bi-arrow-left"></i> Back
        </a>
        
        <div class="container-fluid">
            <div class="row">
                <div class="col-12">
                    <h1 class="text-center text-white mt-4 mb-4">
                        <i class="bi bi-activity"></i> System Monitoring
                    </h1>
                </div>
            </div>
            
            <div class="monitor-card">
                <h3><i class="bi bi-server"></i> System Status</h3>
                <div class="row g-3">
                    <div class="col-6 col-md-3">
                        <div class="text-center">
                            <span class="status-indicator status-online"></span>
                            <div><strong>API Server</strong></div>
                            <small class="text-success">Online</small>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center">
                            <span class="status-indicator status-online"></span>
                            <div><strong>Database</strong></div>
                            <small class="text-success">Connected</small>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center">
                            <span class="status-indicator status-warning"></span>
                            <div><strong>Data Feed</strong></div>
                            <small class="text-warning">Delayed</small>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center">
                            <span class="status-indicator status-online"></span>
                            <div><strong>Charts</strong></div>
                            <small class="text-success">Active</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="monitor-card">
                <h3><i class="bi bi-bell"></i> Recent Alerts</h3>
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i> 
                    <strong>Data Delay:</strong> Treasury feed delayed by 5 minutes
                    <small class="d-block">2 minutes ago</small>
                </div>
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i>
                    <strong>System Update:</strong> Charts refreshed successfully
                    <small class="d-block">15 minutes ago</small>
                </div>
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i>
                    <strong>Connection Restored:</strong> All systems operational
                    <small class="d-block">1 hour ago</small>
                </div>
            </div>
            
            <div class="monitor-card">
                <h3><i class="bi bi-graph-up"></i> Performance Metrics</h3>
                <div class="row g-3">
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h4 text-primary">99.8%</div>
                            <small>Uptime</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h4 text-success">1.2s</div>
                            <small>Avg Response</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h4 text-info">245</div>
                            <small>Active Users</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h4 text-warning">15.2GB</div>
                            <small>Data Processed</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# API endpoints (same as demo.py)
@app.get("/api/treasury")
async def api_treasury():
    """Treasury data API endpoint"""
    return {"data": get_treasury_data(), "status": "success", "timestamp": datetime.now().isoformat()}

@app.get("/api/repo")
async def api_repo():
    """Repo data API endpoint"""
    return {"data": get_repo_data(), "status": "success", "timestamp": datetime.now().isoformat()}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "mobile_optimized": True,
        "features": ["responsive_design", "touch_friendly", "offline_ready"]
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Mobile-Responsive Finance Tracker...")
    print("📱 Optimized for mobile, tablet, and desktop")
    print("🌐 Access at: http://localhost:8001")
    uvicorn.run("mobile_demo:app", host="0.0.0.0", port=8001, reload=True)
