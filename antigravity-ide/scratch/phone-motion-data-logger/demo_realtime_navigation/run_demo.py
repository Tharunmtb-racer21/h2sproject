"""
SIH26168 Intelligent Dead Reckoning System
One-Click Launch Script for Real-Time Navigation Prototype

Usage:
    python demo_realtime_navigation/run_demo.py [--port 8080]
"""

import sys
import os
import time
import webbrowser
import argparse

# Ensure current package is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_realtime_navigation.backend.app import run_server


def main():
    parser = argparse.ArgumentParser(description="SIH26168 Real-Time Navigation Prototype Launcher")
    parser.add_argument("--port", type=int, default=8080, help="Port to host the dashboard (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open default web browser")
    args = parser.parse_args()

    url = f"http://localhost:{args.port}"
    print("=" * 70)
    print(" [SIH26168] AI-ML BASED INTELLIGENT DEAD RECKONING SYSTEM")
    print(" Real-Time Navigation Dashboard (Research Prototype)")
    print("=" * 70)
    print(f" Dashboard URL: {url}")
    print(" Mode: REPLAY & SIMULATION (Live Sensor Integration Next Phase)")
    print("=" * 70)

    if not args.no_browser:
        def open_browser():
            time.sleep(1.0)
            print(f" Opening {url} in your default browser...")
            webbrowser.open(url)

        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    run_server(port=args.port)


if __name__ == "__main__":
    main()
