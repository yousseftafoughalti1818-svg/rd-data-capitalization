"""Step 5 - Data quality controls, run on the database after loading.

Each anomaly is stored in the `issue` table with a pointer to its source
(file and cell), and exported to reports/quality_report.md.
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from rdcap import config

CHECKS = [
    ("Valeur manquante", "haute",
     """SELECT 'mesure ' || m.property || ' vide pour ' || m.trial_id, sf.path || ' [' || m.source_cell || ']'
        FROM measurement m JOIN trial t USING(trial_id) JOIN source_file sf ON sf.file_id = t.file_id
        WHERE m.value IS NULL AND m.property IS NOT NULL"""),
    ("Résine différente de 100 phr", "moyenne",
     """SELECT f.trial_id || ' : résine à ' || f.quantity_phr || ' phr', sf.path || ' [' || f.source_cell || ']'
        FROM formulation_line f JOIN trial t USING(trial_id) JOIN source_file sf ON sf.file_id = t.file_id
        WHERE f.component_id = 'PVC_PATE' AND f.quantity_phr <> 100"""),
    ("Essai sans formulation", "haute",
     """SELECT t.trial_id || ' n''a aucune ligne de formulation', sf.path
        FROM trial t JOIN source_file sf ON sf.file_id = t.file_id
        WHERE NOT EXISTS (SELECT 1 FROM formulation_line f WHERE f.trial_id = t.trial_id)"""),
    ("Essai sans étude", "moyenne",
     """SELECT t.trial_id || ' rattaché à aucune étude connue', sf.path
        FROM trial t JOIN source_file sf ON sf.file_id = t.file_id
        WHERE t.study_id IS NULL OR t.study_id NOT IN (SELECT study_id FROM study)"""),
]


def run_quality_checks(db_path=None) -> pd.DataFrame:
    db_path = db_path or config.DB_PATH
    conn = sqlite3.connect(db_path)
    for category, severity, sql in CHECKS:
        for detail, source in conn.execute(sql).fetchall():
            conn.execute("INSERT INTO issue VALUES (?, ?, ?, ?)", (category, severity, detail, source))

    # value ranges (outliers, often unit mistakes)
    ranges = pd.read_csv(config.REFERENCE_DIR / "ranges.csv")
    for r in ranges.itertuples():
        if r.property == "gel_temperature_c":
            sql = """SELECT study_id, gel_temperature_c, sf.path FROM study s
                     JOIN source_file sf ON sf.file_id = s.file_id
                     WHERE gel_temperature_c NOT BETWEEN ? AND ?"""
            for sid, val, src in conn.execute(sql, (r.min, r.max)):
                conn.execute("INSERT INTO issue VALUES ('Valeur hors plage', 'haute', ?, ?)",
                             (f"{sid} : température de gélification {val} °C (attendu {r.min}-{r.max})", src))
        else:
            sql = """SELECT m.trial_id, m.value, sf.path || ' [' || m.source_cell || ']'
                     FROM measurement m JOIN trial t USING(trial_id) JOIN source_file sf ON sf.file_id = t.file_id
                     WHERE m.property = ? AND m.value IS NOT NULL AND m.value NOT BETWEEN ? AND ?"""
            for tid, val, src in conn.execute(sql, (r.property, r.min, r.max)):
                conn.execute("INSERT INTO issue VALUES ('Valeur hors plage', 'haute', ?, ?)",
                             (f"{tid} : {r.property} = {val:g} {r.unit} (attendu {r.min}-{r.max})", src))

    conn.commit()
    issues = pd.read_sql_query("SELECT * FROM issue ORDER BY severity, category", conn)
    conn.close()
    return issues


def write_report(issues: pd.DataFrame, counts: dict, inventory: pd.DataFrame) -> None:
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    issues.to_csv(config.REPORTS_DIR / "quality_issues.csv", index=False)
    inventory.to_csv(config.REPORTS_DIR / "inventory.csv", index=False)
    lines = [
        "# Rapport de capitalisation des données R&D", "",
        "## Inventaire des sources", "",
        f"- Fichiers trouvés : **{len(inventory)}**",
    ]
    for template, n in inventory["template"].value_counts().items():
        lines.append(f"  - {template} : {n}")
    lines += ["", "## Chargement", "",
              f"- Études chargées : **{counts['studies']}**",
              f"- Essais chargés : **{counts['trials']}**",
              f"- Fichiers en double écartés : **{counts['duplicates']}**",
              f"- Fichiers non reconnus : **{counts['not_recognised']}**", "",
              "## Anomalies détectées", "",
              f"**{len(issues)} anomalies**, chacune avec sa source (fichier et cellule).", "",
              "| Catégorie | Gravité | Détail | Source |", "|---|---|---|---|"]
    for r in issues.itertuples():
        lines.append(f"| {r.category} | {r.severity} | {r.detail} | `{r.source}` |")
    (config.REPORTS_DIR / "quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
