import re
from src.engine.findings import create_finding
from src.engine.compare import is_empty, check_threshold, is_within_range


def audit_roles(raw_data, baseline):
    audit_results = []

    config = baseline.get("roles_audit", {})
    active = raw_data.get("active_assignments", [])
    eligible = raw_data.get("eligible_assignments", [])
    policies = raw_data.get("pim_policies", [])
    assignments = raw_data.get("policy_assignments", [])
    role_defs = raw_data.get("role_definitions", [])
    critical_roles = config.get("critical_roles", [])

    name_to_id = {rd.get("displayName"): rd.get("id") for rd in role_defs if rd.get("displayName") and rd.get("id")}
    ga_role_id = name_to_id.get("Global Administrator")

    # SECTION 1 : NOMBRE DE GA (AAD-01) min=2, max=8
    ga_active_names = []
    for r in [role for role in active if role.get("displayName") == "Global Administrator"]:
        ga_active_names.extend(
            [m.get("displayName", m.get("userPrincipalName", "Inconnu")) for m in r.get("members", [])]
        )

    ga_eligible_names = []
    for e in [item for item in eligible if ga_role_id and item.get("roleDefinitionId") == ga_role_id]:
        principal = e.get("principal", {})
        name = principal.get("displayName") or principal.get("userPrincipalName") or e.get("principalId", "ID Inconnu")
        ga_eligible_names.append(name)

    all_ga_names = []
    for n in (ga_active_names + ga_eligible_names):
        if n not in all_ga_names:
            all_ga_names.append(n)

    total_ga_count = len(all_ga_names)

    min_ga = config.get("min_global_admins", 2)
    max_ga = config.get("max_global_admins", 8)

    is_ga_ok = is_within_range(total_ga_count, min_ga, max_ga)

    details_ga = f"{total_ga_count} GA trouvé(s) :\n"
    details_ga += ", ".join(all_ga_names) if all_ga_names else "Aucun"

    audit_results.append(
        create_finding(
            "AAD-01",
            "Roles",
            f"Nombre de Global Admin entre {min_ga} et {max_ga}",
            is_ga_ok,
            int(total_ga_count),
            details_ga
        )
    )

    # SECTION 2 : CUMUL ET RÔLES CRITIQUES (AAD-02 & AAD-03)
    user_roles_map = {}
    for role in active:
        r_name = role.get("displayName", "Inconnu")
        for m in role.get("members", []):
            u_name = m.get("displayName", "Inconnu")
            user_roles_map.setdefault(u_name, []).append(r_name)

    cumul_list = [f"{n} ({', '.join(rs)})" for n, rs in user_roles_map.items() if len(rs) > 1]
    audit_results.append(
        create_finding(
            "AAD-02",
            "Roles",
            "Pas de cumul de privilèges",
            is_empty(cumul_list),
            int(len(cumul_list)),
            "Conforme" if not cumul_list else f"Cumuls détectés : {'; '.join(cumul_list)}",
        )
    )

    violations_pim = []
    for role in active:
        if role.get("displayName") in critical_roles:
            m_names = [m.get("displayName", "Inconnu") for m in role.get("members", [])]
            if m_names:
                violations_pim.append(f"{role.get('displayName')} ({', '.join(m_names)})")

    audit_results.append(
        create_finding(
            "AAD-03",
            "PIM",
            "Rôles critiques via PIM uniquement",
            is_empty(violations_pim),
            int(len(violations_pim)),
            "Conforme" if not violations_pim else f"Permanents détectés : {'; '.join(violations_pim)}",
        )
    )

    # SECTION 3 : POLITIQUES PIM (AAD-04, AAD-05, AAD-06)
    def get_rules_for_role(role_def_id: str):
        a = next((x for x in assignments if x.get("roleDefinitionId") == role_def_id), None)
        if not a:
            return None, [], "no_assignment"
        policy_id = a.get("policyId")
        p = next((pp for pp in policies if pp.get("id") == policy_id), None)
        if not p:
            return policy_id, [], "no_policy"
        return policy_id, p.get("rules", []), "ok"

    def find_rule(rules_list, odata_contains: str, ids):
        return next(
            (
                r for r in rules_list
                if odata_contains in r.get("@odata.type", "")
                and r.get("id", "") in ids
            ),
            None,
        )

    # AAD-04 : APPROBATION (seulement GA)
    ga_policy_id, ga_rules, ga_status = get_rules_for_role(ga_role_id) if ga_role_id else (None, [], "no_role_definition")

    approval_rule = find_rule(
        ga_rules,
        "Approval",
        ["Approval_EndUser_Assignment", "Approval_EndUser_Activation"],
    )

    has_approval = False
    if approval_rule:
        has_approval = bool(approval_rule.get("setting", {}).get("isApprovalRequired", False))

    if ga_status != "ok":
        has_approval = False

    details_aad04 = "Configuré" if has_approval else "Échec : Approbation non activée pour l'utilisateur final"
    if ga_status != "ok":
        details_aad04 = f"Échec : impossible de lire la policy GA ({ga_status})"

    audit_results.append(
        create_finding(
            "AAD-04",
            "PIM",
            "Activation GA nécessite approbation",
            has_approval,
            0 if has_approval else 1,
            details_aad04,
        )
    )

    # AAD-05 : MFA requis (tous les rôles critiques)
    non_compliant_mfa = []
    missing_data_mfa = []

    for role_name in critical_roles:
        role_id = name_to_id.get(role_name)
        if not role_id:
            missing_data_mfa.append(f"{role_name} (roleDefinitionId introuvable)")
            continue

        policy_id, role_rules, status = get_rules_for_role(role_id)
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
            enabled_list = mfa_rule.get("enabledRules", [])
            has_mfa = any("MultiFactorAuthentication" in rule for rule in enabled_list)

        if not has_mfa:
            non_compliant_mfa.append(role_name)

    is_mfa_ok = is_empty(non_compliant_mfa) and is_empty(missing_data_mfa)

    if is_mfa_ok:
        details_mfa = "Conforme (MFA exigé pour les rôles critiques)"
    else:
        parts = []
        if non_compliant_mfa:
            parts.append(f"MFA non exigé pour : {', '.join(non_compliant_mfa)}")
        if missing_data_mfa:
            parts.append(f"Données manquantes : {', '.join(missing_data_mfa)}")
        details_mfa = " | ".join(parts)

    audit_results.append(
        create_finding(
            "AAD-05",
            "PIM",
            "MFA requis pour activation PIM (rôles critiques)",
            is_mfa_ok,
            int(len(non_compliant_mfa) + len(missing_data_mfa)),
            details_mfa,
        )
    )

    # AAD-06 : Durée d'activation <= 8h (tous les rôles critiques)
    non_compliant_duration = []
    missing_data_duration = []

    for role_name in critical_roles:
        role_id = name_to_id.get(role_name)
        if not role_id:
            missing_data_duration.append(f"{role_name} (roleDefinitionId introuvable)")
            continue

        policy_id, role_rules, status = get_rules_for_role(role_id)
        if status != "ok":
            missing_data_duration.append(f"{role_name} ({status})")
            continue

        exp_rule = find_rule(
            role_rules,
            "Expiration",
            ["Expiration_EndUser_Assignment", "Expiration_EndUser_Activation"],
        )

        if not exp_rule:
            non_compliant_duration.append(f"{role_name} (règle expiration absente)")
            continue

        duration_str = exp_rule.get("maximumDuration", "PT0H")
        h_match = re.search(r"PT(\d+)H", duration_str)
        m_match = re.search(r"PT.*?(\d+)M", duration_str)
        hours = int(h_match.group(1)) if h_match else 0
        mins = int(m_match.group(1)) if m_match else 0
        max_hours = hours + (mins / 60)

        if not is_within_range(max_hours, 0.0000001, 8):
            non_compliant_duration.append(f"{role_name} ({max_hours}h)")

    is_duration_ok = is_empty(non_compliant_duration) and is_empty(missing_data_duration)

    if is_duration_ok:
        details_dur = "Conforme"
    else:
        parts = []
        if non_compliant_duration:
            parts.append(f"Durée non conforme : {', '.join(non_compliant_duration)}")
        if missing_data_duration:
            parts.append(f"Données manquantes : {', '.join(missing_data_duration)}")
        details_dur = " | ".join(parts)

    audit_results.append(
        create_finding(
            "AAD-06",
            "PIM",
            "Durée d'activation <= 8h (rôles critiques)",
            is_duration_ok,
            int(len(non_compliant_duration) + len(missing_data_duration)),
            details_dur,
        )
    )
   
    return audit_results