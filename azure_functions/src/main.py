import json
from datetime import datetime, timezone

from src.auth import get_token
from src.collectors.roles_collector import fetch_raw_roles
from src.collectors.auth_collector import fetch_raw_auth
from src.collectors.activity_collector import fetch_raw_activity

from src.audits.audit_roles import audit_roles
from src.audits.audit_mfa import audit_mfa
from src.audits.audit_inactivity import audit_inactivity

from src.tenants import get_all_tenants
from src.storage.fs_store import save_json
from src.config import RAW_DATA_PATH
from src.engine.severity import classify_risk
from src.storage.db_store import init_db, save_audit_to_db

REPORTS_PATH = "data/reports"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_baseline():
    with open("baseline/baseline.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _build_report(tenant_id, tenant_name, audit_results, execution_mode):
    risk_score = sum(r.get("Risk Points", 0) for r in audit_results)
    risk_level = classify_risk(int(risk_score))
    failed_controls = sum(1 for r in audit_results if not r.get("Passed", True))
    total_controls = len(audit_results)

    report = {
        "tenant": tenant_name,
        "tenant_id": tenant_id,
        "execution_mode": execution_mode,
        "summary": {
            "audit_date": _utc_now_iso(),
            "risk_score": int(risk_score),
            "risk_level": risk_level,
            "failed_controls": int(failed_controls),
            "total_controls": int(total_controls),
        },
        "findings": audit_results,
    }

    return report


def run_audit_workflow(tenant_id, tenant_name, execution_mode="local"):
    """
    Exécute le workflow complet d'audit pour un tenant.

    Modes disponibles :
    - local : sauvegarde des données brutes, rapport JSON local et possibilité de stockage SQLite
    - cloud : aucun stockage local ; le rapport est seulement retourné à l'appelant
    """
    print(f"--- Audit pour {tenant_name} | mode={execution_mode} ---")

    if execution_mode not in ["local", "cloud"]:
        raise ValueError("execution_mode doit être 'local' ou 'cloud'")

    try:
        token = get_token(tenant_id)

        # 1) Collecte des données
        raw_roles = fetch_raw_roles(token)
        raw_auth = fetch_raw_auth(token)
        raw_activity = fetch_raw_activity(token)

        # 2) Sauvegarde des données brutes uniquement en mode local
        if execution_mode == "local":
            save_json(RAW_DATA_PATH, f"{tenant_name}_roles_raw", raw_roles)
            save_json(RAW_DATA_PATH, f"{tenant_name}_auth_raw", raw_auth)
            save_json(RAW_DATA_PATH, f"{tenant_name}_activity_raw", raw_activity)

        # 3) Chargement de la baseline
        baseline = _load_baseline()

        # 4) Exécution des audits
        roles_results = audit_roles(raw_roles, baseline)
        mfa_results = audit_mfa(raw_auth, raw_roles, baseline)
        inactivity_results = audit_inactivity(raw_activity, raw_roles, baseline)

        audit_results = roles_results + mfa_results + inactivity_results

        # 5) Construction du rapport
        report = _build_report(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            audit_results=audit_results,
            execution_mode=execution_mode,
        )

        # 6) Sauvegarde du rapport uniquement en mode local
        if execution_mode == "local":
            save_json(REPORTS_PATH, f"{tenant_name}_audit_report", report)

        print(f"Rapport généré : {len(audit_results)} contrôles effectués.\n")
        return report

    except Exception as e:
        print(f"Erreur sur {tenant_name} : {str(e)}")
        return None


def run_and_save_audit(tenant_id, tenant_name):
    """
    Utilisé par l'interface Streamlit.
    Exécute l'audit en mode local puis sauvegarde le résultat dans SQLite.
    """
    report = run_audit_workflow(tenant_id, tenant_name, execution_mode="local")

    if report:
        save_audit_to_db(tenant_id, tenant_name, report)

    return report


def run_cloud_audit(tenant_id, tenant_name):
    """
    Utilisé par Azure Function.
    Exécute l'audit en mode cloud sans écriture locale ni SQLite.
    """
    return run_audit_workflow(tenant_id, tenant_name, execution_mode="cloud")


if __name__ == "__main__":
    init_db()
    print("Base SQLite initialisée.")

    tenants = get_all_tenants()
    print(f"{len(tenants)} tenant(s) détecté(s). Début du scan...\n")

    for t in tenants:
        if t.get("id"):
            report = run_audit_workflow(t["id"], t["name"], execution_mode="local")

            if report:
                save_audit_to_db(t["id"], t["name"], report)
        else:
            print(f"Saut de {t['name']} : ID manquant.")

    print("Opération terminée.")