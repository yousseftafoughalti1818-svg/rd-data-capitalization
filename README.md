# 🧪 Capitalisation des données R&D – Word & Excel vers une base SQL

![CI](https://github.com/yousseftafoughalti1818-svg/rd-data-capitalization/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![SQL](https://img.shields.io/badge/SQL-SQLite-003B57)
![Streamlit](https://img.shields.io/badge/Streamlit-interface-FF4B4B)

Dans beaucoup de laboratoires R&D, des années de résultats d'essais sont dispersées dans des
centaines de fichiers **Word** (contexte des études) et **Excel** (résultats techniques).
Retrouver un essai ou comparer deux formulations demande alors beaucoup de temps.

Ce projet construit une **chaîne de capitalisation complète et reproductible** :
inventaire des fichiers → **extraction automatique** → **normalisation** (unités, nomenclatures) →
**base de données relationnelle** → **contrôles qualité avec traçabilité** → **interface de recherche**.

> ⚠️ **Toutes les données sont fictives.** Elles sont générées par `scripts/generate_sample_data.py`
> pour imiter une vraie archive (essais de formulation de PVC pâte) avec ses défauts habituels.

---

## 🗂️ L'archive simulée

Le générateur crée **62 fichiers** répartis sur 4 années, avec les problèmes que l'on rencontre
dans une vraie archive :

| Difficulté réelle | Comment elle apparaît dans l'archive |
|---|---|
| Plusieurs **gabarits** de fichiers | un ancien modèle Excel (2021-2022, une seule feuille par blocs) et un nouveau (2023-2024, deux feuilles) |
| En-têtes qui ne sont **pas en ligne 1** | titres et métadonnées au-dessus des tableaux |
| **Unités différentes** | viscosité en Pa·s ou en mPa·s, stabilité en secondes ou en minutes |
| Unités **écrites dans le libellé** | « Visco 1h (Pa.s) » |
| **Noms de composants** variables | « DINP », « Dinp », « plastifiant DINP »… |
| **Virgule décimale** | « 1,5 » au lieu de 1.5 |
| **Doublon** | un fichier « … - copie.xlsx » |
| **Valeur manquante**, **erreur d'unité**, **faute de frappe** | une cellule vide, 4,6 saisi en mPa·s au lieu de Pa·s, 1800 °C au lieu de 180 °C, « plastifant » |
| Fichier **sans gabarit** | `notes_diverses.xlsx` |

## ⚙️ La chaîne de traitement

```
data/raw/ (Word + Excel)
   │
   ├─ 1. inventory.py   → liste tous les fichiers et détecte leur gabarit
   ├─ 2. extract.py     → openpyxl (Excel), python-docx (Word), expressions régulières
   ├─ 3. normalize.py   → noms, nombres, dates, conversion d'unités (référentiels CSV)
   ├─ 4. load.py        → base SQLite, doublons écartés, traçabilité fichier + cellule
   ├─ 5. quality.py     → contrôles qualité + rapport
   └─ app/              → interface Streamlit (recherche, fiche, comparaison, export Excel)
```

**Principe clé : aucune donnée n'est perdue en silence.** Un fichier non reconnu, un composant
inconnu ou une unité non convertible est **enregistré comme anomalie**, avec sa source, pour être
traité avec les équipes métier.

## 🧱 Le modèle de données

```
source_file ──┬── study (titre, objectif, auteur, date, conditions de gélification)
              │      │ 1..n
              └── trial (date, opérateur)
                     │ 1..n                    │ 1..n
              formulation_line            measurement
              (composant, quantité phr,   (propriété, valeur normalisée, unité,
               nom d'origine, cellule)     valeur et unité d'origine, cellule)
                     │
              component (nom normalisé, type)        issue (anomalies)
```

- Chaque valeur garde sa **valeur d'origine** et sa **cellule source** (par exemple `Résultats!B4`) :
  on peut toujours remonter au document.
- Les référentiels `reference/nomenclature.csv`, `properties.csv` et `ranges.csv` sont **modifiables
  par les experts métier** sans toucher au code.
- La vue `v_trial_summary` donne un essai par ligne, avec sa formulation et ses principales mesures.

## ✅ Résultats sur l'archive simulée

| | |
|---|---|
| Fichiers inventoriés | **62** (25 ancien gabarit, 24 nouveau, 12 rapports Word, 1 inconnu) |
| Études chargées | **12** |
| Essais chargés | **48** (178 lignes de formulation, 192 mesures) |
| Doublon écarté | **1** (le fichier « copie », l'original est gardé) |
| Anomalies détectées | **6 sur 6** injectées |

Extrait du rapport généré (`reports/quality_report.md`) :

| Catégorie | Détail | Source |
|---|---|---|
| Composant inconnu | 'plastifant DINP' absent de la nomenclature | `ESS-2023-027.xlsx [Formulation!B8]` |
| Valeur hors plage | viscosite_1h = 4.6 mPa.s (attendu 500-20000) | `ESS-2023-026.xlsx [Résultats!B4]` |
| Valeur hors plage | température de gélification 1800 °C | `ETU-2022-03_rapport.docx` |
| Valeur manquante | viscosite_24h vide pour ESS-2023-025 | `ESS-2023-025.xlsx [Résultats!B5]` |
| Essai en double | ESS-2021-004 déjà chargé | `ESS-2021-004 - copie.xlsx` |
| Fichier non reconnu | aucun gabarit connu | `notes_diverses.xlsx` |

## 🖥️ L'interface (Streamlit)

Pensée pour des **techniciens et ingénieurs non informaticiens** :

1. **Recherche multicritère** : plastifiant, étude, taux de plastifiant, année, viscosité maximale,
   avec un graphique viscosité / taux de plastifiant et un **export Excel**.
2. **Fiche essai** : formulation et mesures, avec la valeur d'origine et la cellule source.
3. **Comparaison** de plusieurs essais côte à côte, exportable.
4. **Qualité des données** : la liste des anomalies à vérifier.

## 🚀 Lancer le projet

```bash
git clone https://github.com/yousseftafoughalti1818-svg/rd-data-capitalization.git
cd rd-data-capitalization
pip install -r requirements-dev.txt
pip install -e .

python scripts/generate_sample_data.py   # crée l'archive fictive dans data/raw/
python -m rdcap.pipeline                 # base data/rd_database.db + reports/
streamlit run app/streamlit_app.py       # interface
pytest -q                                # 16 tests
```

## 🧪 Qualité du code

- **16 tests** pytest : normalisation, détection des gabarits, extraction Word et Excel, chargement,
  détection des anomalies, traçabilité, recherche et comparaison.
- **CI GitHub Actions** : lint (ruff), tests, exécution complète de la chaîne et rapport en artefact.
- Requêtes SQL **paramétrées** (pas d'injection SQL).

## 🔭 Pistes pour un passage en production

- **PostgreSQL** à la place de SQLite (accès multi-utilisateurs, droits) ;
- **traitement incrémental** : ne retraiter que les fichiers nouveaux ou modifiés ;
- **nouveaux gabarits** : un extracteur par gabarit, ajouté au fur et à mesure de la cartographie ;
- **extraction d'information** (NLP / LLM) pour le texte libre des rapports Word ;
- **hébergement et sécurité** avec la DSI (authentification, sauvegardes, maintenance).

## 🛠️ Technologies

Python · pandas · openpyxl · python-docx · expressions régulières · SQL (SQLite) · Streamlit · pytest · GitHub Actions

## 👤 Auteur

**Youssef Tafoughalti** – M2 Ingénierie des Systèmes Complexes (EILCO)
[LinkedIn](https://www.linkedin.com/in/youssef-tafoughalti-b1012a196/) ·
[GitHub](https://github.com/yousseftafoughalti1818-svg)
