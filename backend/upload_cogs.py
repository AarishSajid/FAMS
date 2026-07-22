import logging
from database import SessionLocal
from models.farm import Farm
from models.cycle import Cycle
from seed import upload_mock_cogs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("upload_cogs")

def main():
    db = SessionLocal()
    farms = db.query(Farm).all()
    cycle = db.query(Cycle).filter(Cycle.active == True).first()
    if cycle:
        upload_mock_cogs(farms, cycle.id, logger)
        logger.info("Uploaded COGs.")
    else:
        logger.warning("No active cycle found.")
    db.close()

if __name__ == "__main__":
    main()
