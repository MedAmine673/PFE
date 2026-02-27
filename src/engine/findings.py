from src.engine.severity import get_severity

def create_finding(control_id, category, requirement, result, affected, details):
    """
    Génère un dictionnaire standardisé pour le rapport final.
    """
    return {
        "Control ID": control_id,
        "Category": category,
        "Requirement": requirement,
        "Result": "Pass" if result else "Fail",
        "Criticality": get_severity(control_id),
        "Affected": affected,
        "Details": details
    }