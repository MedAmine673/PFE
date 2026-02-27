import os
from src.config import AZ_TENANT_ID

def get_all_tenants():
  
    return [
        {
            "id": AZ_TENANT_ID, 
            "name": "Tenant_Production"
        },
       
       
    ]