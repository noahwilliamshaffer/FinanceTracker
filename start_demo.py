"""
Finance Tracker - Simple Startup Script
"""

from demo import app
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 FINANCE TRACKER - STARTING...")
    print("=" * 60)
    print("📊 Dashboard:    http://localhost:8000")
    print("🔗 API Docs:     http://localhost:8000/docs")
    print("❤️  Health:      http://localhost:8000/health")
    print("=" * 60)
    print("✅ Starting server... Press Ctrl+C to stop")
    print("=" * 60)
    
    # Start without reload to avoid the warning
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
