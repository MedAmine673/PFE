import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Dashboard Audit PFE", layout="wide")

st.title(" Résultats de l'Audit Sécurité")

report_file = "data/reports/Tenant_Production_audit_report.json"

if os.path.exists(report_file):
    with open(report_file, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)

    # Style pour le statut
    def style_result(val):
        color = '#ff4b4b' if val == "Fail" else '#00cc96'
        return f'color: {color}; font-weight: bold'

    st.dataframe(
        df.style.applymap(style_result, subset=['Result']),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Details": st.column_config.TextColumn(
                "Details",
                width="large",  # Donne plus d'espace à cette colonne
                help="Détails complets de la non-conformité"
            )
        }
    )
else:
    st.info("Lancez 'python3 -m src.main' pour générer les données.")