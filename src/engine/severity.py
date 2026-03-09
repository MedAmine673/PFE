# src/engine/severity.py

def get_severity(control_id):
    """
    Définit la criticité par défaut pour chaque ID de contrôle.
    """
    severities = {
        "AAD-01": "High",      # Nombre de GA
        "AAD-02": "Critical",  # Cumul de privilèges
        "AAD-03": "Medium",    # Rôles critiques permanents
        "AAD-04": "High",      # Approbation GA
        "AAD-05": "Low",       # MFA activation PIM
        "AAD-06": "Low",       # Durée activation
        "AAD-07": "High",    # Admin sans MFA
        "AAD-08": "Medium",  # Absence de CA admin
    }
    return severities.get(control_id, "Low")


def get_severity_points(severity: str) -> int:
    """
    Poids associé à une criticité.
    """
    weights = {
        "Critical": 10,
        "High": 7,
        "Medium": 4,
        "Low": 1
    }
    return int(weights.get(severity, 1))


def get_control_points(control_id: str, passed: bool) -> int:
    """
    Points de risque pour un contrôle.
    Si Pass => 0, sinon poids selon criticité.
    """
    if passed:
        return 0
    sev = get_severity(control_id)
    return get_severity_points(sev)


def classify_risk(score: int) -> str:
    """
    Classification globale à partir du score.
    """
    if score == 0:
        return "Faible"
    if score <= 10:
        return "Modéré"
    if score <= 20:
        return "Élevé"
    return "Critique"