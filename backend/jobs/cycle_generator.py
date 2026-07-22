"""
Background job to auto-generate the 5-day cycle.
Runs every 5 days via APScheduler.
"""

import logging
from database import SessionLocal
from services.cycle_service import generate_cycle

logger = logging.getLogger("fams.jobs.cycle")


def run_cycle_generator():
    """APScheduler wrapper for the cycle generator."""
    logger.info("Running scheduled cycle generator job...")
    db = SessionLocal()
    try:
        result = generate_cycle(db)
        logger.info(f"Cycle {result['cycle']['index']} generated. Created {result['casesCreated']} cases.")
        if result['skippedNoServiceCenter']:
            logger.warning(f"Skipped {len(result['skippedNoServiceCenter'])} farms with no service center assigned.")
    except Exception as e:
        logger.error(f"Error running cycle generator: {e}")
    finally:
        db.close()
