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


def get_control_points(severity: str, passed: bool) -> int:
    """
    Points de risque pour un contrôle.
    Si Pass => 0, sinon poids selon criticité.
    """
    if passed:
        return 0
    return get_severity_points(severity)


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