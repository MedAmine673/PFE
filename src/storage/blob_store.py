import json
from azure.storage.blob import BlobServiceClient

from src.config import AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER


def _get_container_client():
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING n'est pas configurée.")

    blob_service_client = BlobServiceClient.from_connection_string(
        AZURE_STORAGE_CONNECTION_STRING
    )

    return blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER)


def list_blob_reports(tenant_name=None):
    """
    Liste les rapports JSON stockés dans Azure Blob Storage.
    Si tenant_name est fourni, on filtre les rapports du tenant sélectionné.
    """
    container_client = _get_container_client()

    prefix = None
    if tenant_name:
        safe_tenant = (
            tenant_name.strip()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
        )
        prefix = f"{safe_tenant}/"

    blobs = container_client.list_blobs(name_starts_with=prefix)

    reports = []
    for blob in blobs:
        if blob.name.endswith(".json"):
            reports.append({
                "name": blob.name,
                "last_modified": blob.last_modified,
                "size": blob.size,
            })

    reports.sort(key=lambda x: x["last_modified"], reverse=True)
    return reports


def load_blob_report(blob_name):
    """
    Télécharge un rapport JSON depuis Azure Blob Storage.
    """
    container_client = _get_container_client()
    blob_client = container_client.get_blob_client(blob_name)

    content = blob_client.download_blob().readall()
    return json.loads(content.decode("utf-8"))