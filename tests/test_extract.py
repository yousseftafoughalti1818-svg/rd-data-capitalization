from rdcap.extract import extract_excel, extract_study
from rdcap.inventory import TEMPLATE_OLD, TEMPLATE_RECENT, UNKNOWN, build_inventory


def test_inventory_detects_every_template(archive):
    inv = build_inventory(archive["raw"])
    counts = inv["template"].value_counts()
    assert counts["word_etude"] == 12
    assert counts[UNKNOWN] == 1
    assert counts[TEMPLATE_OLD] > 0 and counts[TEMPLATE_RECENT] > 0


def test_recent_template_extraction(archive):
    path = sorted(archive["raw"].rglob("ESS-2024-*.xlsx"))[0]
    t = extract_excel(path, TEMPLATE_RECENT, path.name)
    assert t["trial_id"].startswith("ESS-2024")
    assert t["study_id"].startswith("ETU-2024")
    assert len(t["formulation"]) >= 3
    assert {m["property_raw"] for m in t["measurements"]} >= {"Viscosité 1h", "Dureté Shore A"}
    assert all(m["source_cell"].startswith("Résultats!") for m in t["measurements"])


def test_old_template_reads_unit_from_label(archive):
    path = sorted(archive["raw"].rglob("ESS-2021-*.xlsx"))[0]
    t = extract_excel(path, TEMPLATE_OLD, path.name)
    units = {m["property_raw"]: m["unit_raw"] for m in t["measurements"]}
    assert units["Visco 1h"] == "Pa.s"
    assert units["Temps de stabilité"] == "s"


def test_word_report_extraction(archive):
    path = sorted(archive["raw"].rglob("*_rapport.docx"))[0]
    s = extract_study(path, path.name)
    assert s["study_id"].startswith("ETU-")
    assert s["title"] and s["objective"]
    assert s["gel_temperature_c"] in (170, 180, 190, 1800)
    assert len(s["listed_trials"]) >= 3
