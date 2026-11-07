"""Step 1 - Map the sources: list every file and detect which template it follows."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from docx import Document
from openpyxl import load_workbook

TEMPLATE_RECENT = "excel_recent"      # sheets "Formulation" + "Résultats"
TEMPLATE_OLD = "excel_ancien"         # one sheet "Essai", blocks COMPOSITION / MESURES
TEMPLATE_STUDY = "word_etude"         # study report, heading "Étude ..."
UNKNOWN = "inconnu"


def detect_template(path: Path) -> str:
    """Recognise a template from its structure (sheet names, key cells, heading)."""
    try:
        if path.suffix.lower() == ".xlsx":
            wb = load_workbook(path, read_only=True)
            sheets = set(wb.sheetnames)
            if {"Formulation", "Résultats"} <= sheets:
                return TEMPLATE_RECENT
            if "Essai" in sheets and wb["Essai"]["A1"].value == "N° essai":
                return TEMPLATE_OLD
        elif path.suffix.lower() == ".docx":
            paragraphs = [p.text for p in Document(path).paragraphs if p.text.strip()]
            if paragraphs and paragraphs[0].startswith("Étude"):
                return TEMPLATE_STUDY
    except Exception:   # corrupted or unreadable file: reported, never silently ignored
        return UNKNOWN
    return UNKNOWN


def build_inventory(raw_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(Path(raw_dir).rglob("*")):
        if not path.is_file():
            continue
        rows.append({
            "file": str(path.relative_to(raw_dir)),
            "extension": path.suffix.lower(),
            "size_kb": round(path.stat().st_size / 1024, 1),
            "modified": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d"),
            "template": detect_template(path),
        })
    return pd.DataFrame(rows)
