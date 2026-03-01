import requests


def fetch_raw_roles(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    results = {
        "role_definitions": [],
        "active_assignments": [],
        "eligible_assignments": [],
        "pim_policies": [],
        "policy_assignments": [],
    }

    try:
        # 1) Définitions des rôles
        url_defs = "https://graph.microsoft.com/v1.0/roleManagement/directory/roleDefinitions"
        resp = requests.get(url_defs, headers=headers)
        if resp.status_code == 200:
            results["role_definitions"] = resp.json().get("value", [])
        else:
            print("DEBUG role_definitions status:", resp.status_code)
            print("DEBUG role_definitions body:", resp.text)

        # 2) Assignations permanentes (Directory roles + members)
        url_active = "https://graph.microsoft.com/v1.0/directoryRoles?$expand=members"
        resp = requests.get(url_active, headers=headers)
        if resp.status_code == 200:
            results["active_assignments"] = resp.json().get("value", [])
        else:
            print("DEBUG active_assignments status:", resp.status_code)
            print("DEBUG active_assignments body:", resp.text)

        # 3) Assignations éligibles (PIM)
        url_eligible = "https://graph.microsoft.com/v1.0/roleManagement/directory/roleEligibilitySchedules?$expand=principal"
        resp = requests.get(url_eligible, headers=headers)
        if resp.status_code == 200:
            results["eligible_assignments"] = resp.json().get("value", [])
        else:
            print("DEBUG eligible_assignments status:", resp.status_code)
            print("DEBUG eligible_assignments body:", resp.text)

        # 4) Politiques PIM + rules
        url_policies = (
            "https://graph.microsoft.com/v1.0/policies/roleManagementPolicies"
            "?$filter=scopeId eq '/' and scopeType eq 'Directory'&$expand=rules"
        )
        resp = requests.get(url_policies, headers=headers)
        if resp.status_code == 200:
            results["pim_policies"] = resp.json().get("value", [])
            print(f"DEBUG: {len(results['pim_policies'])} politiques récupérées.")
        else:
            print("DEBUG policies status:", resp.status_code)
            print("DEBUG policies body:", resp.text)

        # Fallback si besoin (tu peux le garder)
        if not results["pim_policies"]:
            url_fallback = "https://graph.microsoft.com/v1.0/roleManagement/directory/roleManagementPolicies?$expand=rules"
            resp_fb = requests.get(url_fallback, headers=headers)
            if resp_fb.status_code == 200:
                results["pim_policies"] = resp_fb.json().get("value", [])
                print("DEBUG: Récupération via fallback réussie.")
            else:
                print("DEBUG fallback policies status:", resp_fb.status_code)
                print("DEBUG fallback policies body:", resp_fb.text)

        # 5) Assignments (lien entre roleDefinitionId et policyId)
        url_assign = (
            "https://graph.microsoft.com/v1.0/policies/roleManagementPolicyAssignments"
            "?$filter=scopeId eq '/' and scopeType eq 'Directory'"
        )
        resp_a = requests.get(url_assign, headers=headers)
        if resp_a.status_code == 200:
            results["policy_assignments"] = resp_a.json().get("value", [])
            print(f"DEBUG: {len(results['policy_assignments'])} assignments récupérés.")
        else:
            print("DEBUG assignments status:", resp_a.status_code)
            print("DEBUG assignments body:", resp_a.text)

    except Exception as e:
        print(f"Erreur Collector : {e}")

    return results