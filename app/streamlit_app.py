"""User interface for technicians and engineers.

Run:
    streamlit run app/streamlit_app.py
"""
import io
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rdcap import config, queries as q  # noqa: E402

st.set_page_config(page_title="Base R&D – essais PVC", page_icon="🧪", layout="wide")
st.title("🧪 Base de données R&D – essais de formulation (données fictives)")

if not config.DB_PATH.exists():
    st.error("Base introuvable. Lancez d'abord : `python scripts/generate_sample_data.py` "
             "puis `python -m rdcap.pipeline`.")
    st.stop()

conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)


def to_excel(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Export")
    return buffer.getvalue()


tab_search, tab_trial, tab_compare, tab_quality = st.tabs(
    ["🔍 Recherche", "📄 Fiche essai", "⚖️ Comparaison", "✅ Qualité des données"])

# ------------------------------------------------------------------ search
with tab_search:
    c1, c2, c3 = st.columns(3)
    plasticizers = c1.multiselect("Plastifiant", q.list_values(conn, "plasticizer"))
    studies = c1.multiselect("Étude", q.list_values(conn, "study_id"))
    phr = c2.slider("Taux de plastifiant (phr)", 0, 120, (0, 120))
    years = c2.slider("Année", 2020, 2025, (2020, 2025))
    visco_max = c3.number_input("Viscosité 1h max (mPa.s)", min_value=0, value=20000, step=500)

    results = q.search_trials(conn, plasticizers, studies, phr[0], phr[1], visco_max, years[0], years[1])
    st.caption(f"{len(results)} essai(s) trouvé(s)")
    st.dataframe(results, use_container_width=True, hide_index=True)
    st.download_button("📥 Exporter en Excel", to_excel(results), "essais.xlsx")

    if len(results) > 1:
        st.subheader("Viscosité 1h selon le taux de plastifiant")
        st.scatter_chart(results, x="plasticizer_phr", y="viscosite_1h", color="plasticizer")

# ------------------------------------------------------------------ one trial
with tab_trial:
    all_trials = q.search_trials(conn)["trial_id"].tolist()
    trial_id = st.selectbox("Choisir un essai", all_trials)
    if trial_id:
        d = q.trial_details(conn, trial_id)
        s = d["summary"].iloc[0]
        st.markdown(f"**Étude :** {s['study_id']} – {s['study_title']}  \n"
                    f"**Date :** {s['trial_date']} · **Opérateur :** {s['operator']}  \n"
                    f"**Fichier source :** `{s['source_file']}`")
        c1, c2 = st.columns(2)
        c1.markdown("**Formulation**")
        c1.dataframe(d["formulation"], hide_index=True, use_container_width=True)
        c2.markdown("**Mesures** (valeur normalisée et valeur d'origine)")
        c2.dataframe(d["measurements"], hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ compare
with tab_compare:
    selected = st.multiselect("Essais à comparer", all_trials, default=all_trials[:3])
    if selected:
        comparison = q.compare_trials(conn, selected)
        st.dataframe(comparison, use_container_width=True)
        st.download_button("📥 Exporter la comparaison", to_excel(comparison.reset_index()), "comparaison.xlsx")

# ------------------------------------------------------------------ quality
with tab_quality:
    issues = q.issues(conn)
    st.metric("Anomalies à vérifier", len(issues))
    st.dataframe(issues, use_container_width=True, hide_index=True)
