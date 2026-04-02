
import msal
from src.config import CLIENT_ID, CLIENT_SECRET 

def get_token(tenant_id):
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, 
        authority=authority, 
        client_credential=CLIENT_SECRET
    )
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Erreur d'auth : {result.get('error_description')}")