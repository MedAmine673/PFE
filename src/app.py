import streamlit as st
import pandas as pd
from src.tenants import get_all_tenants
from src.main import run_and_save_audit
from src.storage.db_store import get_audit_runs_by_tenant, get_audit_report_by_run_id

st.set_page_config(
    page_title="Dashboard Audit PFE",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 38px;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .subtitle {
        font-size: 17px;
        color: #6b7280;
        margin-bottom: 24px;
    }
    .metric-card {
        background: #ffffff;
        padding: 18px;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .metric-title {
        font-size: 15px;
        font-weight: 600;
        color: #6b7280;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 30px;
        font-weight: 700;
        color: #111827;
    }
    .risk-badge {
        padding: 8px 16px;
        border-radius: 12px;
        font-weight: 700;
        display: inline-block;
        font-size: 16px;
    }
    .risk-low {
        background: #e6f4ea;
        color: #137333;
    }
    .risk-medium {
        background: #fff4e5;
        color: #b45309;
    }
    .risk-high {
        background: #ffe4e6;
        color: #b91c1c;
    }
    .risk-critical {
        background: #f8d7da;
        color: #7f1d1d;
    }
    .action-label {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .small-button button {
        height: 42px;
        font-size: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "audit_done" not in st.session_state:
    st.session_state.audit_done = False

if "current_report" not in st.session_state:
    st.session_state.current_report = None

if "audited_tenant_name" not in st.session_state:
    st.session_state.audited_tenant_name = None

if "show_success_message" not in st.session_state:
    st.session_state.show_success_message = False

tenants = get_all_tenants()

if not tenants:
    st.warning("Aucun tenant trouvé.")
    st.stop()

tenant_names = [t["name"] for t in tenants]

st.markdown("<div class='main-title'>Audit Sécurité Microsoft Entra ID</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='subtitle'>Sélectionnez un tenant, lancez un nouvel audit ou consultez un audit déjà enregistré.</div>",
    unsafe_allow_html=True,
)

selected_tenant_name = st.selectbox(
    "Choisir un tenant à auditer",
    tenant_names
)

selected_tenant = next((t for t in tenants if t["name"] == selected_tenant_name), None)
st.caption(f"Tenant sélectionné : {selected_tenant_name}")

if st.session_state.show_success_message:
    st.success(f"Audit terminé pour {st.session_state.audited_tenant_name}.")
    st.session_state.show_success_message = False

# Historique relu à chaque exécution de la page
audit_runs = get_audit_runs_by_tenant(selected_tenant_name)

def format_audit_label(audit_run):
    dt = audit_run["audit_date"]
    date_part, time_part = dt.split("T")
    time_part = time_part.split(".")[0]
    return f"Audit #{audit_run['id']} — {date_part} {time_part}"

st.markdown("### Actions")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("<div class='small-button'>", unsafe_allow_html=True)
    launch = st.button("Lancer un nouvel audit", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    if audit_runs:
        st.markdown("<div class='action-label'>Historique des audits</div>", unsafe_allow_html=True)

        selected_audit_label = st.selectbox(
            "Choisir un ancien audit",
            options=audit_runs,
            format_func=format_audit_label,
            key=f"history_select_{selected_tenant_name}",
            label_visibility="collapsed"
        )

        load_old_audit = st.button("Afficher cet audit", use_container_width=True)
    else:
        st.markdown("<div class='action-label'>Historique des audits</div>", unsafe_allow_html=True)

        st.selectbox(
            "Choisir un ancien audit",
            options=["Aucun audit enregistré pour ce tenant"],
            disabled=True,
            label_visibility="collapsed",
            key=f"history_empty_{selected_tenant_name}"
        )

        load_old_audit = False

if launch:
    if selected_tenant and selected_tenant.get("id"):
        with st.spinner(f"Audit en cours pour {selected_tenant_name}..."):
            report_data = run_and_save_audit(
                selected_tenant["id"],
                selected_tenant["name"]
            )

        if report_data:
            st.session_state.audit_done = True
            st.session_state.current_report = report_data
            st.session_state.audited_tenant_name = selected_tenant_name
            st.session_state.show_success_message = True
            st.rerun()
        else:
            st.error("Erreur pendant l'audit.")
    else:
        st.error("Tenant invalide ou ID manquant.")

if load_old_audit and audit_runs:
    report_data = get_audit_report_by_run_id(selected_audit_label["id"])

    if report_data:
        st.session_state.audit_done = True
        st.session_state.current_report = report_data
        st.session_state.audited_tenant_name = selected_tenant_name
        st.success(f"Ancien audit chargé pour {selected_tenant_name}.")
    else:
        st.error("Impossible de charger cet audit.")

if st.session_state.audit_done and st.session_state.current_report:
    data = st.session_state.current_report
    displayed_tenant_name = st.session_state.audited_tenant_name or selected_tenant_name

    st.markdown("## Résultats de l'audit")

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
        st.markdown(f"### Classification du risque · {displayed_tenant_name}")

        if summary.get("audit_date"):
            st.caption(f"Date de l'audit : {summary.get('audit_date')}")

        risk_level = summary.get("risk_level", "N/A")
        risk_class = {
            "Faible": "risk-low",
            "Modéré": "risk-medium",
            "Élevé": "risk-high",
            "Critique": "risk-critical",
        }.get(risk_level, "")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-title'>Niveau de risque</div>
                    <div class='metric-value'>
                        <span class='risk-badge {risk_class}'>{risk_level}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-title'>Score</div>
                    <div class='metric-value'>{summary.get('risk_score', 0)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c3:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-title'>Contrôles non conformes</div>
                    <div class='metric-value'>{summary.get('failed_controls', 0)} / {summary.get('total_controls', len(findings))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

    if not df.empty:
        st.markdown("### Détail des contrôles")

        def style_result(val):
            if val == "Fail":
                return "color: #ef4444; font-weight: 700"
            if val == "Pass":
                return "color: #10b981; font-weight: 700"
            return ""

        if "Result" in df.columns:
            styled_df = df.style.map(style_result, subset=["Result"])
        else:
            styled_df = df.style

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Control ID": st.column_config.TextColumn("Control ID", width="small"),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Requirement": st.column_config.TextColumn("Requirement", width="medium"),
                "Result": st.column_config.TextColumn("Result", width="small"),
                "Criticality": st.column_config.TextColumn("Criticality", width="small"),
                "Risk Points": st.column_config.NumberColumn("Risk Points", width="small"),
                "Affected": st.column_config.NumberColumn("Affected", width="small"),
                "Details": st.column_config.TextColumn(
                    "Details",
                    width="large",
                    help="Détails complets du contrôle",
                ),
            },
        )
    else:
        st.info("Aucun résultat à afficher pour ce tenant.")
else:
    st.info("Sélectionnez un tenant puis lancez un nouvel audit ou chargez un audit existant.")