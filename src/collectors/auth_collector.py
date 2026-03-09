import requests


def fetch_raw_auth(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    results = {
        "user_registration_details": [],
        "conditional_access_policies": [],
    }

    try:
        # 1) Détails MFA / méthodes enregistrées des utilisateurs
        url_reg = "https://graph.microsoft.com/v1.0/reports/authenticationMethods/userRegistrationDetails"
        resp = requests.get(url_reg, headers=headers)
        if resp.status_code == 200:
            results["user_registration_details"] = resp.json().get("value", [])
        else:
            print("DEBUG user_registration_details status:", resp.status_code)
            print("DEBUG user_registration_details body:", resp.text)

        # 2) Politiques Conditional Access
        url_ca = "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies"
        resp = requests.get(url_ca, headers=headers)
        if resp.status_code == 200:
            results["conditional_access_policies"] = resp.json().get("value", [])
        else:
            print("DEBUG conditional_access_policies status:", resp.status_code)
            print("DEBUG conditional_access_policies body:", resp.text)

    except Exception as e:
        print(f"Erreur Auth Collector : {e}")

    return results