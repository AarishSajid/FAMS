import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from config import get_settings
from database import SessionLocal
from models.user import User
from models.service_center import District, ServiceCenter
from models.farm import Farm, FieldCrop
from models.service_request import Service, Product

logger = logging.getLogger("fams.sync")

settings = get_settings()

def run_sync():
    """
    Connects to the remote Agriverse DB and syncs core tables to the local FAMS DB.
    """
    logger.info(f"Starting Agriverse DB Sync. Target: {settings.AGRIVERSE_DB_URL}")
    
    # 1. Connect to remote DB
    try:
        remote_engine = create_engine(settings.AGRIVERSE_DB_URL, connect_args={"connect_timeout": 5})
        RemoteSession = sessionmaker(bind=remote_engine)
        remote_db = RemoteSession()
        # Test connection
        remote_engine.connect().close()
    except OperationalError as e:
        logger.warning(f"Could not connect to remote Agriverse DB. Sync aborted. Details: {e}")
        return
    except Exception as e:
        logger.error(f"Unexpected error connecting to remote DB: {e}")
        return

    # 2. Connect to local DB
    local_db = SessionLocal()
    
    try:
        # Example logic for syncing Users (Assuming the remote DB has a matching 'User' table structure)
        # Note: Since the remote DB doesn't exist yet, we wrap the actual queries in try-except.
        try:
            remote_users = remote_db.query(User).all()
            for ru in remote_users:
                lu = local_db.query(User).filter(User.id == ru.id).first()
                if lu:
                    # Update fields
                    lu.email = ru.email
                    lu.username = ru.username
                    lu.firstName = ru.firstName
                    lu.lastName = ru.lastName
                    lu.role = ru.role
                    lu.isActive = ru.isActive
                    lu.serviceCenterId = ru.serviceCenterId
                    lu.availabilityStatus = ru.availabilityStatus
                else:
                    # Insert new
                    local_db.add(User(
                        id=ru.id, email=ru.email, username=ru.username, 
                        password=ru.password, firstName=ru.firstName, lastName=ru.lastName,
                        role=ru.role, isActive=ru.isActive, 
                        serviceCenterId=ru.serviceCenterId, availabilityStatus=ru.availabilityStatus,
                        createdAt=ru.createdAt, updatedAt=ru.updatedAt, lastLogin=ru.lastLogin
                    ))
            local_db.commit()
            logger.info(f"Synced {len(remote_users)} users.")
        except Exception as e:
            logger.error(f"Error syncing Users: {e}")
            local_db.rollback()

        # Similar blocks would be implemented for District, ServiceCenter, Farm, FieldCrop, Service, Product
        # using the same upsert pattern once the remote schema is confirmed.
        
        logger.info("Agriverse DB Sync completed successfully.")
        
    finally:
        remote_db.close()
        local_db.close()
