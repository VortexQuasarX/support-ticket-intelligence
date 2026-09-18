"""Unified Single-Command Launcher for Support Ticket Intelligence System."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure UTF-8 console output across all operating systems and Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.config import API_HOST, API_PORT, UI_PORT
from app.database.db_manager import db_manager
from app.ingestion.pipeline import ingestion_pipeline


def prepare_environment():
    """Ensure database is seeded prior to booting services."""
    print("=" * 60)
    print("🚀 Initializing Support Ticket Intelligence System...")
    db_manager.init_database()
    count = db_manager.get_ticket_count()
    if count == 0:
        print("📦 Ingesting support_tickets.csv into SQLite database...")
        summary = ingestion_pipeline.run()
        print(f"✅ Ingested {summary['records_inserted']} tickets.")
    else:
        print(f"✅ Database verified with {count} tickets.")
    print("=" * 60)


def run_api():
    """Launch FastAPI server with Uvicorn."""
    print(f"📡 Starting FastAPI REST API at http://{API_HOST}:{API_PORT} ...")
    print(f"📖 OpenAPI Interactive Swagger Docs: http://localhost:{API_PORT}/docs")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", API_HOST,
        "--port", str(API_PORT)
    ], cwd=str(BASE_DIR))


def run_ui():
    """Launch Streamlit Dashboard."""
    print(f"🎨 Starting Streamlit UI Dashboard at http://localhost:{UI_PORT} ...")
    ui_script = BASE_DIR / "app" / "ui" / "streamlit_app.py"
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(ui_script),
        "--server.port", str(UI_PORT),
        "--server.headless", "true"
    ], cwd=str(BASE_DIR))


def run_both():
    """Launch both FastAPI and Streamlit concurrently."""
    print("✨ Starting both FastAPI backend and Streamlit frontend...")
    print(f"   - REST API & Swagger: http://localhost:{API_PORT}/docs")
    print(f"   - Streamlit Dashboard: http://localhost:{UI_PORT}")
    print("Press Ctrl+C to terminate both services.\n")

    # Start FastAPI as subprocess
    api_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", API_HOST,
        "--port", str(API_PORT)
    ], cwd=str(BASE_DIR))

    # Give API a brief moment to bind port
    time.sleep(1.5)

    # Start Streamlit in main thread
    ui_script = BASE_DIR / "app" / "ui" / "streamlit_app.py"
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(ui_script),
            "--server.port", str(UI_PORT),
            "--server.headless", "true"
        ], cwd=str(BASE_DIR))
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
    finally:
        api_proc.terminate()
        api_proc.wait()
        print("✅ Shutdown complete.")


def main():
    parser = argparse.ArgumentParser(description="Support Ticket Intelligence Launcher")
    parser.add_argument("--api", action="store_true", help="Launch FastAPI REST API only")
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit UI only")
    args = parser.parse_args()

    prepare_environment()

    if args.api:
        run_api()
    elif args.ui:
        run_ui()
    else:
        run_both()


if __name__ == "__main__":
    main()
