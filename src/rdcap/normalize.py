"""Step 3 - Normalization of names, numbers, dates and units."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

import pandas as pd

from rdcap import config

# conversion factors towards the reference unit of each property
UNIT_CONVERSIONS = {
    ("pa.s", "mPa.s"): 1000.0,
    ("pa·s", "mPa.s"): 1000.0,
    ("mpa.s", "mPa.s"): 1.0,
    ("cp", "mPa.s"): 1.0,            # 1 centipoise = 1 mPa.s
    ("s", "min"): 1 / 60,
    ("min", "min"): 1.0,
    ("shore a", "ShoreA"): 1.0,
    ("shorea", "ShoreA"): 1.0,
}
MISSING_TOKENS = {"", "n.d.", "nd", "na", "n/a", "-", "?"}


def clean_text(text) -> str:
    """Lower case, no accents, single spaces: 'Résine  PVC Pâte ' -> 'resine pvc pate'."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text).strip().lower()


def to_number(value) -> float | None:
    """'1,5' -> 1.5 ; 'n.d.' -> None ; 60 -> 60.0"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if text in MISSING_TOKENS:
        return None
    try:
        return float(text.replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def to_iso_date(value) -> str | None:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def load_mapping(filename: str) -> pd.DataFrame:
    df = pd.read_csv(config.REFERENCE_DIR / filename)
    df["key"] = df["alias"].map(clean_text)
    # several aliases can become identical after cleaning (accents, case): keep one
    return df.drop_duplicates("key").set_index("key")


class Normalizer:
    def __init__(self):
        self.components = load_mapping("nomenclature.csv")
        self.properties = load_mapping("properties.csv")

    def component(self, raw) -> tuple[str | None, str | None]:
        key = clean_text(raw)
        if key in self.components.index:
            row = self.components.loc[key]
            return row["canonical_name"], row["component_type"]
        return None, None

    def measurement(self, prop_raw, value_raw, unit_raw) -> dict:
        key = clean_text(prop_raw)
        prop, target_unit = None, None
        if key in self.properties.index:
            prop, target_unit = self.properties.loc[key, ["property", "unit"]]
        value = to_number(value_raw)
        unit_key = clean_text(unit_raw) if unit_raw else clean_text(target_unit or "")
        factor = UNIT_CONVERSIONS.get((unit_key, target_unit)) if target_unit else None
        converted = value * factor if (value is not None and factor is not None) else None
        return {"property": prop, "value": converted, "unit": target_unit,
                "value_raw": None if value_raw is None else str(value_raw),
                "unit_raw": unit_raw, "unit_known": factor is not None}
