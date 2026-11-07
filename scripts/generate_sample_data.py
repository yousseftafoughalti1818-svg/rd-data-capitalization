"""Generate a FICTIVE R&D archive (Word + Excel files) that mimics real-life messiness.

All studies, trials, people and values are invented for demonstration purposes.
Two Excel templates are used (a recent one and an older one), with inconsistent
component names, mixed units, missing values, a duplicated file, an outlier and
a file that follows no template.

Usage:
    python scripts/generate_sample_data.py
"""
import random
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

from docx import Document
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rdcap import config  # noqa: E402

random.seed(7)
OPERATORS = ["A. Martin", "C. Dubois", "L. Bernard", "S. Petit"]
PLASTICIZERS = {  # canonical -> ways people write it
    "DINP": ["DINP", "Dinp", "plastifiant DINP", "DINP "],
    "DOTP": ["DOTP", "plastifiant DOTP", "dotp"],
    "DINCH": ["DINCH", "Dinch"],
}
STUDY_TOPICS = [
    ("Influence du taux de plastifiant", "Mesurer l'effet du taux de plastifiant sur la viscosité du plastisol."),
    ("Comparaison de plastifiants", "Comparer plusieurs plastifiants à taux constant."),
    ("Optimisation du stabilisant", "Évaluer l'effet du stabilisant Ca/Zn sur la stabilité thermique."),
    ("Effet de la charge minérale", "Étudier l'ajout de carbonate de calcium sur la dureté."),
]


def simulate_properties(phr_plast, phr_stab, phr_filler):
    visco_1h = 9000 - 70 * phr_plast + 25 * phr_filler + random.gauss(0, 250)
    visco_24h = visco_1h * random.uniform(1.10, 1.35)
    shore_a = 105 - 0.55 * phr_plast + 0.15 * phr_filler + random.gauss(0, 1.5)
    stab_min = 12 + 9 * phr_stab + random.gauss(0, 2)
    return round(visco_1h), round(visco_24h), round(shore_a, 1), round(stab_min, 1)


def write_template_a(path, trial_id, trial_date, operator, formulation, props):
    """Recent template: 2 sheets, header not on the first row."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Formulation"
    ws["A1"] = "Fiche d'essai - Laboratoire d'application (données fictives)"
    ws["A2"], ws["B2"] = "Essai :", trial_id
    ws["A3"], ws["B3"] = "Date :", trial_date.strftime("%d/%m/%Y")
    ws["A4"], ws["B4"] = "Opérateur :", operator
    ws["A6"], ws["B6"] = "Composant", "Quantité (phr)"
    for i, (comp, qty) in enumerate(formulation, start=7):
        ws[f"A{i}"], ws[f"B{i}"] = comp, qty
    res = wb.create_sheet("Résultats")
    res["A1"] = "Résultats des mesures"
    res["A3"], res["B3"], res["C3"] = "Propriété", "Valeur", "Unité"
    rows = [("Viscosité 1h", props[0], "mPa.s"), ("Viscosité 24h", props[1], "mPa.s"),
            ("Dureté Shore A", props[2], "Shore A"), ("Stabilité thermique", props[3], "min")]
    for i, row in enumerate(rows, start=4):
        for col, val in zip("ABC", row):
            res[f"{col}{i}"] = val
    wb.save(path)


def write_template_b(path, trial_id, trial_date, operator, formulation, props):
    """Older template: one sheet, blocks, units written in the header, other units."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Essai"
    ws["A1"], ws["B1"] = "N° essai", trial_id
    ws["A2"], ws["B2"] = "Date", trial_date.strftime("%Y-%m-%d")
    ws["A3"], ws["B3"] = "Technicien", operator
    ws["A5"] = "COMPOSITION"
    ws["A6"], ws["B6"] = "Produit", "phr"
    r = 7
    for comp, qty in formulation:
        ws[f"A{r}"], ws[f"B{r}"] = comp, str(qty).replace(".", ",")   # decimal comma
        r += 1
    r += 1
    ws[f"A{r}"] = "MESURES"
    r += 1
    ws[f"A{r}"], ws[f"B{r}"] = "Mesure", "Résultat"
    r += 1
    rows = [("Visco 1h (Pa.s)", round(props[0] / 1000, 2)), ("Visco 24h (Pa.s)", round(props[1] / 1000, 2)),
            ("Shore A", props[2]), ("Temps de stabilité (s)", round(props[3] * 60))]
    for name, val in rows:
        ws[f"A{r}"], ws[f"B{r}"] = name, val
        r += 1
    wb.save(path)


