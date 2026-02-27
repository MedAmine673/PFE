def normalize_roles_data(raw_data):
    normalized = []
    # On boucle sur chaque rôle trouvé (Global Admin, etc.)
    for role in raw_data.get('value', []):
        role_name = role.get('displayName')
        # On extrait uniquement les membres de ce rôle
        for member in role.get('members', []):
            normalized.append({
                "userPrincipalName": member.get('userPrincipalName'),
                "displayName": member.get('displayName'),
                "roleName": role_name,
                "userId": member.get('id')
            })
    return normalized # Renvoie une liste simple de dictionnaires