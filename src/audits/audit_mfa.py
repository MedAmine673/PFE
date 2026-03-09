from src.engine.findings import create_finding
from src.engine.compare import is_empty


def audit_mfa(auth_data, roles_data, baseline):
    audit_results = []

    config = baseline.get("mfa_audit", {})
    require_mfa_for_admins = config.get("require_mfa_for_admins", True)
    check_conditional_access = config.get("check_conditional_access", True)
    allowed_mfa_methods = config.get("allowed_mfa_methods", [])

    registration_details = auth_data.get("user_registration_details", [])
    conditional_access_policies = auth_data.get("conditional_access_policies", [])

    active_assignments = roles_data.get("active_assignments", [])
    eligible_assignments = roles_data.get("eligible_assignments", [])
    role_definitions = roles_data.get("role_definitions", [])

    critical_roles = baseline.get("roles_audit", {}).get("critical_roles", [])

    # ==========================================================
    # Préparation : liste des admins à partir des rôles critiques
    # ==========================================================
    name_to_role_id = {
        rd.get("displayName"): rd.get("id")
        for rd in role_definitions
        if rd.get("displayName") and rd.get("id")
    }

    admin_users = {}

    # Admins actifs
    for role in active_assignments:
        role_name = role.get("displayName")
        if role_name in critical_roles:
            for member in role.get("members", []):
                user_key = member.get("userPrincipalName") or member.get("displayName")
                if user_key:
                    admin_users[user_key] = {
                        "displayName": member.get("displayName", "Inconnu"),
                        "userPrincipalName": member.get("userPrincipalName", user_key),
                        "roles": admin_users.get(user_key, {}).get("roles", []) + [role_name],
                    }

    # Admins éligibles
    critical_role_ids = {name_to_role_id.get(r) for r in critical_roles if name_to_role_id.get(r)}

    for item in eligible_assignments:
        if item.get("roleDefinitionId") in critical_role_ids:
            principal = item.get("principal", {})
            user_key = principal.get("userPrincipalName") or principal.get("displayName") or item.get("principalId")
            if user_key:
                role_name = next(
                    (name for name, rid in name_to_role_id.items() if rid == item.get("roleDefinitionId")),
                    "Rôle critique"
                )
                existing_roles = admin_users.get(user_key, {}).get("roles", [])
                admin_users[user_key] = {
                    "displayName": principal.get("displayName", "Inconnu"),
                    "userPrincipalName": principal.get("userPrincipalName", user_key),
                    "roles": existing_roles + [role_name],
                }

    # Dictionnaire MFA par userPrincipalName
    reg_by_upn = {}
    for user in registration_details:
        upn = user.get("userPrincipalName")
        if upn:
            reg_by_upn[upn.lower()] = user

    # ==========================================================
    # AAD-07 : Chaque administrateur est protégé par MFA
    # ==========================================================
    admins_without_mfa = []

    if require_mfa_for_admins:
        for _, admin in admin_users.items():
            upn = (admin.get("userPrincipalName") or "").lower()
            reg = reg_by_upn.get(upn)

            if not reg:
                admins_without_mfa.append(
                    f"{admin.get('displayName')} ({admin.get('userPrincipalName')})"
                )
                continue

            is_mfa_registered = reg.get("isMfaRegistered", False)
            methods_registered = reg.get("methodsRegistered", []) or []

            # Contrôle simple :
            # - MFA enregistré
            # - et si baseline contient des méthodes autorisées, au moins une méthode compatible
            has_allowed_method = True
            if allowed_mfa_methods:
                methods_lower = [m.lower() for m in methods_registered]
                has_allowed_method = any(m.lower() in methods_lower for m in allowed_mfa_methods)

            if not is_mfa_registered or not has_allowed_method:
                admins_without_mfa.append(
                    f"{admin.get('displayName')} ({admin.get('userPrincipalName')})"
                )

    is_mfa_admins_ok = is_empty(admins_without_mfa)

    details_mfa_admins = (
        "Conforme"
        if is_mfa_admins_ok
        else f"Administrateurs sans MFA : {', '.join(admins_without_mfa)}"
    )

    audit_results.append(
        create_finding(
            "AAD-07",
            "MFA",
            "Chaque administrateur est protégé par MFA",
            is_mfa_admins_ok,
            int(len(admins_without_mfa)),
            details_mfa_admins,
        )
    )

    # ==========================================================
    # AAD-08 : Existence d'une politique Conditional Access dédiée aux administrateurs
    # ==========================================================
    ca_policy_found = False

    if check_conditional_access:
        for policy in conditional_access_policies:
            state = policy.get("state", "")
            conditions = policy.get("conditions", {}) or {}
            users = conditions.get("users", {}) or {}

            # Heuristique simple:
            # - policy active
            # - et cible des rôles du répertoire
            include_roles = users.get("includeRoles", []) or []

            if state in ["enabled", "enabledForReportingButNotEnforced"] and len(include_roles) > 0:
                ca_policy_found = True
                break

    details_ca = (
        "Conforme"
        if ca_policy_found
        else "Échec : aucune politique Conditional Access dédiée aux administrateurs n'a été trouvée"
    )

    audit_results.append(
        create_finding(
            "AAD-08",
            "Conditional Access",
            "Une politique Conditional Access dédiée aux administrateurs existe",
            ca_policy_found,
            0 if ca_policy_found else 1,
            details_ca,
        )
    )

    return audit_results