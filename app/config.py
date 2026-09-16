"""Application configuration settings."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_FILE_PATH = DATA_DIR / "support_tickets.csv"
DB_FILE_PATH = DATA_DIR / "tickets.db"

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
PREFERRED_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()

# Server Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
UI_PORT = int(os.getenv("UI_PORT", "8501"))

# Anomaly Thresholds
SLA_CRITICAL_HOURS = float(os.getenv("SLA_CRITICAL_HOURS", "12.0"))
SLA_HIGH_HOURS = float(os.getenv("SLA_HIGH_HOURS", "24.0"))
SLA_MEDIUM_HOURS = float(os.getenv("SLA_MEDIUM_HOURS", "48.0"))
MAX_RESPONSE_TIME_THRESHOLD = float(os.getenv("MAX_RESPONSE_TIME_THRESHOLD", "4.0"))
IQR_MULTIPLIER = float(os.getenv("IQR_MULTIPLIER", "1.5"))
ZSCORE_THRESHOLD = float(os.getenv("ZSCORE_THRESHOLD", "2.5"))
