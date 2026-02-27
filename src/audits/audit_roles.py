from src.engine.findings import create_finding
from src.engine.compare import is_within_range, is_empty

def audit_roles(raw_data, baseline):
    audit_results = []
    
    config = baseline.get("roles_audit", {})
    active = raw_data.get('active_assignments', [])
    critical_roles = config.get('critical_roles', [])

    # --- AAD-01 : Nombre de Global Admins ---
    ga_members = []
    for r in [role for role in active if role['displayName'] == 'Global Administrator']:
        ga_members.extend(r.get('members', []))
    
    count_ga = len(ga_members)
    is_ga_ok = is_within_range(count_ga, 2, config.get('max_global_admins', 3))
    
    # On récupère les noms pour le détail
    ga_names = [m.get('displayName', 'Inconnu') for m in ga_members]
    ga_details = f"{count_ga} Global Admin(s) trouvé(s) : {', '.join(ga_names)}" if count_ga > 0 else "Aucun Global Admin détecté"

    audit_results.append(create_finding(
        control_id="AAD-01",
        category="Roles",
        requirement=f"Nombre de GA entre 2 et {config.get('max_global_admins', 3)}",
        result=is_ga_ok,
        affected=count_ga,
        details=ga_details
    ))

    # --- AAD-02 : Aucun rôle critique permanent ---
    role_violations = []
    total_users_affected = 0

    for role in active:
        role_name = role['displayName']
        if role_name in critical_roles:
            m_names = [m.get('displayName', 'Inconnu') for m in role.get('members', [])]
            if m_names:
                total_users_affected += len(m_names)
                role_violations.append(f"{role_name} ({', '.join(m_names)})")

    is_perm_ok = is_empty(role_violations)
    
    # Formatage type "Expert" : Liste des rôles avec les utilisateurs entre parenthèses
    perm_details = "Conforme : Aucun rôle critique permanent" if is_perm_ok else \
                   f"{len(role_violations)} rôle(s) critique(s) permanent(s) : {'; '.join(role_violations)}"

    audit_results.append(create_finding(
        control_id="AAD-02",
        category="Roles",
        requirement="Aucun rôle critique permanent (PIM obligatoire)",
        result=is_perm_ok,
        affected=total_users_affected,
        details=perm_details
    ))

    # --- AAD-03 : Cumul de rôles ---
    user_roles_map = {} # nom -> [liste des rôles]
    for role in active:
        r_name = role['displayName']
        for m in role.get('members', []):
            u_name = m.get('displayName', 'Inconnu')
            if u_name not in user_roles_map:
                user_roles_map[u_name] = []
            user_roles_map[u_name].append(r_name)
    
    cumul_findings = []
    for name, roles in user_roles_map.items():
        if len(roles) > 1:
            cumul_findings.append(f"{name} ({', '.join(roles)})")
    
    is_cumul_ok = is_empty(cumul_findings)

    audit_results.append(create_finding(
        control_id="AAD-03",
        category="Roles",
        requirement="Pas de cumul de privilèges",
        result=is_cumul_ok,
        affected=len(cumul_findings),
        details="Conforme : Aucun cumul détecté" if is_cumul_ok else \
                f"{len(cumul_findings)} utilisateur(s) multi-rôles : {'; '.join(cumul_findings)}"
    ))

    return audit_results