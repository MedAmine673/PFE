import json
from src.config import TENANTS_FILE, AZ_TENANT_ID


def get_all_tenants():
    try:
        with open(TENANTS_FILE, "r", encoding="utf-8") as f:
            tenants = json.load(f)

        valid_tenants = []
        for t in tenants:
            tenant_id = t.get("id")
            tenant_name = t.get("name", "Tenant_Sans_Nom")

            if tenant_id:
                valid_tenants.append({
                    "id": tenant_id,
                    "name": tenant_name
                })

        return valid_tenants

    except FileNotFoundError:
        return [
            {
                "id": AZ_TENANT_ID,
                "name": "Tenant_01"
            }
        ]