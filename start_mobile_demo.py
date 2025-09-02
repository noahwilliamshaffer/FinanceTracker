#!/usr/bin/env python3
"""
Mobile Finance Tracker Demo Launcher
Starts the mobile-responsive version of the Finance Tracker
"""

import uvicorn
import sys
import os

def main():
    print("=" * 60)
    print("🚀 FINANCE TRACKER - MOBILE DEMO STARTING...")
    print("=" * 60)
    print("📱 Mobile-First Responsive Design")
    print("🎯 Touch-Friendly Interface")
    print("⚡ PWA-Ready Experience")
    print("🌐 Cross-Platform Compatible")
    print("=" * 60)
    print("📊 Dashboard:    http://localhost:8001")
    print("📈 Charts:       http://localhost:8001/visualizations")
    print("⚠️  Monitoring:   http://localhost:8001/monitoring")
    print("🔗 API Docs:     http://localhost:8001/docs")
    print("❤️  Health:      http://localhost:8001/health")
    print("=" * 60)
    print("✅ Starting mobile-optimized server...")
    print("📱 Optimized for phones, tablets, and desktops")
    print("🔄 Pull-to-refresh enabled")
    print("👆 Touch gestures supported")
    print("=" * 60)
    
    try:
        # Start the mobile demo server
        uvicorn.run(
            "mobile_demo:app",
            host="0.0.0.0",
            port=8001,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Mobile Finance Tracker stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting mobile demo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
