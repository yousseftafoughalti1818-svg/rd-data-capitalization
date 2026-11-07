import sqlite3

from rdcap import queries as q


def test_counts(processed):
    r = processed["result"]
    assert r["studies"] == 12
    assert r["duplicates"] == 1
    assert r["not_recognised"] == 1
    assert r["trials"] == 48


def test_every_injected_anomaly_is_detected(processed):
    conn = sqlite3.connect(processed["db"])
    categories = {row[0] for row in conn.execute("SELECT category FROM issue")}
    assert {"Composant inconnu", "Valeur hors plage", "Valeur manquante",
            "Essai en double", "Fichier non reconnu"} <= categories


def test_duplicate_keeps_the_original_file(processed):
    conn = sqlite3.connect(processed["db"])
    src = conn.execute("SELECT source FROM issue WHERE category = 'Essai en double'").fetchone()[0]
    assert "copie" in src


def test_old_units_are_converted(processed):
    conn = sqlite3.connect(processed["db"])
    visco = conn.execute("""SELECT value FROM measurement
                            WHERE trial_id = 'ESS-2021-001' AND property = 'viscosite_1h'""").fetchone()[0]
    assert visco > 500   # Pa.s converted into mPa.s


def test_traceability(processed):
    conn = sqlite3.connect(processed["db"])
    missing = conn.execute("SELECT COUNT(*) FROM measurement WHERE source_cell IS NULL").fetchone()[0]
    assert missing == 0


def test_search_and_compare(processed):
    conn = sqlite3.connect(processed["db"])
    res = q.search_trials(conn, plasticizers=["DINP"], phr_min=60)
    assert len(res) > 0
    assert (res["plasticizer"] == "DINP").all() and (res["plasticizer_phr"] >= 60).all()
    cmp = q.compare_trials(conn, res["trial_id"].head(2).tolist())
    assert cmp.shape[1] == 2
    assert "viscosite_1h" in cmp.index


def test_report_is_written(processed):
    report = (processed["reports"] / "quality_report.md").read_text(encoding="utf-8")
    assert "Anomalies détectées" in report
