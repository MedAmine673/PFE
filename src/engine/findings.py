# src/engine/findings.py
from src.engine.severity import get_severity, get_control_points

def create_finding(control_id, category, requirement, result, affected, details):
    """
    Génère un dictionnaire standardisé pour le rapport final.
    - result est un bool (True/False)
    """
    passed = bool(result)
    severity = get_severity(control_id)
    risk_points = get_control_points(control_id, passed)

    return {
        "Control ID": control_id,
        "Category": category,
        "Requirement": requirement,
        "Result": "Pass" if passed else "Fail",
        "Passed": passed,  # utile pour calculs sans parser "Result"
        "Criticality": severity,
        "Risk Points": int(risk_points),  # utile pour la classification des risques
        "Affected": int(affected) if isinstance(affected, (int, float)) else affected,
        "Details": details
    }