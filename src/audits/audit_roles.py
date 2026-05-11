import re
from src.engine.findings import create_finding
from src.engine.compare import is_empty, is_within_range


def audit_roles(raw_data, baseline):
    audit_results = []

    active = raw_data.get("active_assignments", [])
    eligible = raw_data.get("eligible_assignments", [])
    policies = raw_data.get("pim_policies", [])
    assignments = raw_data.get("policy_assignments", [])
    role_defs = raw_data.get("role_definitions", [])

    aad01 = baseline.get("AAD-01", {})
    aad02 = baseline.get("AAD-02", {})
    aad03 = baseline.get("AAD-03", {})
    aad04 = baseline.get("AAD-04", {})
    aad05 = baseline.get("AAD-05", {})
    aad06 = baseline.get("AAD-06", {})

    critical_roles = aad02.get("critical_roles", [])
    name_to_id = {
        rd.get("displayName"): rd.get("id")
        for rd in role_defs
        if rd.get("displayName") and rd.get("id")
    }

    def get_role_id(role_name: str):
        return name_to_id.get(role_name)

    def get_rules_for_role(role_def_id: str):
        assignment = next(
            (x for x in assignments if x.get("roleDefinitionId") == role_def_id),
            None
        )
        if not assignment:
            return None, [], "no_assignment"

        policy_id = assignment.get("policyId")
        policy = next((p for p in policies if p.get("id") == policy_id), None)
        if not policy:
            return policy_id, [], "no_policy"

        return policy_id, policy.get("rules", []), "ok"

    def find_rule(rules_list, odata_contains: str, ids):
        return next(
            (
                r for r in rules_list
                if odata_contains in r.get("@odata.type", "")
                and r.get("id", "") in ids
            ),
            None
        )

    # AAD-01
    if aad01.get("enabled", True):
        target_role = "Global Administrator"
        target_role_id = get_role_id(target_role)

        active_names = []
        for role in [r for r in active if r.get("displayName") == target_role]:
            active_names.extend([
                m.get("displayName", m.get("userPrincipalName", "Inconnu"))
                for m in role.get("members", [])
            ])

        eligible_names = []
        for item in [e for e in eligible if target_role_id and e.get("roleDefinitionId") == target_role_id]:
            principal = item.get("principal", {})
            name = (
                principal.get("displayName")
                or principal.get("userPrincipalName")
                or item.get("principalId", "ID Inconnu")
            )
            eligible_names.append(name)

        all_names = []
        for name in active_names + eligible_names:
            if name not in all_names:
                all_names.append(name)

        total_count = len(all_names)
        min_ga = aad01.get("min_global_admins", 2)
        max_ga = aad01.get("max_global_admins", 8)

        is_ok = is_within_range(total_count, min_ga, max_ga)
        details = f"{total_count} GA trouvé(s) :\n"
        details += ", ".join(all_names) if all_names else "Aucun"

        audit_results.append(
            create_finding(
                "AAD-01",
                "Roles",
                f"Nombre de Global Admin entre {min_ga} et {max_ga}",
                is_ok,
                int(total_count),
                details,
                aad01.get("severity", "Low")
            )
        )

        # Construire user_roles_map pour AAD-02
    # On compte les rôles critiques actifs + éligibles afin de détecter le cumul potentiel de privilèges
    user_roles_map = {}

    # 1) Rôles actifs permanents
    for role in active:
        role_name = role.get("displayName", "Inconnu")

        for member in role.get("members", []):
            user_name = (
                member.get("displayName")
                or member.get("userPrincipalName")
                or member.get("id")
                or "Inconnu"
            )

            user_roles_map.setdefault(user_name, [])
            if role_name not in user_roles_map[user_name]:
                user_roles_map[user_name].append(role_name)

    # 2) Rôles éligibles via PIM
    id_to_name = {
        rd.get("id"): rd.get("displayName")
        for rd in role_defs
        if rd.get("id") and rd.get("displayName")
    }

    for item in eligible:
        role_id = item.get("roleDefinitionId")
        role_name = id_to_name.get(role_id, "Inconnu")

        principal = item.get("principal", {})
        user_name = (
            principal.get("displayName")
            or principal.get("userPrincipalName")
            or item.get("principalId")
            or "Inconnu"
        )

        user_roles_map.setdefault(user_name, [])
        if role_name not in user_roles_map[user_name]:
            user_roles_map[user_name].append(role_name)


    # AAD-02
    if aad02.get("enabled", True):
        max_roles = aad02.get("max_privileged_roles_per_user", 1)
        filtered_user_roles_map = {}

        for user_name, roles in user_roles_map.items():
            privileged_roles = [r for r in roles if r in critical_roles]
            if privileged_roles:
                filtered_user_roles_map[user_name] = privileged_roles

        cumul_list = [
            f"{name} ({', '.join(roles)})"
            for name, roles in filtered_user_roles_map.items()
            if len(roles) > max_roles
        ]

        audit_results.append(
            create_finding(
                "AAD-02",
                "Roles",
                "Pas de cumul de privilèges",
                is_empty(cumul_list),
                int(len(cumul_list)),
                "Conforme" if not cumul_list else f"Cumuls détectés : {'; '.join(cumul_list)}",
                aad02.get("severity", "Low")
            )
        )

    # AAD-03
    if aad03.get("enabled", True):
        violations_pim = []
        pim_roles = aad03.get("critical_roles", critical_roles)

        for role in active:
            if role.get("displayName") in pim_roles:
                member_names = [
                    m.get("displayName", "Inconnu")
                    for m in role.get("members", [])
                ]
                if member_names:
                    violations_pim.append(f"{role.get('displayName')} ({', '.join(member_names)})")

        audit_results.append(
            create_finding(
                "AAD-03",
                "PIM",
                "Rôles critiques via PIM uniquement",
                is_empty(violations_pim),
                int(len(violations_pim)),
                "Conforme" if not violations_pim else f"Permanents détectés : {'; '.join(violations_pim)}",
                aad03.get("severity", "Low")
            )
        )

    # AAD-04
    if aad04.get("enabled", True):
        target_role = aad04.get("target_role", "Global Administrator")
        target_role_id = get_role_id(target_role)

        policy_id, rules, status = (
            get_rules_for_role(target_role_id)
            if target_role_id else (None, [], "no_role_definition")
        )

        approval_rule = find_rule(
            rules,
            "Approval",
            ["Approval_EndUser_Assignment", "Approval_EndUser_Activation"],
        )

        has_approval = False
        if approval_rule:
            has_approval = bool(
                approval_rule.get("setting", {}).get("isApprovalRequired", False)
            )

        if status != "ok":
            has_approval = False

        details = "Configuré" if has_approval else "Échec : Approbation non activée pour l'utilisateur final"
        if status != "ok":
            details = f"Échec : impossible de lire la policy {target_role} ({status})"

        audit_results.append(
            create_finding(
                "AAD-04",
                "PIM",
                f"Activation {target_role} nécessite approbation",
                has_approval,
                0 if has_approval else 1,
                details,
                aad04.get("severity", "Low")
            )
        )

    # AAD-05
    if aad05.get("enabled", True):
        pim_roles = aad05.get("critical_roles", critical_roles)
        non_compliant_mfa = []
        missing_data_mfa = []

        for role_name in pim_roles:
            role_id = get_role_id(role_name)
            if not role_id:
                missing_data_mfa.append(f"{role_name} (roleDefinitionId introuvable)")
                continue

            _, role_rules, status = get_rules_for_role(role_id)
            if status != "ok":
                missing_data_mfa.append(f"{role_name} ({status})")
                continue

            mfa_rule = find_rule(
                role_rules,
                "Enablement",
                ["Enablement_EndUser_Assignment", "Enablement_EndUser_Activation"],
            )

            has_mfa = False
            if mfa_rule:
                enabled_rules = mfa_rule.get("enabledRules", [])
                has_mfa = any("MultiFactorAuthentication" in rule for rule in enabled_rules)

            if not has_mfa:
                non_compliant_mfa.append(role_name)

        is_ok = is_empty(non_compliant_mfa) and is_empty(missing_data_mfa)

        if is_ok:
            details = "Conforme (MFA exigé pour les rôles critiques)"
        else:
            parts = []
            if non_compliant_mfa:
                parts.append(f"MFA non exigé pour : {', '.join(non_compliant_mfa)}")
            if missing_data_mfa:
                parts.append(f"Données manquantes : {', '.join(missing_data_mfa)}")
            details = " | ".join(parts)

        audit_results.append(
            create_finding(
                "AAD-05",
                "PIM",
                "MFA requis pour activation PIM (rôles critiques)",
                is_ok,
                int(len(non_compliant_mfa) + len(missing_data_mfa)),
                details,
                aad05.get("severity", "Low")
            )
        )

    # AAD-06
    if aad06.get("enabled", True):
        pim_roles = aad06.get("critical_roles", critical_roles)
        max_duration_hours = aad06.get("max_activation_duration_hours", 8)

        non_compliant_duration = []
        missing_data_duration = []

        for role_name in pim_roles:
            role_id = get_role_id(role_name)
            if not role_id:
                missing_data_duration.append(f"{role_name} (roleDefinitionId introuvable)")
                continue

            _, role_rules, status = get_rules_for_role(role_id)
            if status != "ok":
                missing_data_duration.append(f"{role_name} ({status})")
                continue

            expiration_rule = find_rule(
                role_rules,
                "Expiration",
                ["Expiration_EndUser_Assignment", "Expiration_EndUser_Activation"],
            )

            if not expiration_rule:
                non_compliant_duration.append(f"{role_name} (règle expiration absente)")
                continue

            duration_str = expiration_rule.get("maximumDuration", "PT0H")
            hours_match = re.search(r"PT(\d+)H", duration_str)
            mins_match = re.search(r"PT.*?(\d+)M", duration_str)
            hours = int(hours_match.group(1)) if hours_match else 0
            mins = int(mins_match.group(1)) if mins_match else 0
            duration_hours = hours + (mins / 60)

            if not is_within_range(duration_hours, 0.0000001, max_duration_hours):
                non_compliant_duration.append(f"{role_name} ({duration_hours}h)")

        is_ok = is_empty(non_compliant_duration) and is_empty(missing_data_duration)

        if is_ok:
            details = "Conforme"
        else:
            parts = []
            if non_compliant_duration:
                parts.append(f"Durée non conforme : {', '.join(non_compliant_duration)}")
            if missing_data_duration:
                parts.append(f"Données manquantes : {', '.join(missing_data_duration)}")
            details = " | ".join(parts)

        audit_results.append(
            create_finding(
                "AAD-06",
                "PIM",
                f"Durée d'activation <= {max_duration_hours}h (rôles critiques)",
                is_ok,
                int(len(non_compliant_duration) + len(missing_data_duration)),
                details,
                aad06.get("severity", "Low")
            )
        )
    return audit_results