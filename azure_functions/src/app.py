import streamlit as st
import pandas as pd
import altair as alt

from src.tenants import get_all_tenants
from src.main import run_and_save_audit
from src.storage.db_store import get_audit_runs_by_tenant, get_audit_report_by_run_id

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CloudShift — Audit M365",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Layout */
.block-container {
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    max-width: 1200px;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Header ── */
.app-header {
    padding: 28px 0 20px;
    margin-bottom: 4px;
    border-bottom: 1px solid #e5e7eb;
}
.app-title {
    font-size: 20px;
    font-weight: 700;
    color: #111827;
    letter-spacing: -0.3px;
    margin: 0;
}

/* ── Section heading ── */
.section-heading {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.4px;
    color: #6b7280;
    margin: 28px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e5e7eb;
}

/* ── Panel (generic white card) ── */
.panel {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 20px 22px;
}

/* ── KPI cards ── */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 20px 22px;
    border-top: 3px solid #e5e7eb;
}
.kpi-card.accent-red   { border-top-color: #dc2626; }
.kpi-card.accent-green { border-top-color: #16a34a; }
.kpi-card.accent-blue  { border-top-color: #1a56a0; }

.kpi-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    color: #6b7280;
    margin-bottom: 10px;
}
.kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: #111827;
    line-height: 1;
    margin-bottom: 5px;
}
.kpi-value.red   { color: #dc2626; }
.kpi-value.green { color: #16a34a; }
.kpi-value.blue  { color: #1a56a0; }
.kpi-sub {
    font-size: 12px;
    color: #9ca3af;
    font-weight: 400;
}

/* ── Risk badge ── */
.risk-badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 700;
}
.risk-faible   { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.risk-modere   { background: #fefce8; color: #a16207; border: 1px solid #fef08a; }
.risk-eleve    { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
.risk-critique { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

/* ── Score bar ── */
.score-bar-track {
    background: #f3f4f6;
    border-radius: 4px;
    height: 6px;
    margin-top: 12px;
    overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    border-radius: 4px;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    transition: all 0.15s !important;
}
.stButton > button[kind="primary"] {
    background: #1a56a0 !important;
    border-color: #1a56a0 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #154280 !important;
    border-color: #154280 !important;
    box-shadow: 0 2px 8px rgba(26,86,160,0.25) !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: #9ca3af !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    border-radius: 6px !important;
    border-color: #d1d5db !important;
    font-size: 13px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 2px solid #e5e7eb;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 0 !important;
    padding: 10px 20px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #6b7280 !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -2px !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #1a56a0 !important;
    font-weight: 600 !important;
    border-bottom-color: #1a56a0 !important;
}

/* ── Dataframe ── */
.stDataFrame {
    border-radius: 8px !important;
    border: 1px solid #e5e7eb !important;
    overflow: hidden !important;
}

/* ── Alerts ── */
.stAlert { border-radius: 6px !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #374151 !important;
    background: #f9fafb !important;
    border-radius: 6px !important;
}

/* ── Caption ── */
.stCaption { color: #9ca3af !important; font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="app-title">Audit Sécurité Microsoft 365</div>
</div>
""", unsafe_allow_html=True)


# ─── Session state ────────────────────────────────────────────────────────────
for key, default in [
    ("audit_done", False),
    ("current_report", None),
    ("audited_tenant_name", None),
    ("show_success_message", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ─── Helpers ──────────────────────────────────────────────────────────────────
def format_audit_label(audit_run):
    dt = audit_run["audit_date"]
    date_part, time_part = dt.split("T")
    time_part = time_part.split(".")[0]
    return f"Audit #{audit_run['id']} — {date_part}  {time_part}"


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
        "Faible":   "risk-faible",
        "Modéré":   "risk-modere",
        "Élevé":    "risk-eleve",
        "Critique": "risk-critique",
    }
    css = css_map.get(level, "")
    return f'<span class="risk-badge {css}">{level}</span>'


def risk_bar_color(level):
    return {
        "Faible":   "#16a34a",
        "Modéré":   "#ca8a04",
        "Élevé":    "#ea580c",
        "Critique": "#dc2626",
    }.get(level, "#9ca3af")


def build_line_chart(df, y_col, y_title, line_color):
    base = alt.Chart(df).encode(
        x=alt.X(
            "display_date:N",
            sort=None,
            title=None,
            axis=alt.Axis(
                labelAngle=-30,
                labelFontSize=11,
                labelColor="#9ca3af",
                domainColor="#e5e7eb",
                tickColor="#e5e7eb",
                gridColor="#f3f4f6",
            )
        ),
        y=alt.Y(
            f"{y_col}:Q",
            title=y_title,
            axis=alt.Axis(
                labelFontSize=11,
                labelColor="#9ca3af",
                titleColor="#6b7280",
                titleFontSize=11,
                gridColor="#f3f4f6",
                domainOpacity=0,
            )
        ),
        tooltip=[
            alt.Tooltip("display_date:N",    title="Date"),
            alt.Tooltip("risk_score:Q",       title="Score"),
            alt.Tooltip("failed_controls:Q",  title="Non conformes"),
            alt.Tooltip("risk_level:N",       title="Niveau"),
        ]
    )
    area   = base.mark_area(opacity=0.06, color=line_color, interpolate="monotone")
    line   = base.mark_line(strokeWidth=2, color=line_color, interpolate="monotone")
    points = base.mark_circle(size=55, color=line_color, opacity=1)
    return (area + line + points).properties(
        height=210,
        background="#ffffff",
    ).configure_view(strokeWidth=0)


def style_result(val):
    if val == "Fail":
        return "color: #dc2626; font-weight: 700"
    if val == "Pass":
        return "color: #16a34a; font-weight: 700"
    return ""


def style_criticality(val):
    return ""


# ─── Load tenants ─────────────────────────────────────────────────────────────
tenants = get_all_tenants()
if not tenants:
    st.warning("Aucun tenant trouvé. Vérifiez votre fichier tenants.json.")
    st.stop()

tenant_names = [t["name"] for t in tenants]


# ══════════════════════════════════════════════════════════════════════════════
# 1 · Sélection du tenant
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-heading">Tenant cible</div>', unsafe_allow_html=True)

col_sel, col_id = st.columns([3, 2])

with col_sel:
    selected_tenant_name = st.selectbox(
        "Tenant",
        tenant_names,
        label_visibility="collapsed",
    )

with col_id:
    selected_tenant = next((t for t in tenants if t["name"] == selected_tenant_name), None)
    tid = selected_tenant.get("id", "") if selected_tenant else ""
    st.caption(f"Tenant ID : {tid}")

audit_runs = get_audit_runs_by_tenant(selected_tenant_name)


# ══════════════════════════════════════════════════════════════════════════════
# 2 · Actions
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-heading">Actions</div>', unsafe_allow_html=True)

col_new, col_hist = st.columns(2)

with col_new:
    st.markdown(
        '<div style="font-size:15px;font-weight:600;color:#111827;margin-bottom:10px">'
        'Nouvel audit</div>',
        unsafe_allow_html=True,
    )
    launch = st.button("Lancer un audit", type="primary", use_container_width=True)
    st.markdown(
        '<div style="font-size:11px;color:#9ca3af;margin-top:6px">'
        'Collecte les données via Microsoft Graph API et génère un rapport complet.'
        '</div>',
        unsafe_allow_html=True,
    )

with col_hist:
    st.markdown(
        '<div style="font-size:15px;font-weight:600;color:#111827;margin-bottom:10px">'
        'Historique des audits</div>',
        unsafe_allow_html=True,
    )
    if audit_runs:
        selected_audit_label = st.selectbox(
            "Audit",
            options=audit_runs,
            format_func=format_audit_label,
            key=f"history_select_{selected_tenant_name}",
            label_visibility="collapsed",
        )
        load_old_audit = st.button("Afficher cet audit", use_container_width=True)
    else:
        st.selectbox(
            "Audit",
            options=["Aucun audit enregistré"],
            disabled=True,
            label_visibility="collapsed",
            key=f"history_empty_{selected_tenant_name}",
        )
        load_old_audit = False
        st.markdown(
            '<div style="font-size:11px;color:#9ca3af;margin-top:6px">'
            "Lancez un premier audit pour alimenter l'historique."
            '</div>',
            unsafe_allow_html=True,
        )

# Messages de retour
if st.session_state.show_success_message:
    st.success(f"Audit terminé avec succès pour {st.session_state.audited_tenant_name}.")
    st.session_state.show_success_message = False


# ─── Logique métier ───────────────────────────────────────────────────────────
if launch:
    if selected_tenant and selected_tenant.get("id"):
        with st.spinner(f"Audit en cours pour {selected_tenant_name}…"):
            report_data = run_and_save_audit(
                selected_tenant["id"],
                selected_tenant["name"],
            )
        if report_data:
            st.session_state.audit_done = True
            st.session_state.current_report = report_data
            st.session_state.audited_tenant_name = selected_tenant_name
            st.session_state.show_success_message = True
            st.rerun()
        else:
            st.error("Une erreur est survenue pendant l'audit. Vérifiez les logs.")
    else:
        st.error("Tenant invalide ou identifiant manquant.")

if load_old_audit and audit_runs:
    report_data = get_audit_report_by_run_id(selected_audit_label["id"])
    if report_data:
        st.session_state.audit_done = True
        st.session_state.current_report = report_data
        st.session_state.audited_tenant_name = selected_tenant_name
        st.success(f"Audit #{selected_audit_label['id']} chargé pour {selected_tenant_name}.")
    else:
        st.error("Impossible de charger cet audit.")


# ══════════════════════════════════════════════════════════════════════════════
# 3 · Résultats
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.audit_done and st.session_state.current_report:
    data = st.session_state.current_report
    displayed_tenant = st.session_state.audited_tenant_name or selected_tenant_name

    findings = data.get("findings", []) if isinstance(data, dict) else data
    summary  = data.get("summary",  {}) if isinstance(data, dict) else {}

    df = pd.DataFrame(findings)
    if not df.empty and "Passed" in df.columns:
        df = df.drop(columns=["Passed"])

    # ── Section heading with date ─────────────────────────────────────────────
    audit_date_str = ""
    if summary.get("audit_date"):
        audit_date_str = (
            "  ·  "
            + summary["audit_date"].replace("T", " ").split(".")[0]
        )
    st.markdown(
        f'<div class="section-heading">Résultats — {displayed_tenant}{audit_date_str}</div>',
        unsafe_allow_html=True,
    )

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    if summary:
        risk_level = summary.get("risk_level", "N/A")
        risk_score = summary.get("risk_score", 0)
        failed     = summary.get("failed_controls", 0)
        total      = summary.get("total_controls", len(findings))
        passed     = total - failed
        bar_color  = risk_bar_color(risk_level)
        score_pct  = min(int(risk_score * 2.5), 100)
        fail_pct   = int((failed / total) * 100) if total else 0

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(f"""
            <div class="kpi-card accent-red">
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
            <div class="kpi-card">
                <div class="kpi-label">Score de risque</div>
                <div class="kpi-value">{risk_score}</div>
                <div class="kpi-sub">points accumulés</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Non conformes</div>
                <div class="kpi-value">{failed}<span
                    style="font-size:17px;color:#d1d5db;font-weight:400"> / {total}</span></div>
                <div class="kpi-sub">{fail_pct}% des contrôles</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Conformes</div>
                <div class="kpi-value">{passed}<span
                    style="font-size:17px;color:#d1d5db;font-weight:400"> / {total}</span></div>
                <div class="kpi-sub">{100 - fail_pct}% des contrôles</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_detail, tab_history = st.tabs(["Détail des contrôles", "Évolution historique"])

    # ── Tab 1 · Tableau HTML (texte complet, pas de troncature) ──────────────
    with tab_detail:
        if not df.empty:
            # Colonnes à afficher dans l'ordre
            display_cols = [c for c in
                ["Control ID", "Category", "Requirement", "Result",
                 "Criticality", "Risk Points", "Affected", "Details"]
                if c in df.columns]

            def _cell_style(col, val):
                if col == "Result":
                    if val == "Fail":
                        return "color:#dc2626;font-weight:700"
                    if val == "Pass":
                        return "color:#16a34a;font-weight:700"
                return ""

            # Construire le HTML
            header_cells = "".join(
                f'<th style="padding:10px 14px;text-align:left;font-size:11px;'
                f'font-weight:700;text-transform:uppercase;letter-spacing:0.8px;'
                f'color:#6b7280;background:#f9fafb;border-bottom:1px solid #e5e7eb;'
                f'white-space:nowrap">{c}</th>'
                for c in display_cols
            )

            rows_html = ""
            for _, row in df[display_cols].iterrows():
                cells = ""
                for col in display_cols:
                    val = row[col] if col in row else ""
                    val_str = "" if (val is None or (isinstance(val, float) and __import__("math").isnan(val))) else str(val)
                    style = _cell_style(col, val_str)
                    cells += (
                        f'<td style="padding:10px 14px;font-size:13px;color:#374151;'
                        f'vertical-align:top;border-bottom:1px solid #f3f4f6;'
                        f'word-break:break-word;{style}">{val_str}</td>'
                    )
                rows_html += f"<tr>{cells}</tr>"

            html_table = f"""
            <div style="overflow-x:auto;border:1px solid #e5e7eb;border-radius:8px;">
              <table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif;background:#fff">
                <thead><tr>{header_cells}</tr></thead>
                <tbody>{rows_html}</tbody>
              </table>
            </div>
            """
            st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.info("Aucun résultat à afficher pour ce tenant.")

    # ── Tab 2 · Graphes d'évolution ───────────────────────────────────────────
    with tab_history:
        history_df = build_history_dataframe(audit_runs)

        if not history_df.empty:
            st.caption(
                f"{len(history_df)} audit(s) enregistré(s) pour {selected_tenant_name}."
            )
            g1, g2 = st.columns(2)

            with g1:
                st.markdown(
                    '<div style="font-size:13px;font-weight:600;color:#111827;margin-bottom:4px">'
                    'Score de risque</div>'
                    '<div style="font-size:11px;color:#9ca3af;margin-bottom:10px">'
                    'Évolution dans le temps</div>',
                    unsafe_allow_html=True,
                )
                st.altair_chart(
                    build_line_chart(history_df, "risk_score", "Score", "#1a56a0"),
                    use_container_width=True,
                )

            with g2:
                st.markdown(
                    '<div style="font-size:13px;font-weight:600;color:#111827;margin-bottom:4px">'
                    'Contrôles non conformes</div>'
                    '<div style="font-size:11px;color:#9ca3af;margin-bottom:10px">'
                    'Évolution dans le temps</div>',
                    unsafe_allow_html=True,
                )
                st.altair_chart(
                    build_line_chart(history_df, "failed_controls", "Non conformes", "#dc2626"),
                    use_container_width=True,
                )


        else:
            st.info(
                "Aucune donnée historique disponible. "
                "Lancez plusieurs audits pour voir l'évolution."
            )

else:
    # ── État vide ─────────────────────────────────────────────────────────────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 52px 40px;
        text-align: center;
    ">
        <div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:6px">
            Aucun audit sélectionné
        </div>
        <div style="font-size:13px;color:#9ca3af;line-height:1.7">
            Sélectionnez un tenant, puis lancez un nouvel audit<br>
            ou chargez un audit existant depuis l'historique.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Graphes accessibles même sans audit actif
    history_df = build_history_dataframe(audit_runs)
    if not history_df.empty:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        with st.expander(f"Évolution historique — {selected_tenant_name}"):
            g1, g2 = st.columns(2)
            with g1:
                st.markdown(
                    '<div style="font-size:13px;font-weight:600;color:#111827;margin-bottom:10px">'
                    'Score de risque</div>',
                    unsafe_allow_html=True,
                )
                st.altair_chart(
                    build_line_chart(history_df, "risk_score", "Score", "#1a56a0"),
                    use_container_width=True,
                )
            with g2:
                st.markdown(
                    '<div style="font-size:13px;font-weight:600;color:#111827;margin-bottom:10px">'
                    'Contrôles non conformes</div>',
                    unsafe_allow_html=True,
                )
                st.altair_chart(
                    build_line_chart(history_df, "failed_controls", "Non conformes", "#dc2626"),
                    use_container_width=True,
                )