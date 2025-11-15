#!/usr/bin/env python3
"""
LeadFactory Control Center Launcher

This is a convenience wrapper for launch.py that starts the complete LeadFactory system:
- Agentic pipeline (main.py)
- Visual dashboard (dashboard.py)
- Auto-opens browser

Usage:
    python start_leadfactory.py

The system will start and automatically open your browser to http://127.0.0.1:5000
Press Ctrl+C to stop all services gracefully.
"""

if __name__ == "__main__":
    # Import and run the main launcher
    from launch import main

    print("=" * 60)
    print("LeadFactory - Visual Control Center")
    print("=" * 60)
    print()
    print("Starting complete system...")
    print("  - Agentic pipeline (main.py)")
    print("  - Visual dashboard (dashboard.py)")
    print("  - Browser auto-launch")
    print()

    main()
