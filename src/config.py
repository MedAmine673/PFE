import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZ_TENANT_ID = os.getenv("AZURE_TENANT_ID")
TENANTS_FILE = os.getenv("TENANTS_FILE", "tenants.json")

RAW_DATA_PATH = "data/raw"
NORMALIZED_DATA_PATH = "data/normalized"