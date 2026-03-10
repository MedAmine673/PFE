from datetime import datetime, timezone
from src.engine.findings import create_finding
from src.engine.compare import is_empty


def audit_inactivity(activity_data, roles_data, baseline):
    audit_results = []

    config = baseline.get("activity_audit", {})
    max_inactivity_days = config.get("max_inactivity_days", 90)
    alert_on_never_logged_in = config.get("alert_on_never_logged_in", True)

    users_signin_activity = activity_data.get("users_signin_activity", [])
    active_assignments = roles_data.get("active_assignments", [])
    eligible_assignments = roles_data.get("eligible_assignments", [])
    role_definitions = roles_data.get("role_definitions", [])

    critical_roles = baseline.get("roles_audit", {}).get("critical_roles", [])

    # Mapping role name -> roleDefinitionId
    name_to_role_id = {
        rd.get("displayName"): rd.get("id")
        for rd in role_definitions
        if rd.get("displayName") and rd.get("id")
    }

    # 1) Construire la liste des admins
    admin_users = {}

    # Admins actifs
    for role in active_assignments:
        role_name = role.get("displayName")
        if role_name in critical_roles:
            for member in role.get("members", []):
                user_key = member.get("userPrincipalName") or member.get("id")
                if user_key:
                    key = str(user_key).lower()
                    admin_users[key] = {
                        "displayName": member.get("displayName", "Inconnu"),
                        "userPrincipalName": member.get("userPrincipalName", "Inconnu"),
                        "roles": admin_users.get(key, {}).get("roles", []) + [role_name],
                    }

    # Admins éligibles
    critical_role_ids = {
        name_to_role_id.get(role_name)
        for role_name in critical_roles
        if name_to_role_id.get(role_name)
    }

    for item in eligible_assignments:
        if item.get("roleDefinitionId") in critical_role_ids:
            principal = item.get("principal", {})
            user_key = (
                principal.get("userPrincipalName")
                or principal.get("id")
                or item.get("principalId")
            )

            if user_key:
                key = str(user_key).lower()
                role_name = next(
                    (
                        name
                        for name, rid in name_to_role_id.items()
                        if rid == item.get("roleDefinitionId")
                    ),
                    "Rôle critique",
                )

                existing_roles = admin_users.get(key, {}).get("roles", [])
                admin_users[key] = {
                    "displayName": principal.get("displayName", "Inconnu"),
                    "userPrincipalName": principal.get("userPrincipalName", str(user_key)),
                    "roles": existing_roles + [role_name],
                }

    # 2) Construire le dictionnaire activité
    activity_by_upn = {}
    activity_by_id = {}

    for user in users_signin_activity:
        upn = user.get("userPrincipalName")
        user_id = user.get("id")

        if upn:
            activity_by_upn[upn.lower()] = user
        if user_id:
            activity_by_id[user_id.lower()] = user

    # 3) AAD-09 : administrateur inactif > N jours
    inactive_admins = []
    now = datetime.now(timezone.utc)

    # 4) AAD-10 : compte sans historique de connexion
    never_logged_in_admins = []

    for key, admin in admin_users.items():
        upn = (admin.get("userPrincipalName") or "").lower()
        user_activity = activity_by_upn.get(upn)

        if not user_activity:
            user_activity = activity_by_id.get(key)

        # Si aucune donnée activité trouvée
        if not user_activity:
            if alert_on_never_logged_in:
                never_logged_in_admins.append(
                    f"{admin.get('displayName')} ({admin.get('userPrincipalName')})"
                )
            continue

        sign_in_activity = user_activity.get("signInActivity", {}) or {}
        last_signin = sign_in_activity.get("lastSignInDateTime")

        # Cas jamais connecté / pas d'historique
        if not last_signin:
            if alert_on_never_logged_in:
                never_logged_in_admins.append(
                    f"{admin.get('displayName')} ({admin.get('userPrincipalName')})"
                )
            continue

        # Cas inactif
        try:
            last_signin_dt = datetime.fromisoformat(last_signin.replace("Z", "+00:00"))
            inactivity_days = (now - last_signin_dt).days

            if inactivity_days > max_inactivity_days:
                inactive_admins.append(
                    f"{admin.get('displayName')} ({admin.get('userPrincipalName')}) - {inactivity_days} jours"
                )
        except Exception:
            if alert_on_never_logged_in:
                never_logged_in_admins.append(
                    f"{admin.get('displayName')} ({admin.get('userPrincipalName')})"
                )

    # AAD-09
    is_inactivity_ok = is_empty(inactive_admins)

    details_aad09 = (
        "Conforme"
        if is_inactivity_ok
        else f"Administrateurs inactifs : {', '.join(inactive_admins)}"
    )

    audit_results.append(
        create_finding(
            "AAD-09",
            "Activity",
            f"Administrateur inactif depuis plus de {max_inactivity_days} jours",
            is_inactivity_ok,
            int(len(inactive_admins)),
            details_aad09,
        )
    )

    # AAD-10
    if alert_on_never_logged_in:
        is_never_login_ok = is_empty(never_logged_in_admins)

        details_aad10 = (
            "Conforme"
            if is_never_login_ok
            else f"Comptes sans historique de connexion : {', '.join(never_logged_in_admins)}"
        )

        audit_results.append(
            create_finding(
                "AAD-10",
                "Activity",
                "Compte administrateur sans historique de connexion",
                is_never_login_ok,
                int(len(never_logged_in_admins)),
                details_aad10,
            )
        )

    return audit_results