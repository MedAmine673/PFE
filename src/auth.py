import msal
from src.config import CLIENT_ID, CLIENT_SECRET 

def get_token(tenant_id):
    authority = f"https://login.microsoftonline.com/{tenant_id}" #C’est l’endpoint vers lequel l’application envoie sa demande d’authentification.
    
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, 
        authority=authority, 
        client_credential=CLIENT_SECRET
        # Cet objet représente ton application côté authentification. C’est lui qui va demander un token auprès de Microsoft Entra ID.
    )
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"]) #Le scope .default permet de récupérer un jeton d’accès contenant les permissions effectivement accordées à l’application dans le tenant ciblé
    
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Erreur d'auth : {result.get('error_description')}")
