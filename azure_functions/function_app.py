import os
import sys
import json
import logging
from datetime import datetime, timezone

import requests
import azure.functions as func
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

PROJECT_ROOT = os.path.dirname(__file__)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

IMPORT_ERROR = None
get_all_tenants = None
run_cloud_audit = None

try:
    from src.tenants import get_all_tenants
    from src.main import run_cloud_audit
except Exception as e:
    IMPORT_ERROR = str(e)
    logging.exception("Erreur import modules src: %s", str(e))


def get_env_var(name: str, required: bool = True, default: str = None) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Variable d'environnement manquante : {name}")
    return value


def sanitize_name(value: str) -> str:
    return (
        value.strip()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def build_blob_name(tenant_name: str, audit_date: str) -> str:
    safe_tenant = sanitize_name(tenant_name)
    dt = datetime.fromisoformat(audit_date.replace("Z", "+00:00"))

    return (
        f"{safe_tenant}/"
        f"{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/"
        f"{safe_tenant}_audit_{audit_date.replace(':', '-')}.json"
    )


def upload_report_to_blob(report: dict, tenant_name: str) -> str:
    connection_string = get_env_var("AZURE_STORAGE_CONNECTION_STRING")
    container_name = get_env_var("AZURE_STORAGE_CONTAINER", default="audit-reports")

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    try:
        container_client.create_container()
        logging.info("Conteneur Blob créé : %s", container_name)
    except Exception:
        logging.info("Conteneur Blob déjà existant ou déjà disponible : %s", container_name)

    audit_date = report.get("summary", {}).get("audit_date")
    if not audit_date:
        audit_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        report.setdefault("summary", {})["audit_date"] = audit_date

    blob_name = build_blob_name(tenant_name, audit_date)
    blob_client = container_client.get_blob_client(blob_name)

    payload = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    blob_client.upload_blob(payload, overwrite=True)

    logging.info("Rapport stocké dans Blob Storage : %s/%s", container_name, blob_name)
    return blob_name


def should_trigger_alert(report: dict) -> bool:
    summary = report.get("summary", {})
    findings = report.get("findings", [])

    risk_level = str(summary.get("risk_level", "")).strip().lower()

    if risk_level in ["élevé", "eleve", "critique"]:
        return True

    for finding in findings:
        result_value = str(finding.get("Result", "")).strip().lower()
        passed_value = finding.get("Passed", None)
        criticality = str(finding.get("Criticality", "")).strip().lower()

        failed = (result_value == "fail") or (passed_value is False)

        if failed and criticality in ["critical", "critique"]:
            return True

    return False


def send_notification_log(tenant_name: str, report: dict, blob_name: str) -> None:
    summary = report.get("summary", {})

    logging.warning(
        (
            "ALERTE AUDIT | tenant=%s | niveau=%s | score=%s | "
            "non_conformes=%s/%s | blob=%s"
        ),
        tenant_name,
        summary.get("risk_level", "N/A"),
        summary.get("risk_score", 0),
        summary.get("failed_controls", 0),
        summary.get("total_controls", 0),
        blob_name,
    )


def build_teams_message_card(tenant_name: str, report: dict, blob_name: str) -> dict:
    summary = report.get("summary", {})
    risk_level = summary.get("risk_level", "N/A")
    risk_score = summary.get("risk_score", 0)
    failed_controls = summary.get("failed_controls", 0)
    total_controls = summary.get("total_controls", 0)
    audit_date = summary.get("audit_date", "N/A")

    color_map = {
        "Faible": "2EB886",
        "Modéré": "D4A72C",
        "Élevé": "E67E22",
        "Critique": "C0392B"
    }
    theme_color = color_map.get(risk_level, "0078D4")

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": f"Alerte audit Microsoft 365 - {tenant_name}",
        "themeColor": theme_color,
        "title": "Alerte de sécurité Microsoft 365",
        "sections": [
            {
                "activityTitle": f"Tenant : {tenant_name}",
                "activitySubtitle": "Résultat d'un audit automatisé Azure Function",
                "facts": [
                    {"name": "Niveau de risque", "value": str(risk_level)},
                    {"name": "Score de risque", "value": str(risk_score)},
                    {"name": "Contrôles non conformes", "value": f"{failed_controls}/{total_controls}"},
                    {"name": "Date d'audit", "value": str(audit_date)},
                    {"name": "Rapport Blob", "value": str(blob_name)},
                ],
                "markdown": True,
                "text": (
                    "Une alerte a été déclenchée car le niveau de risque est élevé "
                    "ou critique, ou parce qu'un contrôle critique est en échec."
                ),
            }
        ]
    }


