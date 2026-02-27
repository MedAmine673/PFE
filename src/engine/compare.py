def is_within_range(value, min_val, max_val):
    """Vérifie si une valeur est dans l'intervalle autorisé."""
    return min_val <= value <= max_val

def is_empty(collection):
    """Vérifie si une liste ou un dictionnaire est vide."""
    return len(collection) == 0

def check_threshold(current_value, max_allowed):
    """Vérifie si on ne dépasse pas un maximum."""
    return current_value <= max_allowed