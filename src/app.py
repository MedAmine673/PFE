import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Dashboard Audit PFE", layout="wide")

st.title(" Résultats de l'Audit Sécurité")

report_file = "data/reports/Tenant_01_audit_report.json"

if os.path.exists(report_file):
    with open(report_file, "r") as f:
        data = json.load(f)

    # Compatibilité: ancien format (liste) vs nouveau format (dict avec summary/findings)
    if isinstance(data, list):
        findings = data
        summary = {}
    else:
        findings = data.get("findings", [])
        summary = data.get("summary", {})

    df = pd.DataFrame(findings)

    # Supprime la colonne Passed si elle existe
    if "Passed" in df.columns:
        df = df.drop(columns=["Passed"])

    # Bloc classification du risque (au-dessus du tableau)
    if summary:
        st.subheader("Classification du risque")

        st.markdown(
            """
            <style>
            .metric-title {
                font-size:18px;
                font-weight:600;
            }
            .metric-value {
                font-size:28px;
                font-weight:700;
            }

            .risk-badge {
                padding:6px 14px;
                border-radius:8px;
                font-weight:600;
                display:inline-block;
            }
            .risk-low {
                background:#e6f4ea;
                color:#137333;
            }
            .risk-medium {
                background:#fff4e5;
                color:#b45309;
            }
            .risk-high {
                background:#ffe4e6;
                color:#b91c1c;
            }
            .risk-critical {
                background:#f8d7da;
                color:#7f1d1d;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        risk_level = summary.get("risk_level", "N/A")
        risk_class = {
            "Faible": "risk-low",
            "Modéré": "risk-medium",
            "Élevé": "risk-high",
            "Critique": "risk-critical",
        }.get(risk_level, "")

        col1, col2, col3 = st.columns(3)

        col1.markdown(
            f"<div class='metric-title'>Niveau</div>"
            f"<div class='metric-value'><span class='risk-badge {risk_class}'>{risk_level}</span></div>",
            unsafe_allow_html=True,
        )

        col2.markdown(
            f"<div class='metric-title'>Score</div><div class='metric-value'>{summary.get('risk_score',0)}</div>",
            unsafe_allow_html=True,
        )

        col3.markdown(
            f"<div class='metric-title'>Non conformes</div>"
            f"<div class='metric-value'>{summary.get('failed_controls',0)} / {summary.get('total_controls',len(findings))}</div>",
            unsafe_allow_html=True,
        )

        st.divider()

    # Style pour le statut
    def style_result(val):
        color = "#ff4b4b" if val == "Fail" else "#00cc96"
        return f"color: {color}; font-weight: bold"

    # Sécurité: si la colonne Result n'existe pas
    if "Result" in df.columns:
        styled_df = df.style.applymap(style_result, subset=["Result"])
    else:
        styled_df = df.style

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Details": st.column_config.TextColumn(
                "Details",
                width="large",
                help="Détails complets de la non-conformité",
            )
        },
    )
else:
    st.info("Lancez 'python3 -m src.main' pour générer les données.")