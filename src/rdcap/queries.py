"""Search and comparison functions used by the user interface (and tested)."""
from __future__ import annotations

import sqlite3

import pandas as pd

from rdcap import config


def connect(db_path=None) -> sqlite3.Connection:
    return sqlite3.connect(db_path or config.DB_PATH)


def list_values(conn, column: str) -> list:
    allowed = {"plasticizer", "study_id", "operator"}
    if column not in allowed:
        raise ValueError(column)
    rows = conn.execute(f"SELECT DISTINCT {column} FROM v_trial_summary WHERE {column} IS NOT NULL ORDER BY 1")
    return [r[0] for r in rows]


def search_trials(conn, plasticizers=None, study_ids=None, phr_min=None, phr_max=None,
                  visco_max=None, year_min=None, year_max=None) -> pd.DataFrame:
    """Multi-criteria search. All filters are optional; parameters are bound (no SQL injection)."""
    sql = "SELECT * FROM v_trial_summary WHERE 1 = 1"
    params: list = []
    if plasticizers:
        sql += f" AND plasticizer IN ({','.join('?' * len(plasticizers))})"
        params += list(plasticizers)
    if study_ids:
        sql += f" AND study_id IN ({','.join('?' * len(study_ids))})"
        params += list(study_ids)
    if phr_min is not None:
        sql += " AND plasticizer_phr >= ?"
        params.append(phr_min)
    if phr_max is not None:
        sql += " AND plasticizer_phr <= ?"
        params.append(phr_max)
    if visco_max is not None:
        sql += " AND viscosite_1h <= ?"
        params.append(visco_max)
    if year_min is not None:
        sql += " AND CAST(substr(trial_date, 1, 4) AS INTEGER) >= ?"
        params.append(year_min)
    if year_max is not None:
        sql += " AND CAST(substr(trial_date, 1, 4) AS INTEGER) <= ?"
        params.append(year_max)
    return pd.read_sql_query(sql + " ORDER BY trial_id", conn, params=params)


def trial_details(conn, trial_id: str) -> dict:
    """Everything about one trial, with the traceability to the source cells."""
    return {
        "summary": pd.read_sql_query("SELECT * FROM v_trial_summary WHERE trial_id = ?", conn, params=[trial_id]),
        "formulation": pd.read_sql_query(
            "SELECT component_raw, component_id, quantity_phr, source_cell FROM formulation_line WHERE trial_id = ?",
            conn, params=[trial_id]),
        "measurements": pd.read_sql_query(
            "SELECT property, value, unit, value_raw, unit_raw, source_cell FROM measurement WHERE trial_id = ?",
            conn, params=[trial_id]),
    }


def compare_trials(conn, trial_ids: list[str]) -> pd.DataFrame:
    """Side-by-side comparison: one column per trial."""
    if not trial_ids:
        return pd.DataFrame()
    df = pd.read_sql_query(
        f"SELECT * FROM v_trial_summary WHERE trial_id IN ({','.join('?' * len(trial_ids))})",
        conn, params=list(trial_ids))
    return df.set_index("trial_id").T


def issues(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM issue ORDER BY severity, category", conn)
