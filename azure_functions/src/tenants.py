import json
from src.config import TENANTS_FILE

def get_all_tenants():
    try:
        with open(TENANTS_FILE, "r", encoding="utf-8") as f:
            tenants = json.load(f)

        return [
            {
                "id": t["id"],
                "name": t.get("name", "Tenant")
            }
            for t in tenants if t.get("id")
        ]

    except Exception:
        return []