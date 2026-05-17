import streamlit as st
import pandas as pd
import altair as alt
import math

from src.tenants import get_all_tenants
from src.main import run_and_save_audit
from src.storage.db_store import get_audit_runs_by_tenant, get_audit_report_by_run_id

try:
    from src.storage.blob_store import list_blob_reports, load_blob_report
except Exception:
    list_blob_reports = None
    load_blob_report = None


# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CloudShift — Audit M365",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: #f8f9fb !important;
    color: #1a202c;
}

.block-container {
    padding-top: 0 !important;
    padding-bottom: 3rem !important;
    max-width: 1600px;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.app-header {
    padding: 28px 0 24px;
    margin-bottom: 18px;
    border-bottom: 1px solid #dbe3ef;
    display: flex;
    justify-content: center;
    align-items: center;
    text-align: center;
}

.app-title-main {
    font-size: 40px;
    font-weight: 800;
    color: #0b1b53;
    letter-spacing: -0.9px;
    line-height: 1.15;
    margin: 0;
}

.tenant-section {
    margin-top: 4px;
    margin-bottom: 14px;
}

.tenant-title {
    font-size: 22px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 6px;
}

.tenant-sub {
    font-size: 16px;
    color: #64748b;
    margin-top: 0;
    margin-bottom: 14px;
}

.section-heading {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.8px;
    color: #64748b;
    margin: 36px 0 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #dbe3ef;
}

.action-card {
    background: #ffffff;
    border: 1px solid #dbe3ef;
    border-radius: 14px;
    padding: 18px 20px 16px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    min-height: 130px;
}

.action-card-title {
    font-size: 18px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 8px;
    letter-spacing: -0.3px;
}

.action-card-sub {
    font-size: 15px;
    color: #64748b;
    line-height: 1.5;
    margin-bottom: 14px;
}

.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 22px 24px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.2s, transform 0.2s;
}

.kpi-card:hover {
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    transform: translateY(-1px);
}

.kpi-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
}

