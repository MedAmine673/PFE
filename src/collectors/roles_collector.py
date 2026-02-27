import requests

def fetch_raw_roles(token):
    headers = {'Authorization': f'Bearer {token}'}
    results = {}

    # 3.1 : Rôles Actifs (Permanents)
    url_active = "https://graph.microsoft.com/v1.0/directoryRoles?$expand=members"
    resp_active = requests.get(url_active, headers=headers)
    results['active_assignments'] = resp_active.json().get('value', [])

    # 3.3 : Rôles Éligibles (PIM)
    url_eligible = "https://graph.microsoft.com/v1.0/roleManagement/directory/roleEligibilitySchedules"
    resp_eligible = requests.get(url_eligible, headers=headers)
    results['eligible_assignments'] = resp_eligible.json().get('value', [])

    return results