def send_teams_notification(tenant_name: str, report: dict, blob_name: str) -> bool:
    webhook_url = os.getenv("TEAMS_WEBHOOK_URL")

    if not webhook_url:
        logging.warning("Webhook Teams non configuré. Notification ignorée.")
        return False

    summary = report.get("summary", {})

    risk_level = summary.get("risk_level", "N/A")
    risk_score = summary.get("risk_score", 0)
    failed_controls = summary.get("failed_controls", 0)
    total_controls = summary.get("total_controls", 0)
    audit_date = summary.get("audit_date", "N/A")

    # Couleur selon le niveau de risque
    color_map = {
        "Faible": "2EB886",
        "Modéré": "D4A72C",
        "Élevé": "E67E22",
        "Critique": "C0392B"
    }
    theme_color = color_map.get(risk_level, "0078D4")

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": f"Alerte audit Microsoft 365 - {tenant_name}",
        "themeColor": theme_color,
        "title": " Alerte de sécurité Microsoft 365",
        "sections": [
            {
                "activityTitle": f" Tenant : **{tenant_name}**",
                "activitySubtitle": "Résultat d’un audit automatisé Azure Function",
                "facts": [
                    {"name": "Niveau de risque", "value": str(risk_level)},
                    {"name": "Score de risque", "value": str(risk_score)},
                    {"name": "Contrôles non conformes", "value": f"{failed_controls}/{total_controls}"},
                    {"name": "Date d’audit", "value": str(audit_date)},
                ],
                "markdown": True,
                "text": (
                    " Une alerte a été déclenchée car le niveau de risque est **élevé ou critique**, "
                    "ou parce qu’un contrôle critique est en échec.\n\n"
                    f" Rapport disponible dans le Blob Storage : `{blob_name}`"
                ),
            }
        ]
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )

        if 200 <= response.status_code < 300:
            logging.info("Notification Teams envoyée avec succès pour %s", tenant_name)
            return True

        logging.error(
            "Échec envoi Teams | tenant=%s | status=%s | body=%s",
            tenant_name,
            response.status_code,
            response.text
        )
        return False

    except Exception as e:
        logging.exception(
            "Erreur pendant l'envoi de la notification Teams pour %s : %s",
            tenant_name,
            str(e)
        )
        return False

def enrich_report_metadata(report: dict, tenant_id: str, tenant_name: str) -> dict:
    if report is None:
        return None

    report["tenant"] = tenant_name
    report["tenant_id"] = tenant_id
    report["generated_by"] = "azure_function"
    report["execution_context"] = "scheduled_timer_trigger"

    return report


@app.function_name(name="audit_timer_function")
@app.schedule(
    schedule="0 0 7 * * *",
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True
)

def audit_timer_function(mytimer: func.TimerRequest) -> None:
    logging.info(
        "Début exécution Azure Function | date=%s",
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    if mytimer.past_due:
        logging.warning("Le déclenchement planifié est en retard.")

    if IMPORT_ERROR:
        logging.error("Impossible de charger les modules du projet : %s", IMPORT_ERROR)
        return

    logging.info("Imports OK")

    try:
        tenants = get_all_tenants()
        logging.info("Tenants chargés : %s", len(tenants))
    except Exception as e:
        logging.exception("Erreur chargement tenants : %s", str(e))
        return

    if not tenants:
        logging.warning("Aucun tenant trouvé. Fin de l'exécution.")
        return

    success_count = 0
    error_count = 0
    alert_count = 0
    teams_sent_count = 0

    for tenant in tenants:
        tenant_id = tenant.get("id")
        tenant_name = tenant.get("name", "unknown_tenant")

        if not tenant_id:
            logging.warning("Tenant ignoré : %s | ID manquant", tenant_name)
            continue

        logging.info("----- Début audit tenant : %s -----", tenant_name)

        try:
            report = run_cloud_audit(tenant_id, tenant_name)

            if not report:
                logging.error("Aucun rapport généré pour le tenant : %s", tenant_name)
                error_count += 1
                continue

            report = enrich_report_metadata(report, tenant_id, tenant_name)

            blob_name = upload_report_to_blob(report, tenant_name)

            if should_trigger_alert(report):
                send_notification_log(tenant_name, report, blob_name)

                teams_sent = send_teams_notification(tenant_name, report, blob_name)
                if teams_sent:
                    teams_sent_count += 1

                alert_count += 1
                logging.info("Alerte déclenchée pour le tenant : %s", tenant_name)
            else:
                logging.info("Aucune alerte nécessaire pour le tenant : %s", tenant_name)

            success_count += 1
            logging.info("Audit terminé avec succès pour : %s", tenant_name)

        except Exception as e:
            error_count += 1
            logging.exception(
                "Erreur pendant l'audit du tenant %s : %s",
                tenant_name,
                str(e)
            )

        logging.info("----- Fin audit tenant : %s -----", tenant_name)

    logging.info(
        "Fin de l'exécution automatisée | succès=%s | erreurs=%s | alertes=%s | notifications_teams=%s",
        success_count,
        error_count,
        alert_count,
        teams_sent_count
    )