.kpi-card.accent-red::after    { background: linear-gradient(90deg, #ef4444, #f87171); }
.kpi-card.accent-orange::after { background: linear-gradient(90deg, #f97316, #fb923c); }
.kpi-card.accent-blue::after   { background: linear-gradient(90deg, #1e40af, #3b82f6); }
.kpi-card.accent-green::after  { background: linear-gradient(90deg, #16a34a, #4ade80); }
.kpi-card.accent-gray::after   { background: #e2e8f0; }

.kpi-label {
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.1px;
    color: #94a3b8;
    margin-bottom: 12px;
}

.kpi-value {
    font-size: 36px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1;
    letter-spacing: -1px;
    margin-bottom: 6px;
}

.kpi-value-frac {
    font-size: 22px;
    font-weight: 500;
    color: #cbd5e1;
    letter-spacing: 0;
}

.kpi-sub {
    font-size: 14px;
    color: #64748b;
    font-weight: 500;
    margin-top: 4px;
}

.risk-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 700;
}

.risk-badge::before {
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}

.risk-faible   { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.risk-faible::before   { background: #22c55e; }
.risk-modere   { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.risk-modere::before   { background: #f59e0b; }
.risk-eleve    { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
.risk-eleve::before    { background: #f97316; }
.risk-critique { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.risk-critique::before { background: #ef4444; }

.score-bar-track {
    background: #e2e8f0;
    border-radius: 999px;
    height: 8px;
    margin-top: 16px;
    overflow: hidden;
}

.score-bar-fill {
    height: 100%;
    border-radius: 999px;
}

.stButton > button {
    border-radius: 12px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    height: 48px !important;
    letter-spacing: -0.1px !important;
    transition: all 0.18s ease !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2450d3 0%, #3262e4 100%) !important;
    border: none !important;
    box-shadow: 0 3px 10px rgba(37,99,235,0.28), inset 0 1px 0 rgba(255,255,255,0.10) !important;
    color: #fff !important;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1e44bd 0%, #2b57d5 100%) !important;
    box-shadow: 0 6px 16px rgba(37,99,235,0.34) !important;
    transform: translateY(-1px) !important;
}

.stButton > button:not([kind="primary"]) {
    background: #eef3ff !important;
    border: 1px solid #bcd0ff !important;
    color: #2c55d8 !important;
    font-weight: 700 !important;
}

.stButton > button:not([kind="primary"]):hover {
    background: #e2ebff !important;
    border-color: #9fb8ff !important;
    color: #2148c7 !important;
}

.stSelectbox { width: 100% !important; }
.stSelectbox > div { width: 100% !important; }

.stSelectbox > div > div {
    min-height: 54px !important;
    border-radius: 14px !important;
    border: 1.5px solid #d7deea !important;
    background: #ffffff !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03) !important;
    transition: all 0.2s ease !important;
    overflow: visible !important;
}

.stSelectbox > div > div:hover {
    border-color: #3b82f6 !important;
    box-shadow: 0 4px 12px rgba(59,130,246,0.10) !important;
}

.stSelectbox div[data-baseweb="select"] > div {
    min-height: 54px !important;
    padding-left: 10px !important;
    padding-right: 10px !important;
}

.stSelectbox span {
    font-size: 16px !important;
    font-weight: 600 !important;
    color: #0f172a !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    line-height: 1.4 !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: transparent !important;
    border-bottom: 1px solid #e2e8f0;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 0 !important;
    padding: 13px 26px !important;
    font-size: 17px !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
    background: transparent !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    transition: color 0.15s !important;
}

.stTabs [data-baseweb="tab"]:hover { color: #475569 !important; }

.stTabs [aria-selected="true"] {
    color: #1e40af !important;
    font-weight: 700 !important;
    border-bottom-color: #2563eb !important;
}

.stAlert {
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 10px 16px !important;
}

.streamlit-expanderHeader {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #1e293b !important;
    background: #ffffff !important;
    border-radius: 12px !important;
    border: 1px solid #dbe3ef !important;
    padding: 14px 18px !important;
}

.stCaption {
    color: #64748b !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    margin-bottom: 18px !important;
}

.result-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 28px 0 18px;
}

.result-heading-title {
    font-size: 24px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.3px;
}

.result-heading-date {
    font-size: 13px;
    color: #64748b;
    font-weight: 600;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 4px 10px;
}

.ctrl-table-wrap {
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    overflow-x: auto;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    background: #fff;
    margin-top: 8px;
}

table.ctrl-table {
    width: 100%;
    min-width: 1400px;
    border-collapse: collapse;
    font-family: 'Plus Jakarta Sans', sans-serif;
    background: #fff;
}

.ctrl-table thead tr {
    background: #f1f5f9;
    border-bottom: 2px solid #e2e8f0;
}

.ctrl-table th {
    padding: 11px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #1e293b;
    white-space: nowrap;
}

.ctrl-table th:nth-child(4),
.ctrl-table th:nth-child(6),
.ctrl-table th:nth-child(7) {
    text-align: center;
}

.ctrl-table tbody tr {
    border-bottom: 1px solid #f1f5f9;
    transition: background 0.1s;
}

.ctrl-table tbody tr:last-child { border-bottom: none; }
.ctrl-table tbody tr:nth-child(even) { background: #fafbfc; }
.ctrl-table tbody tr:hover { background: #eff6ff; }
.ctrl-table tbody tr.row-fail { border-left: 3px solid #fca5a5; }
.ctrl-table tbody tr.row-pass { border-left: 3px solid transparent; }

.ctrl-table td {
    padding: 10px 14px;
    font-size: 13px;
    color: #374151;
    vertical-align: top;
    line-height: 1.5;
}

.ctrl-table td.td-id {
    font-size: 11.5px;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.3px;
    white-space: nowrap;
}

.ctrl-table td.td-req  { font-weight: 600; color: #1e293b; }
.ctrl-table td.td-detail,
.ctrl-table td.td-reco { font-size: 12.5px; color: #1e293b; }

.ctrl-table td:nth-child(4),
.ctrl-table td:nth-child(6),
.ctrl-table td:nth-child(7) {
    text-align: center;
    vertical-align: middle;
}

.pill {
    display: inline-block;
    padding: 3px 11px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.2px;
}

.pill-pass { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.pill-fail { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }

.crit {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    font-weight: 600;
}

.crit::before {
    content: '';
    width: 7px; height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}

.crit-Critical { color: #b91c1c; }
.crit-Critical::before { background: #ef4444; box-shadow: 0 0 0 2px #fee2e2; }
.crit-High     { color: #c2410c; }
.crit-High::before     { background: #f97316; box-shadow: 0 0 0 2px #ffedd5; }
.crit-Medium   { color: #b45309; }
.crit-Medium::before   { background: #f59e0b; box-shadow: 0 0 0 2px #fef3c7; }
.crit-Low      { color: #15803d; }
.crit-Low::before      { background: #22c55e; box-shadow: 0 0 0 2px #dcfce7; }

.cat {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 5px;
    font-size: 11.5px;
    font-weight: 700;
}

.cat-Roles    { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.cat-PIM      { background: #f0f9ff; color: #0369a1; border: 1px solid #bae6fd; }
.cat-MFA      { background: #faf5ff; color: #7e22ce; border: 1px solid #e9d5ff; }
.cat-CA       { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.cat-Activity { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }

.rp-high { color: #b91c1c; font-weight: 700; }
.rp-low  { color: #64748b; font-weight: 600; }

.chart-title-fixed {
    font-size: 18px;
    font-weight: 800;
    color: #0f172a;
    margin: 4px 0 6px;
    letter-spacing: -0.2px;
}

.chart-sub-fixed {
    font-size: 14px;
    font-weight: 500;
    color: #8091ad;
    margin-bottom: 14px;
}

.history-caption {
    font-size: 15px;
    color: #64748b;
    font-weight: 500;
    margin: 18px 0 20px;
}

.history-caption strong {
    color: #0f172a;
    font-weight: 700;
}

.history-caption {
    font-size: 15px;
    color: #64748b;
    font-weight: 500;
    margin: 18px 0 20px;
}

.history-caption strong {
    color: #0f172a;
    font-weight: 700;
}

.empty-state {
    background: #ffffff;
    border: 1.5px dashed #cbd5e1;
    border-radius: 16px;
    padding: 72px 40px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}

.empty-state-icon {
    font-size: 44px;
    margin-bottom: 18px;
    display: block;
    opacity: 0.35;
}

.empty-state-title {
    font-size: 20px;
    font-weight: 800;
    color: #1e293b;
    margin-bottom: 10px;
    letter-spacing: -0.3px;
}

.empty-state-sub {
    font-size: 15px;
    color: #94a3b8;
    line-height: 1.8;
}

.tenant-id-box {
    background: #f8fafc;
    border: 1px solid #d7deea;
    border-radius: 14px;
    min-height: 54px;
    display: flex;
    align-items: center;
    padding: 0 18px;
    font-size: 15px;
    color: #334155;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.tenant-id-box strong {
    color: #0f172a;
    margin-right: 6px;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f8f9fb; }
::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #cbd5e1; }
</style>
""", unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="app-title-main">Audit de sécurité Microsoft 365</div>
</div>
""", unsafe_allow_html=True)


# ─── Session state ────────────────────────────────────────────────────────────
for key, default in [
    ("audit_done", False),
    ("current_report", None),
    ("audited_tenant_name", None),
    ("show_success_message", False),
    ("current_source", "local"),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ─── Helpers ──────────────────────────────────────────────────────────────────
def format_audit_label(audit_run):
    dt = audit_run["audit_date"]
    date_part, time_part = dt.split("T")
    time_part = time_part.split(".")[0]
    return f"Audit #{audit_run['id']} - {date_part} {time_part}"


def format_blob_label(blob_report):
    name = blob_report.get("name", "")
    last_modified = blob_report.get("last_modified")

    tenant = name.split("/")[0] if "/" in name else "Tenant"
    filename = name.split("/")[-1]

    date_display = ""
    if last_modified:
        try:
            date_display = last_modified.strftime("%d/%m/%Y à %H:%M")
        except Exception:
            date_display = ""

    if not date_display:
        try:
            parts = name.split("/")
            year, month, day = parts[1], parts[2], parts[3]
            date_display = f"{day}/{month}/{year}"
        except Exception:
            date_display = "Date inconnue"

    return f"{tenant} • {date_display}"


def build_history_dataframe(audit_runs_data):
    if not audit_runs_data:
        return pd.DataFrame()

    df = pd.DataFrame(audit_runs_data).copy()

    if df.empty:
        return df

    df["audit_date"] = pd.to_datetime(df["audit_date"], errors="coerce")
    df = df.dropna(subset=["audit_date"])
    df = df.sort_values("audit_date").reset_index(drop=True)
    df["display_date"] = df["audit_date"].dt.strftime("%d/%m %H:%M")
    df["audit_order"] = range(1, len(df) + 1)

    if len(df) > 15:
        df = df.tail(15).reset_index(drop=True)

    return df


def risk_badge_html(level):
    css_map = {
        "Faible": "risk-faible",
        "Modéré": "risk-modere",
        "Élevé": "risk-eleve",
        "Critique": "risk-critique",
    }
    css = css_map.get(level, "")
    return f'<span class="risk-badge {css}">{level}</span>'


def risk_bar_color(level):
    return {
        "Faible": "#22c55e",
        "Modéré": "#f59e0b",
        "Élevé": "#f97316",
        "Critique": "#ef4444",
    }.get(level, "#94a3b8")


def kpi_accent(level):
    return {
        "Faible": "accent-green",
        "Modéré": "accent-orange",
        "Élevé": "accent-orange",
        "Critique": "accent-red",
    }.get(level, "accent-gray")


def build_line_chart(df, y_col, y_title, line_color):
    base = alt.Chart(df).encode(
        x=alt.X(
            "display_date:N",
            sort=None,
            title=None,
            axis=alt.Axis(
                labelAngle=-35,
                labelFontSize=13,
                labelColor="#7c8aa5",
                labelFont="Plus Jakarta Sans",
                labelFontWeight=500,
                domainColor="#e2e8f0",
                tickColor="#e2e8f0",
                grid=False,
            )
        ),
        y=alt.Y(
            f"{y_col}:Q",
            title=y_title,
            axis=alt.Axis(
                labelFontSize=13,
                labelColor="#7c8aa5",
                labelFont="Plus Jakarta Sans",
                labelFontWeight=500,
                titleColor="#7c8aa5",
                titleFontSize=14,
                titleFontWeight=600,
                titleFont="Plus Jakarta Sans",
                gridColor="#edf2f7",
                gridOpacity=0.9,
                domainOpacity=0,
            )
        ),
        tooltip=[
            alt.Tooltip("display_date:N", title="Date"),
            alt.Tooltip("risk_score:Q", title="Score"),
            alt.Tooltip("failed_controls:Q", title="Non conformes"),
            alt.Tooltip("risk_level:N", title="Niveau"),
        ]
    )

    area = base.mark_area(
        opacity=0.10,
        color=line_color,
        interpolate="monotone"
    )

    line = base.mark_line(
        strokeWidth=3.5,
        color=line_color,
        interpolate="monotone"
    )

    points = base.mark_circle(
        size=80,
        color=line_color,
        opacity=1
    )

    return (area + line + points).properties(
        height=230,
        background="#ffffff",
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        labelPadding=8,
        titlePadding=12
    )


def safe_str(val):
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val)


# ─── Load tenants ─────────────────────────────────────────────────────────────
tenants = get_all_tenants()

if not tenants:
    st.warning("Aucun tenant trouvé. Vérifiez votre fichier tenants.json.")
    st.stop()

tenant_names = [t["name"] for t in tenants]


# ══════════════════════════════════════════════════════════════════════════════
# 1 · Sélection du tenant
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="tenant-section">
    <div class="tenant-title">Tenant cible</div>
    <div class="tenant-sub">Sélectionnez le tenant Microsoft 365 à auditer.</div>
</div>
""", unsafe_allow_html=True)

col_sel, col_id = st.columns([3.2, 2.2])

with col_sel:
    selected_tenant_name = st.selectbox(
        "Tenant",
        tenant_names,
        label_visibility="collapsed",
    )

with col_id:
    selected_tenant = next((t for t in tenants if t["name"] == selected_tenant_name), None)
    tid = selected_tenant.get("id", "") if selected_tenant else ""

    st.markdown(
        f'<div class="tenant-id-box"><strong>Tenant ID :</strong> {tid}</div>',
        unsafe_allow_html=True
    )

audit_runs = get_audit_runs_by_tenant(selected_tenant_name)


# ══════════════════════════════════════════════════════════════════════════════
# 2 · Actions
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-heading">Actions</div>', unsafe_allow_html=True)

launch = False
load_old_audit = False
load_cloud_audit = False
selected_audit_label = None
selected_blob = None
blob_reports = []

col_new, col_hist = st.columns(2, gap="large")

with col_new:
    st.markdown("""
    <div class="action-card">
        <div class="action-card-title">Nouvel audit</div>
        <div class="action-card-sub">Démarrez un nouvel audit manuel pour le tenant sélectionné et enregistrez le résultat dans SQLite.</div>
    """, unsafe_allow_html=True)

    launch = st.button("Lancer un audit", type="primary", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

with col_hist:
    st.markdown("""
    <div class="action-card">
        <div class="action-card-title">Consultation des résultats</div>
        <div class="action-card-sub">Consultez un audit local ou un rapport généré automatiquement dans le cloud.</div>
    """, unsafe_allow_html=True)

    result_source = st.radio(
        "Source",
        ["Historique local SQLite", "Rapports cloud Azure Blob Storage"],
        horizontal=True,
        label_visibility="collapsed",
        key="result_source_radio",
    )

    if result_source == "Historique local SQLite":
        if audit_runs:
            selected_audit_label = st.selectbox(
                "Audit",
                options=audit_runs,
                format_func=format_audit_label,
                key=f"history_select_{selected_tenant_name}",
                label_visibility="collapsed",
            )

            load_old_audit = st.button("Afficher cet audit local", use_container_width=True)
        else:
            st.selectbox(
                "Audit",
                options=["Aucun audit enregistré"],
                disabled=True,
                label_visibility="collapsed",
                key=f"history_empty_{selected_tenant_name}",
            )

            st.markdown(
                '<div style="font-size:13px;color:#64748b;margin-top:10px;">'
                "Lancez un premier audit pour alimenter l'historique local."
                '</div>',
                unsafe_allow_html=True,
            )

    else:
        if list_blob_reports is None or load_blob_report is None:
            st.error(
                "Le module Blob Storage n'est pas disponible. "
                "Vérifiez le fichier src/storage/blob_store.py et la dépendance azure-storage-blob."
            )
        else:
            try:
                blob_reports = list_blob_reports(selected_tenant_name)

                if blob_reports:
                    selected_blob = st.selectbox(
                        "Rapport cloud",
                        options=blob_reports,
                        format_func=format_blob_label,
                        key=f"blob_select_{selected_tenant_name}",
                        label_visibility="collapsed",
                    )

                    load_cloud_audit = st.button(
                        "Afficher ce rapport cloud",
                        use_container_width=True
                    )
                else:
                    st.selectbox(
                        "Rapport cloud",
                        options=["Aucun rapport cloud trouvé"],
                        disabled=True,
                        label_visibility="collapsed",
                        key=f"blob_empty_{selected_tenant_name}",
                    )

                    st.markdown(
                        '<div style="font-size:13px;color:#64748b;margin-top:10px;">'
                        "Aucun rapport JSON trouvé dans Azure Blob Storage pour ce tenant."
                        '</div>',
                        unsafe_allow_html=True,
                    )

            except Exception as e:
                st.error(f"Impossible de charger les rapports Blob Storage : {str(e)}")

    st.markdown("</div>", unsafe_allow_html=True)


# Messages de retour
if st.session_state.show_success_message:
    st.toast(
        f"Audit terminé avec succès pour {st.session_state.audited_tenant_name}.",
        icon="✅"
    )
    st.session_state.show_success_message = False


# ─── Logique métier ───────────────────────────────────────────────────────────
if launch:
    if selected_tenant and selected_tenant.get("id"):
        with st.spinner(f"Audit en cours pour {selected_tenant_name}..."):
            report_data = run_and_save_audit(
                selected_tenant["id"],
                selected_tenant["name"],
            )

        if report_data:
            st.session_state.audit_done = True
            st.session_state.current_report = report_data
            st.session_state.audited_tenant_name = selected_tenant_name
            st.session_state.show_success_message = True
            st.session_state.current_source = "local"
            st.rerun()
        else:
            st.error("Une erreur est survenue pendant l'audit. Vérifiez les logs.")
    else:
        st.error("Tenant invalide ou identifiant manquant.")


if load_old_audit and audit_runs and selected_audit_label:
    report_data = get_audit_report_by_run_id(selected_audit_label["id"])

    if report_data:
        st.session_state.audit_done = True
        st.session_state.current_report = report_data
        st.session_state.audited_tenant_name = selected_tenant_name
        st.session_state.current_source = "local"
        st.toast(
            f"Audit #{selected_audit_label['id']} chargé pour {selected_tenant_name}.",
            icon="📂"
        )
        st.rerun()
    else:
        st.error("Impossible de charger cet audit.")


if load_cloud_audit and selected_blob:
    try:
        report_data = load_blob_report(selected_blob["name"])

        if report_data:
            st.session_state.audit_done = True
            st.session_state.current_report = report_data
            st.session_state.audited_tenant_name = report_data.get(
                "tenant",
                selected_tenant_name
            )
            st.session_state.current_source = "cloud"
            st.toast("Rapport cloud chargé depuis Azure Blob Storage.", icon="☁️")
            st.rerun()
        else:
            st.error("Le rapport cloud est vide ou invalide.")

    except Exception as e:
        st.error(f"Impossible de charger ce rapport cloud : {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# 3 · Résultats
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.audit_done and st.session_state.current_report:
    data = st.session_state.current_report
    displayed_tenant = st.session_state.audited_tenant_name or selected_tenant_name
    current_source = st.session_state.current_source

    findings = data.get("findings", []) if isinstance(data, dict) else data
    summary = data.get("summary", {}) if isinstance(data, dict) else {}

    df = pd.DataFrame(findings)

    if not df.empty and "Passed" in df.columns:
        df = df.drop(columns=["Passed"])

    audit_date_str = ""

    if summary.get("audit_date"):
        audit_date_str = summary["audit_date"].replace("T", " ").split(".")[0]

    source_label = "SQLite local" if current_source == "local" else "Azure Blob Storage"

    st.markdown(f"""
    <div class="result-heading">
        <div class="result-heading-title">Résultats - {displayed_tenant}</div>
        <div class="result-heading-date">{source_label} | {audit_date_str}</div>
    </div>
    """, unsafe_allow_html=True)

    if summary:
        risk_level = summary.get("risk_level", "N/A")
        risk_score = summary.get("risk_score", 0)
        failed = summary.get("failed_controls", 0)
        total = summary.get("total_controls", len(findings))
        passed = total - failed
        bar_color = risk_bar_color(risk_level)
        score_pct = min(int(risk_score * 2.5), 100)
        fail_pct = int((failed / total) * 100) if total else 0

        c1, c2, c3, c4 = st.columns(4, gap="medium")

        with c1:
            st.markdown(f"""
            <div class="kpi-card {kpi_accent(risk_level)}">
                <div class="kpi-label">Niveau de risque</div>
                {risk_badge_html(risk_level)}
                <div class="score-bar-track">
                    <div class="score-bar-fill"
                         style="width:{score_pct}%;background:{bar_color}"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="kpi-card accent-blue">
                <div class="kpi-label">Score de risque</div>
                <div class="kpi-value">{risk_score}</div>
                <div class="kpi-sub">points accumulés</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="kpi-card accent-red">
                <div class="kpi-label">Non conformes</div>
                <div class="kpi-value">{failed}<span class="kpi-value-frac"> / {total}</span></div>
                <div class="kpi-sub">{fail_pct}% des contrôles en échec</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="kpi-card accent-green">
                <div class="kpi-label">Conformes</div>
                <div class="kpi-value">{passed}<span class="kpi-value-frac"> / {total}</span></div>
                <div class="kpi-sub">{100 - fail_pct}% des contrôles conformes</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    tab_detail, tab_history = st.tabs([
        "  Détail des contrôles  ",
        "  Évolution historique locale  "
    ])

    with tab_detail:
        if not df.empty:
            display_cols = [
                c for c in [
                    "Control ID",
                    "Category",
                    "Requirement",
                    "Result",
                    "Criticality",
                    "Risk Points",
                    "Affected",
                    "Details",
                    "Recommendation",
                ]
                if c in df.columns
            ]

            col_labels = {
                "Control ID": "ID contrôle",
                "Category": "Catégorie",
                "Requirement": "Exigence",
                "Result": "Résultat",
                "Criticality": "Criticité",
                "Risk Points": "Points de risque",
                "Affected": "Éléments affectés",
                "Details": "Détails",
                "Recommendation": "Recommandation",
            }

            category_labels = {
                "Roles": "Rôles",
                "PIM": "PIM",
                "MFA": "MFA",
                "CA": "CA",
                "Activity": "Activité",
            }

            result_labels = {
                "Pass": "Conforme",
                "Fail": "Non conforme",
            }

            criticality_labels = {
                "Low": "Faible",
                "Medium": "Modéré",
                "High": "Élevé",
                "Critical": "Critique",
            }

            header_cells = "".join(
                f"<th>{col_labels.get(c, c)}</th>"
                for c in display_cols
            )

            rows_html = ""

            for _, row in df[display_cols].iterrows():
                result_val = safe_str(row.get("Result", ""))
                row_class = "row-fail" if result_val == "Fail" else "row-pass"
                cells = ""

                for col in display_cols:
                    val = safe_str(row.get(col, ""))

                    if col == "Control ID":
                        cells += f'<td class="td-id">{val}</td>'

                    elif col == "Category":
                        cat_cls = f"cat-{val}" if val in ["Roles", "PIM", "MFA", "CA", "Activity"] else ""
                        val_fr = category_labels.get(val, val)
                        cells += f'<td><span class="cat {cat_cls}">{val_fr}</span></td>'

                    elif col == "Requirement":
                        cells += f'<td class="td-req">{val}</td>'

                    elif col == "Result":
                        pill_cls = "pill-pass" if val == "Pass" else "pill-fail"
                        val_fr = result_labels.get(val, val)
                        cells += f'<td><span class="pill {pill_cls}">{val_fr}</span></td>'

                    elif col == "Criticality":
                        crit_cls = f"crit-{val}"
                        val_fr = criticality_labels.get(val, val)
                        cells += f'<td><span class="crit {crit_cls}">{val_fr}</span></td>'

                    elif col == "Risk Points":
                        try:
                            rp_cls = "rp-high" if float(val) > 5 else "rp-low"
                        except Exception:
                            rp_cls = "rp-low"

                        cells += f'<td><span class="{rp_cls}">{val}</span></td>'

                    elif col == "Details":
                        cells += f'<td class="td-detail">{val}</td>'

                    elif col == "Recommendation":
                        cells += f'<td class="td-reco">{val}</td>'

                    else:
                        cells += f'<td>{val}</td>'

                rows_html += f'<tr class="{row_class}">{cells}</tr>'

            html_table = f"""
            <div class="ctrl-table-wrap">
              <table class="ctrl-table">
                <thead><tr>{header_cells}</tr></thead>
                <tbody>{rows_html}</tbody>
              </table>
            </div>
            """

            st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.info("Aucun résultat à afficher pour ce tenant.")

    with tab_history:
        history_df = build_history_dataframe(audit_runs)

        if current_source == "cloud":
            st.info(
                "Cette courbe utilise l’historique local SQLite. "
                "Le rapport affiché vient du Blob Storage et n’est pas encore injecté dans SQLite."
            )

        if not history_df.empty:
            st.markdown(
                f"""
                <div class="history-caption">
                    {len(history_df)} audit(s) local(aux) enregistré(s) pour <strong>{selected_tenant_name}</strong>.
                </div>
                """,
                unsafe_allow_html=True
            )

            g1, g2 = st.columns(2, gap="large")

            with g1:
                with st.container(border=True):
                    st.markdown("""
                    <div class="chart-title-fixed">Score de risque</div>
                    <div class="chart-sub-fixed">Évolution locale dans le temps</div>
                    """, unsafe_allow_html=True)

                    st.altair_chart(
                        build_line_chart(history_df, "risk_score", "Score", "#2563eb"),
                        use_container_width=True,
                    )

            with g2:
                with st.container(border=True):
                    st.markdown("""
                    <div class="chart-title-fixed">Contrôles non conformes</div>
                    <div class="chart-sub-fixed">Évolution locale dans le temps</div>
                    """, unsafe_allow_html=True)

                    st.altair_chart(
                        build_line_chart(history_df, "failed_controls", "Non conformes", "#ef4444"),
                        use_container_width=True,
                    )

        else:
            st.info(
                "Aucune donnée historique locale disponible. "
                "Lancez plusieurs audits locaux pour voir l'évolution."
            )

else:
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="empty-state">
        <span class="empty-state-icon"></span>
        <div class="empty-state-title">Aucun audit sélectionné</div>
        <div class="empty-state-sub">
            Sélectionnez un tenant, puis lancez un audit local<br>
            ou chargez un rapport cloud depuis Azure Blob Storage.
        </div>
    </div>
    """, unsafe_allow_html=True)

    history_df = build_history_dataframe(audit_runs)

    if not history_df.empty:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        with st.expander(f"Évolution historique locale - {selected_tenant_name}"):
            g1, g2 = st.columns(2, gap="large")

            with g1:
                st.markdown("""
                <div class="chart-wrap">
                    <div class="chart-wrap-title">Score de risque</div>
                    <div class="chart-wrap-sub">Évolution locale dans le temps</div>
                """, unsafe_allow_html=True)

                st.altair_chart(
                    build_line_chart(history_df, "risk_score", "Score", "#2563eb"),
                    use_container_width=True,
                )

                st.markdown("</div>", unsafe_allow_html=True)

            with g2:
                st.markdown("""
                <div class="chart-wrap">
                    <div class="chart-wrap-title">Contrôles non conformes</div>
                    <div class="chart-wrap-sub">Évolution locale dans le temps</div>
                """, unsafe_allow_html=True)

                st.altair_chart(
                    build_line_chart(history_df, "failed_controls", "Non conformes", "#ef4444"),
                    use_container_width=True,
                )

                st.markdown("</div>", unsafe_allow_html=True)