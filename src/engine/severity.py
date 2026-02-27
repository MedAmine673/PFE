def get_severity(control_id):
    """
    Définit la criticité par défaut pour chaque ID de contrôle.
    """
    severities = {
        "AAD-01": "High",     # Nombre de GA
        "AAD-02": "Critical", # Rôles permanents
        "AAD-03": "Medium",   # Cumul de rôles
        "AAD-04": "High"      # Audit MFA 
    }
    return severities.get(control_id, "Low")