def write_study_doc(path, study_id, title, objective, author, study_date, temp, minutes, trials):
    doc = Document()
    doc.add_heading(f"Étude {study_id}", level=1)
    doc.add_paragraph("Document fictif généré pour démonstration.")
    doc.add_paragraph(f"Titre : {title}")
    doc.add_paragraph(f"Objectif : {objective}")
    doc.add_paragraph(f"Auteur : {author}")
    doc.add_paragraph(f"Date : {study_date.strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Conditions : gélification à {temp} °C pendant {minutes} min.")
    doc.add_paragraph("Liste des essais :")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "Essai", "Fichier"
    for trial_id, filename in trials:
        cells = table.add_row().cells
        cells[0].text, cells[1].text = trial_id, filename
    doc.save(path)


def generate(raw_dir: Path | None = None, seed: int = 7) -> Path:
    random.seed(seed)
    raw_dir = Path(raw_dir) if raw_dir else config.RAW_DIR
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    raw_dir.mkdir(parents=True)

    trial_counter = 0
    for year in (2021, 2022, 2023, 2024):
        template = write_template_b if year <= 2022 else write_template_a
        for s in range(1, 4):
            study_id = f"ETU-{year}-{s:02d}"
            title, objective = STUDY_TOPICS[(year + s) % len(STUDY_TOPICS)]
            study_dir = raw_dir / str(year) / f"{study_id} {title}"
            study_dir.mkdir(parents=True)
            study_date = date(year, random.randint(1, 10), random.randint(1, 28))
            plast = random.choice(list(PLASTICIZERS))
            trials = []
            for t in range(random.randint(3, 5)):
                trial_counter += 1
                trial_id = f"ESS-{year}-{trial_counter:03d}"
                phr_plast = random.choice([40, 50, 60, 70, 80])
                phr_stab = random.choice([1, 2, 3, 4])
                phr_filler = random.choice([0, 10, 20, 30])
                formulation = [
                    (random.choice(["Résine PVC pâte", "PVC pâte", "resine PVC pate"]), 100),
                    (random.choice(PLASTICIZERS[plast]), phr_plast),
                    (random.choice(["Stabilisant Ca/Zn", "stab Ca/Zn"]), phr_stab),
                ]
                if phr_filler:
                    formulation.append((random.choice(["CaCO3", "Carbonate de calcium"]), phr_filler))
                props = list(simulate_properties(phr_plast, phr_stab, phr_filler))
                filename = f"{trial_id}.xlsx"
                template(study_dir / filename, trial_id,
                         study_date + timedelta(days=7 * t), random.choice(OPERATORS), formulation, props)
                trials.append((trial_id, filename))
            temp = random.choice([170, 180, 190])
            write_study_doc(study_dir / f"{study_id}_rapport.docx", study_id, title, objective,
                            random.choice(OPERATORS), study_date, temp, random.choice([2, 3, 4]), trials)

    # ---- realistic anomalies -------------------------------------------------
    files = sorted(raw_dir.rglob("ESS-*.xlsx"))
    # 1. duplicated file ("copie")
    shutil.copy(files[3], files[3].with_name(files[3].stem + " - copie.xlsx"))
    # 2. missing value + 3. outlier (unit mistake) in a recent-template file
    from openpyxl import load_workbook
    recent = [f for f in files if "-2024-" in f.name or "-2023-" in f.name]
    wb = load_workbook(recent[0]); wb["Résultats"]["B5"] = None; wb.save(recent[0])
    wb = load_workbook(recent[1]); wb["Résultats"]["B4"] = 4.6; wb.save(recent[1])   # Pa.s typed in mPa.s
    # 4. unknown component (typo not in the nomenclature)
    wb = load_workbook(recent[2]); wb["Formulation"]["A8"] = "plastifant DINP"; wb.save(recent[2])
    # 5. a typo in a Word report (1800 °C instead of 180 °C)
    doc_path = sorted(raw_dir.rglob("*_rapport.docx"))[5]
    doc = Document(doc_path)
    for p in doc.paragraphs:
        if p.text.startswith("Conditions"):
            p.text = "Conditions : gélification à 1800 °C pendant 3 min."
    doc.save(doc_path)
    # 6. a file that follows no template
    misc = Workbook(); misc.active["A1"] = "Notes diverses, à trier"; misc.save(raw_dir / "2023" / "notes_diverses.xlsx")
    print(f"Fictive archive generated in {raw_dir}")
    return raw_dir


if __name__ == "__main__":
    generate()
