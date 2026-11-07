"""Step 4 - Load the normalized data into a centralized SQL database (SQLite)."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from rdcap import config
from rdcap.extract import extract_excel, extract_study
from rdcap.inventory import TEMPLATE_OLD, TEMPLATE_RECENT, TEMPLATE_STUDY, UNKNOWN
from rdcap.normalize import Normalizer, to_iso_date, to_number

log = logging.getLogger("rdcap.load")


def create_database(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(config.SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def add_issue(conn, category, severity, detail, source):
    conn.execute("INSERT INTO issue VALUES (?, ?, ?, ?)", (category, severity, detail, source))


def load_all(inventory: pd.DataFrame, raw_dir: Path, db_path: Path) -> dict:
    conn = create_database(db_path)
    norm = Normalizer()
    counts = {"studies": 0, "trials": 0, "duplicates": 0, "not_recognised": 0}

    # studies first (trials reference them); files named "copie" last, so the original wins
    inventory = inventory.assign(_is_copy=inventory["file"].str.contains("copie", case=False))
    ordered = pd.concat([inventory[inventory.template == TEMPLATE_STUDY],
                         inventory[inventory.template != TEMPLATE_STUDY].sort_values(["_is_copy", "file"])])
    listed_in_reports = {}
    for row in ordered.itertuples():
        path = raw_dir / row.file

        if row.template == UNKNOWN:
            conn.execute("INSERT INTO source_file(path, template, status) VALUES (?, ?, 'not_recognised')",
                         (row.file, row.template))
            add_issue(conn, "Fichier non reconnu", "moyenne",
                      "Aucun gabarit connu : à traiter manuellement avec la R&D", row.file)
            counts["not_recognised"] += 1
            continue

        if row.template == TEMPLATE_STUDY:
            s = extract_study(path, row.file)
            cur = conn.execute("INSERT INTO source_file(path, template, status) VALUES (?, ?, 'loaded')",
                               (row.file, row.template))
            conn.execute("INSERT INTO study VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (s["study_id"], s["title"], s["objective"], s["author"], to_iso_date(s["date_raw"]),
                          s["gel_temperature_c"], s["gel_time_min"], cur.lastrowid))
            listed_in_reports[s["study_id"]] = (s["listed_trials"], row.file)
            counts["studies"] += 1
            continue

        if row.template in (TEMPLATE_RECENT, TEMPLATE_OLD):
            t = extract_excel(path, row.template, row.file)
            exists = conn.execute("SELECT 1 FROM trial WHERE trial_id = ?", (t["trial_id"],)).fetchone()
            if exists:   # same trial already loaded from another file
                conn.execute("INSERT INTO source_file(path, template, status) VALUES (?, ?, 'duplicate')",
                             (row.file, row.template))
                add_issue(conn, "Essai en double", "moyenne",
                          f"{t['trial_id']} déjà chargé depuis un autre fichier", row.file)
                counts["duplicates"] += 1
                continue

            cur = conn.execute("INSERT INTO source_file(path, template, status) VALUES (?, ?, 'loaded')",
                               (row.file, row.template))
            conn.execute("INSERT INTO trial VALUES (?, ?, ?, ?, ?)",
                         (t["trial_id"], t["study_id"], to_iso_date(t["date_raw"]), t["operator"], cur.lastrowid))
            counts["trials"] += 1

            for line in t["formulation"]:
                comp_id, comp_type = norm.component(line["component_raw"])
                if comp_id:
                    conn.execute("INSERT OR IGNORE INTO component VALUES (?, ?)", (comp_id, comp_type))
                else:
                    add_issue(conn, "Composant inconnu", "haute",
                              f"'{line['component_raw']}' absent de la nomenclature",
                              f"{row.file} [{line['source_cell']}]")
                conn.execute("INSERT INTO formulation_line VALUES (?, ?, ?, ?, ?)",
                             (t["trial_id"], comp_id, line["component_raw"],
                              to_number(line["quantity_raw"]), line["source_cell"]))

            for m in t["measurements"]:
                res = norm.measurement(m["property_raw"], m["value_raw"], m["unit_raw"])
                if res["property"] is None:
                    add_issue(conn, "Propriété inconnue", "haute",
                              f"'{m['property_raw']}' absente du référentiel", f"{row.file} [{m['source_cell']}]")
                elif not res["unit_known"]:
                    add_issue(conn, "Unité inconnue", "haute",
                              f"unité '{m['unit_raw']}' non convertible", f"{row.file} [{m['source_cell']}]")
                conn.execute("INSERT INTO measurement VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (t["trial_id"], res["property"], res["value"], res["unit"],
                              res["value_raw"], res["unit_raw"], m["source_cell"]))

    # consistency between Word reports and Excel files
    loaded = {r[0] for r in conn.execute("SELECT trial_id FROM trial")}
    for study_id, (listed, report_file) in listed_in_reports.items():
        for trial_id in listed:
            if trial_id not in loaded:
                add_issue(conn, "Essai cité sans fichier", "moyenne",
                          f"{trial_id} cité dans le rapport de {study_id} mais aucun fichier trouvé", report_file)

    conn.commit()
    conn.close()
    log.info("Loaded %s", counts)
    return counts
