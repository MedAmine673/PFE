from src.engine.severity import get_control_points

def create_finding(control_id, category, requirement, result, affected, details, severity):
    """
    Génère un dictionnaire standardisé pour le rapport final.
    - result est un bool (True/False)
    - severity provient de la baseline
    """
    passed = bool(result)
    risk_points = get_control_points(severity, passed)

    return {
        "Control ID": control_id,
        "Category": category,
        "Requirement": requirement,
        "Result": "Pass" if passed else "Fail",
        "Passed": passed,
        "Criticality": severity,
        "Risk Points": int(risk_points),
        "Affected": int(affected) if isinstance(affected, (int, float)) else affected,
        "Details": details
    }