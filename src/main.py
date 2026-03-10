import json
from src.auth import get_token
from src.collectors.roles_collector import fetch_raw_roles
from src.collectors.auth_collector import fetch_raw_auth
from src.audits.audit_roles import audit_roles
from src.audits.audit_mfa import audit_mfa
from src.collectors.activity_collector import fetch_raw_activity
from src.audits.audit_inactivity import audit_inactivity
from src.tenants import get_all_tenants
from src.storage.fs_store import save_json
from src.config import RAW_DATA_PATH
from src.engine.severity import classify_risk

REPORTS_PATH = "data/reports"


def run_audit_workflow(tenant_id, tenant_name):
    print(f"--- Audit pour {tenant_name} ---")
    try:
        token = get_token(tenant_id)

        # 1) Collecte des données rôles
        raw_roles = fetch_raw_roles(token)
        save_json(RAW_DATA_PATH, f"{tenant_name}_roles_raw", raw_roles)

        # 2) Collecte des données MFA / Conditional Access
        raw_auth = fetch_raw_auth(token)
        save_json(RAW_DATA_PATH, f"{tenant_name}_auth_raw", raw_auth)

        # 3) Collecte des données d'activité / connexions
        raw_activity = fetch_raw_activity(token)
        save_json(RAW_DATA_PATH, f"{tenant_name}_activity_raw", raw_activity)

        # 4) Chargement de la baseline
        with open("baseline/baseline.json", "r", encoding="utf-8") as f:
            baseline = json.load(f)

        # 5) Exécution des audits
        roles_results = audit_roles(raw_roles, baseline)
        mfa_results = audit_mfa(raw_auth, raw_roles, baseline)
        inactivity_results = audit_inactivity(raw_activity, raw_roles, baseline)

        audit_results = roles_results + mfa_results + inactivity_results

        # 5) Classification des risques
        risk_score = sum(r.get("Risk Points", 0) for r in audit_results)
        risk_level = classify_risk(int(risk_score))
        failed_controls = sum(1 for r in audit_results if not r.get("Passed", True))
        total_controls = len(audit_results)

        report = {
            "tenant": tenant_name,
            "summary": {
                "risk_score": int(risk_score),
                "risk_level": risk_level,
                "failed_controls": int(failed_controls),
                "total_controls": int(total_controls),
            },
            "findings": audit_results,
        }

        # 6) Sauvegarde du rapport final
        save_json(REPORTS_PATH, f"{tenant_name}_audit_report", report)
        print(f" Rapport généré : {len(audit_results)} contrôles effectués.\n")

        return report

    except Exception as e:
        print(f"Erreur sur {tenant_name} : {str(e)}")
        return None


if __name__ == "__main__":
    tenants = get_all_tenants()
    print(f" {len(tenants)} tenant(s) détecté(s). Début du scan...\n")

    for t in tenants:
        if t["id"]:
            run_audit_workflow(t["id"], t["name"])
        else:
            print(f" Saut de {t['name']} : ID manquant.")

    print(" Opération terminée.")