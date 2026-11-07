"""Step 2 - Automated extraction from Word and Excel files.

Every extracted value keeps a pointer to its origin (file, sheet, cell) so that
any number in the database can be traced back to the source document.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from openpyxl import load_workbook

from rdcap.inventory import TEMPLATE_OLD, TEMPLATE_RECENT

STUDY_ID_RE = re.compile(r"ETU-\d{4}-\d{2}")
TEMP_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*°C")
DURATION_RE = re.compile(r"pendant\s+(\d+(?:[.,]\d+)?)\s*min")
UNIT_IN_HEADER_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")   # "Visco 1h (Pa.s)" -> ("Visco 1h", "Pa.s")


def _study_id_from_path(path: Path) -> str | None:
    match = STUDY_ID_RE.search(str(path))
    return match.group(0) if match else None


def _find_row(ws, text: str, column: str = "A") -> int | None:
    """Find the row whose cell in `column` equals `text` (header detection)."""
    for row in range(1, ws.max_row + 1):
        value = ws[f"{column}{row}"].value
        if isinstance(value, str) and value.strip().lower() == text.lower():
            return row
    return None


def extract_excel(path: Path, template: str, rel_path: str) -> dict:
    wb = load_workbook(path, data_only=True)
    trial = {"study_id": _study_id_from_path(path), "source_file": rel_path}
    formulation, measurements = [], []

    if template == TEMPLATE_RECENT:
        ws = wb["Formulation"]
        trial.update(trial_id=ws["B2"].value, date_raw=ws["B3"].value, operator=ws["B4"].value)
        header = _find_row(ws, "Composant")
        for row in range(header + 1, ws.max_row + 1):
            name, qty = ws[f"A{row}"].value, ws[f"B{row}"].value
            if name:
                formulation.append({"component_raw": name, "quantity_raw": qty,
                                    "source_cell": f"Formulation!B{row}"})
        res = wb["Résultats"]
        header = _find_row(res, "Propriété")
        for row in range(header + 1, res.max_row + 1):
            name = res[f"A{row}"].value
            if name:
                measurements.append({"property_raw": name, "value_raw": res[f"B{row}"].value,
                                     "unit_raw": res[f"C{row}"].value, "source_cell": f"Résultats!B{row}"})

    elif template == TEMPLATE_OLD:
        ws = wb["Essai"]
        trial.update(trial_id=ws["B1"].value, date_raw=ws["B2"].value, operator=ws["B3"].value)
        start, end = _find_row(ws, "Produit"), _find_row(ws, "MESURES")
        for row in range(start + 1, end):
            name, qty = ws[f"A{row}"].value, ws[f"B{row}"].value
            if name:
                formulation.append({"component_raw": name, "quantity_raw": qty,
                                    "source_cell": f"Essai!B{row}"})
        header = _find_row(ws, "Mesure")
        for row in range(header + 1, ws.max_row + 1):
            name = ws[f"A{row}"].value
            if not name:
                continue
            match = UNIT_IN_HEADER_RE.match(name)       # units are written in the label
            prop, unit = (match.group(1), match.group(2)) if match else (name, None)
            measurements.append({"property_raw": prop, "value_raw": ws[f"B{row}"].value,
                                 "unit_raw": unit, "source_cell": f"Essai!B{row}"})
    else:
        raise ValueError(f"Unsupported template: {template}")

    trial["formulation"], trial["measurements"] = formulation, measurements
    return trial


def extract_study(path: Path, rel_path: str) -> dict:
    doc = Document(path)
    fields = {}
    for p in doc.paragraphs:
        if ":" in p.text:
            key, _, value = p.text.partition(":")
            fields[key.strip().lower()] = value.strip()
    conditions = fields.get("conditions", "")
    temp, duration = TEMP_RE.search(conditions), DURATION_RE.search(conditions)
    listed_trials = [row.cells[0].text for table in doc.tables for row in table.rows[1:]]
    return {
        "study_id": _study_id_from_path(path),
        "title": fields.get("titre"),
        "objective": fields.get("objectif"),
        "author": fields.get("auteur"),
        "date_raw": fields.get("date"),
        "gel_temperature_c": float(temp.group(1).replace(",", ".")) if temp else None,
        "gel_time_min": float(duration.group(1).replace(",", ".")) if duration else None,
        "listed_trials": listed_trials,
        "source_file": rel_path,
    }
