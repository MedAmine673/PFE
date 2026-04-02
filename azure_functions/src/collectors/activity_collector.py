import requests


def fetch_raw_activity(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    results = {
        "users_signin_activity": [],
    }

    try:
        url = (
            "https://graph.microsoft.com/v1.0/users"
            "?$select=id,displayName,userPrincipalName,signInActivity"
        )

        while url:
            resp = requests.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                results["users_signin_activity"].extend(data.get("value", []))
                url = data.get("@odata.nextLink")
            else:
                print("DEBUG users_signin_activity status:", resp.status_code)
                print("DEBUG users_signin_activity body:", resp.text)
                break

    except Exception as e:
        print(f"Erreur Activity Collector : {e}")

    return results