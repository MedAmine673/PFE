import streamlit as st
import pandas as pd
import json
import os

from src.tenants import get_all_tenants
from src.main import run_audit_workflow

st.set_page_config(page_title="Dashboard Audit PFE", layout="wide")


if "audit_done" not in st.session_state:
    st.session_state.audit_done = False

if "current_report" not in st.session_state:
    st.session_state.current_report = None

tenants = get_all_tenants()

if not tenants:
    st.warning("Aucun tenant trouvé.")
    st.stop()

tenant_names = [t["name"] for t in tenants]

selected_tenant_name = st.selectbox(
    "Choisir un tenant à auditer",
    tenant_names
)

selected_tenant = next((t for t in tenants if t["name"] == selected_tenant_name), None)

if st.button("Lancer l'audit"):
    if selected_tenant and selected_tenant.get("id"):
        with st.spinner(f"Audit en cours pour {selected_tenant_name}..."):
            report_data = run_audit_workflow(selected_tenant["id"], selected_tenant["name"])

        if report_data:
            st.session_state.audit_done = True
            st.session_state.current_report = report_data
            st.success(f"Audit terminé pour {selected_tenant_name}.")
        else:
            st.error("Erreur pendant l'audit.")
    else:
        st.error("Tenant invalide ou ID manquant.")

if st.session_state.audit_done and st.session_state.current_report:
    st.title("Résultats de l'Audit")
    data = st.session_state.current_report

    if isinstance(data, list):
        findings = data
        summary = {}
    else:
        findings = data.get("findings", [])
        summary = data.get("summary", {})

    df = pd.DataFrame(findings)

    if not df.empty and "Passed" in df.columns:
        df = df.drop(columns=["Passed"])

    if summary:
        st.subheader(f"Classification du risque - {selected_tenant_name}")

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

        c1, c2, c3 = st.columns(3)

        c1.markdown(
            f"<div class='metric-title'>Niveau</div>"
            f"<div class='metric-value'><span class='risk-badge {risk_class}'>{risk_level}</span></div>",
            unsafe_allow_html=True,
        )

        c2.markdown(
            f"<div class='metric-title'>Score</div>"
            f"<div class='metric-value'>{summary.get('risk_score', 0)}</div>",
            unsafe_allow_html=True,
        )

        c3.markdown(
            f"<div class='metric-title'>Non conformes</div>"
            f"<div class='metric-value'>{summary.get('failed_controls', 0)} / {summary.get('total_controls', len(findings))}</div>",
            unsafe_allow_html=True,
        )

        st.divider()

    def style_result(val):
        color = "#ff4b4b" if val == "Fail" else "#00cc96"
        return f"color: {color}; font-weight: bold"

    if not df.empty and "Result" in df.columns:
        styled_df = df.style.map(style_result, subset=["Result"])
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
    st.info("Sélectionnez un tenant puis cliquez sur 'Lancer l'audit'.")