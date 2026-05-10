import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# 🔹 Authentification Azure (App Registration)
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# 🔹 Fichier contenant la liste des tenants à auditer
TENANTS_FILE = os.getenv("TENANTS_FILE", "tenants.json")

# 🔹 Chemins de stockage local (mode manuel)
RAW_DATA_PATH = "data/raw"
REPORTS_PATH = "data/reports"


