"""Project paths."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT_DIR / "data" / "raw"
DB_PATH = ROOT_DIR / "data" / "rd_database.db"
REFERENCE_DIR = ROOT_DIR / "reference"
REPORTS_DIR = ROOT_DIR / "reports"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
