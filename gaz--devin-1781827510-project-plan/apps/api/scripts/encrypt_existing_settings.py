import asyncio
import os
import sys

# Add the project root to sys.path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.settings import get_settings
from app.db_models import TenantModel
from app.encryption import encrypt_json_secrets

def migrate_settings():
    settings = get_settings()
    if not settings.fernet_key:
        print("Error: FERNET_KEY is not set in environment.")
        return

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with SessionLocal() as session:
        tenants = session.query(TenantModel).all()
        migrated_count = 0
        
        for tenant in tenants:
            if not tenant.settings:
                continue
                
            current_settings = tenant.settings
            encrypted_settings = encrypt_json_secrets(current_settings, settings.fernet_key)
            
            # Check if any changes were made
            if current_settings != encrypted_settings:
                tenant.settings = encrypted_settings
                migrated_count += 1
                
        if migrated_count > 0:
            session.commit()
            print(f"Successfully encrypted settings for {migrated_count} tenants.")
        else:
            print("No tenants needed migration (all secrets already encrypted or empty).")

if __name__ == "__main__":
    migrate_settings()
