from src.engine.severity import get_control_points


def get_recommendation(control_id: str, passed: bool) -> str:
    """
    Retourne une recommandation selon le contrôle.
    Pas de recommandation si le contrôle est conforme.
    """
    if passed:
        return ""

    recommendations = {
        "AAD-01": "Ajuster le nombre de comptes Global Administrator afin de respecter les seuils définis dans la baseline.",
        "AAD-02": "Réduire le cumul de rôles critiques par utilisateur et appliquer le principe du moindre privilège.",
        "AAD-03": "Attribuer les rôles critiques via PIM au lieu d’assignations permanentes.",
        "AAD-04": "Configurer une approbation obligatoire pour l’activation du rôle Global Administrator via PIM.",
        "AAD-05": "Exiger l’authentification multifacteur lors de l’activation des rôles critiques via PIM.",
        "AAD-06": "Réduire la durée maximale d’activation des rôles critiques afin de limiter l’exposition des privilèges.",
        "AAD-07": "Activer le MFA pour tous les comptes administrateurs concernés.",
        "AAD-08": "Mettre en place une politique Conditional Access dédiée à la protection des comptes administrateurs.",
        "AAD-09": "Examiner les comptes administrateurs inactifs et désactiver ou supprimer ceux qui ne sont plus nécessaires.",
        "AAD-10": "Analyser les comptes administrateurs jamais connectés et supprimer ou désactiver ceux qui ne sont pas justifiés.",
    }

    return recommendations.get(
        control_id,
        "Appliquer une action corrective conforme à la baseline de sécurité."
    )


def create_finding(control_id, category, requirement, result, affected, details, severity):
    """
    Génère un dictionnaire standardisé pour le rapport final.
    - result est un bool (True/False)
    - severity provient de la baseline
    """
    passed = bool(result)
    risk_points = get_control_points(severity, passed)
    recommendation = get_recommendation(control_id, passed)

    return {
        "Control ID": control_id,
        "Category": category,
        "Requirement": requirement,
        "Result": "Pass" if passed else "Fail",
        "Passed": passed,
        "Criticality": severity,
        "Risk Points": int(risk_points),
        "Affected": int(affected) if isinstance(affected, (int, float)) else affected,
        "Details": details,
        "Recommendation": recommendation,
    }