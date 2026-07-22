import json
import logging

# Monkeypatch passlib bcrypt bug with bcrypt>=4.0.0
import passlib.handlers.bcrypt
passlib.handlers.bcrypt.detect_wrap_bug = lambda *args: False
import os
import base64
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import boto3
from botocore.exceptions import ClientError

def upload_mock_cogs(db_farms, cycle_id, logger):
    # Valid tiny 1x1 base64 TIFF
    tiny_tiff_b64 = "SUkqAAgAAAASAP4ABAABAAAAAAAAAAABBAABAAAAAQAAAAMBAwABAAAACAAAAAYBAwABAAAAAgAAAAgBAwABAAAAAQAAAAoBAwABAAAAAQAAABEBBAABAAAA4AAAABUBAwABAAAAAwAAABYBBAABAAAAAQAAABcBBAABAAAAAQAAABoBBQABAAAAdgAAABsBBQABAAAAfgAAABwBAwABAAAAAQAAACgBAwABAAAAAgAAADEBAwABAAAAAQAAADsBAwABAAAAAQAAADwBAwABAAAAAQAAAD0BAwABAAAAAQAAAD4BAwABAAAAAQAAAD8BAwABAAAAAQAAAAECAAABAAAAAQAAAAICAAABAAAA/wAAAAMCAAABAAAAAQAAAAMDAwABAAAAIQAAAAQDAwABAAAAIgAAAAoDAwABAAAAAQAAABMCAAABAAAAAgAAABQCAAABAAAA/wAAABUCAAABAAAAAQAAABYCAAABAAAA/wAAAOAAAAABAAAAAQAAAAgAAAAIAAAACAAAAAAAAAAAAAAAAAAAAA=="
    tiff_bytes = base64.b64decode(tiny_tiff_b64)
    
    s3 = boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin',
        region_name='us-east-1'
    )
    bucket = 'agriverse-cogs'
    try:
        s3.create_bucket(Bucket=bucket)
        # Make bucket public
        policy = '{"Version":"2012-10-17","Statement":[{"Action":["s3:GetObject"],"Effect":"Allow","Principal":{"AWS":["*"]},"Resource":["arn:aws:s3:::agriverse-cogs/*"]}]}'
        s3.put_bucket_policy(Bucket=bucket, Policy=policy)
    except Exception as e:
        pass # Bucket likely exists
    
    indices = ["NDVI", "NDMI", "NDRE", "MSAVI"]
    logger.info("Uploading mock COGs to MinIO...")
    for farm in db_farms:
        for idx in indices:
            key = f"{farm.id}/{cycle_id}/{idx}.tif"
            try:
                s3.put_object(Bucket=bucket, Key=key, Body=tiff_bytes, ContentType="image/tiff")
            except Exception as e:
                logger.error(f"Failed to upload COG: {e}")

from database import engine, Base, SessionLocal
from enums import UserRole, FieldAgentAvailability, AdvisoryCaseState, VerificationOutcome, AdvisoryCaseKind, IssueType, AdvisorySeverity, ServiceRequestStatus
from models.user import User
from models.service_center import ServiceCenter, District
from models.farm import Farm, FieldCrop, FarmAdvisory
from models.advisory import AdvisoryCase, AdvisoryVerification, AdvisoryFeedback, AdvisoryEvent, AdvisoryForwarding, AdvisoryClosure
from models.cycle import Cycle
from models.service_request import Service, ServiceRequest, Product, ProductRequest

logger = logging.getLogger("fams.seeder")
logging.basicConfig(level=logging.INFO)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_pass(p): return pwd_context.hash(p)

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    if db.query(User).first():
        logger.info("Database already seeded. Skipping.")
        db.close()
        return

    db.close()

    logger.info("Dropping and recreating all tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Re-open session for seeding
    db = SessionLocal()

    now = datetime.now(timezone.utc)

    try:
        # 1. Districts & Service Centers
        logger.info("Creating Districts and Service Centers...")
        d1 = District(name="Layyah")
        d2 = District(name="Sheikhupura")
        db.add_all([d1, d2])
        db.flush()

        sc1 = ServiceCenter(name="Layyah Center", region="Punjab - Layyah", districtId=d1.id)
        sc2 = ServiceCenter(name="Sheikhupura Center", region="Punjab - Sheikhupura", districtId=d2.id)
        sc3 = ServiceCenter(name="Muridke Center", region="Punjab - Muridke", districtId=d2.id)
        db.add_all([sc1, sc2, sc3])
        db.flush()

        # 2. Users
        logger.info("Creating Users...")
        # Manager
        manager_email = os.getenv("MANAGER_EMAIL", "ayesha.khan@agriverse.com")
        manager_password = os.getenv("MANAGER_PASSWORD", "password")
        manager = User(
            id="usr-manager", email=manager_email, username="ayesha",
            password=hash_pass(manager_password), firstName="Ayesha", lastName="Khan",
            role=UserRole.SERVICE_CENTER_MANAGER, serviceCenterId=sc1.id,
            createdAt=now, updatedAt=now
        )
        
        # Chief Agronomist
        chief_email = os.getenv("CHIEF_EMAIL", "chief@agriverse.com")
        chief_password = os.getenv("CHIEF_PASSWORD", "password")
        chief = User(
            id="usr-chief", email=chief_email, username="chief",
            password=hash_pass(chief_password), firstName="Chief", lastName="Agronomist",
            role=UserRole.CHIEF_AGRONOMIST,
            createdAt=now, updatedAt=now
        )

        # Field Agents
        agent_names = ["Mustafa Kamal", "Tariq Jamil", "Usman Khawaja", "Kamran Akmal"]
        agents = []
        for i, name in enumerate(agent_names):
            parts = name.split()
            ag = User(
                id=f"ag-{i+1}", email=f"agent{i+1}@agriverse.com", username=f"agent{i+1}",
                password=hash_pass("password"), firstName=parts[0], lastName=parts[1] if len(parts)>1 else "",
                role=UserRole.FIELD_AGENT, serviceCenterId=sc1.id,
                availabilityStatus=FieldAgentAvailability.AVAILABLE if i != 1 else FieldAgentAvailability.BUSY,
                createdAt=now, updatedAt=now
            )
            agents.append(ag)

        # Farmer
        farmer_user = User(
            id="usr-farmer", email="farmer@agriverse.com", username="farmer",
            password=hash_pass("password"), firstName="Ali", lastName="Farmer",
            role=UserRole.PROGRESSIVE_FARMER, serviceCenterId=sc1.id,
            createdAt=now, updatedAt=now
        )

        db.add_all([manager, chief, farmer_user] + agents)
        db.flush()

        # 3. Farms & FieldCrops
        logger.info("Loading Farms from JSON...")
        farms_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "lib", "farms.json")
        with open(farms_path, "r") as f:
            farms_data = json.load(f)

        db_farms = []
        for i, f_data in enumerate(farms_data):
            lon = f_data.get("lon")
            district = "Layyah" if lon and lon < 72.5 else "Sheikhupura"
            center_id = sc1.id if district == "Layyah" else (sc2.id if i % 2 == 0 else sc3.id)
            numeric_id = int(str(f_data["id"]).replace("farm-", ""))

            farm = Farm(
                id=numeric_id,
                farmer=f_data.get("farmer", f"Farmer {i}"),
                village=f_data.get("village", ""),
                acres=f_data.get("acres", 5.0),
                lon=lon,
                lat=f_data.get("lat"),
                serviceCenterId=center_id
            )
            db.add(farm)
            db_farms.append(farm)
        db.flush()

        # FieldCrops
        for i, f_data in enumerate(farms_data):
            numeric_id = int(str(f_data["id"]).replace("farm-", ""))
            fc = FieldCrop(
                farmId=numeric_id,
                crop=f_data.get("crop", "Wheat"),
                variety="Standard",
                sowDate=now - timedelta(days=60)
            )
            db.add(fc)
        db.flush()

        # 4. Cycle & Advisories
        logger.info("Creating active Cycle and mock Advisories...")
        cycle = Cycle(index=42, startDate=now - timedelta(days=2), endDate=now + timedelta(days=3), active=True)
        db.add(cycle)
        db.flush()

        def get_issue(f_data):
            disease = f_data.get("disease") or {}
            condition = f_data.get("condition")
            irrigation = f_data.get("irrigation", [])
            sNo = f_data.get("sNo", 0)
            crop = f_data.get("crop")

            if disease.get("outbreak") and (disease.get("severity") or 0) >= 40: return "Pest Infestation"
            if disease.get("issues") and disease.get("outbreak"): return "Pest Infestation"
            if condition != "Good": return "Low Vigour"
            if len(irrigation) == 1 and irrigation[0] == "Tubewell" and sNo % 3 == 0: return "Water Stress"
            if crop == "Sugarcane" and sNo % 2 == 0: return "Nitrogen Deficiency"
            if sNo % 7 == 0: return "Water Stress"
            return None

        def advisory_text(issue, f_data):
            sNo = f_data.get("sNo", 0)
            crop = f_data.get("crop", "field").lower()
            disease_issues = (f_data.get("disease") or {}).get("issues", "jassid")
            if issue == "Pest Infestation":
                return f"Vegetation anomaly consistent with pest activity ({disease_issues}) detected in the {'north-east' if sNo % 2 else 'south-west'} section of the {crop} field. Recommend scouting and targeted spray within 3 days."
            if issue == "Water Stress":
                pct = max(10, (sNo * 7) % 40)
                return f"Moderate moisture stress detected across {pct}% of the field on the NDMI layer. Irrigation recommended within 48 hours to avoid yield loss."
            if issue == "Low Vigour":
                return "Crop vigour below reference for this stage in scattered patches. Verify establishment and consider a nitrogen top-dress if confirmed."
            if issue == "Nitrogen Deficiency":
                return "NDRE indicates chlorophyll/nitrogen status below reference in the central strip. Recommend 1 bag urea per acre after field confirmation."
            return "Anomaly detected; field verification recommended."

        def get_severity(f_data):
            sev = (f_data.get("disease") or {}).get("severity") or 0
            sNo = f_data.get("sNo", 0)
            if sev >= 50: return AdvisorySeverity.HIGH
            if sNo % 3 == 0: return AdvisorySeverity.MODERATE
            if sNo % 2 == 0: return AdvisorySeverity.HIGH
            return AdvisorySeverity.LOW

        issue_mapping = {
            "Pest Infestation": IssueType.PEST,
            "Water Stress": IssueType.IRRIGATION,
            "Low Vigour": IssueType.NUTRIENT,
            "Nitrogen Deficiency": IssueType.NUTRIENT,
            "Moisture Excess": IssueType.IRRIGATION
        }

        # Filter farms like data.js
        layyah_farms_data = [f for f in farms_data if (f.get("lon") and f.get("lon") < 72.5)]
        flagged_farms_data = [f for f in layyah_farms_data if get_issue(f)]
        todays_farms_data = flagged_farms_data[:9]

        for i, f_data in enumerate(todays_farms_data):
            numeric_id = int(str(f_data["id"]).replace("farm-", ""))
            issue = get_issue(f_data)
            
            case = AdvisoryCase(
                cycleId=cycle.id,
                farmId=numeric_id,
                serviceCenterId=sc1.id,
                kind=AdvisoryCaseKind.FARM_LEVEL,
                issueType=issue_mapping.get(issue, IssueType.PEST),
                severity=get_severity(f_data),
                state=AdvisoryCaseState.RECEIVED,
                text=advisory_text(issue, f_data)
            )
            db.add(case)
            db.flush()

            # Advance state for some (based on data.js mkTimeline logic)
            sNo = f_data.get("sNo", 0)
            # Assign an agent
            ag_idx = i % len(agents)
            case.assignedAgentId = agents[ag_idx].id
            
            if i < 3:
                # Received/Assigned
                case.state = AdvisoryCaseState.PENDING_VERIFICATION
            elif 3 <= i <= 6:
                # Verified
                case.state = AdvisoryCaseState.VERIFIED_CONFIRMED
                db.add(AdvisoryVerification(advisoryCaseId=case.id, agentId=agents[ag_idx].id, outcome=VerificationOutcome.CONFIRMED, observations="Confirmed on ground"))
                db.add(AdvisoryFeedback(advisoryCaseId=case.id, recordedById=manager.id, outcome=VerificationOutcome.CONFIRMED, explanation="Looks accurate", returnedToAgrobot=True))
                case.state = AdvisoryCaseState.FEEDBACK_RECORDED
            elif i == 7:
                # Forwarded
                case.state = AdvisoryCaseState.FORWARDED
                db.add(AdvisoryForwarding(advisoryCaseId=case.id, forwardedById=manager.id, deliveredToFarmerApp=True))
            elif i == 8:
                # Closed
                case.state = AdvisoryCaseState.CLOSED_NOT_FORWARDED
                db.add(AdvisoryClosure(advisoryCaseId=case.id, closedById=manager.id, reason="Issue resolved itself before verification"))

            db.add(AdvisoryEvent(advisoryCaseId=case.id, label="RECEIVED", stateSnapshot=AdvisoryCaseState.RECEIVED))

        # 5. Mock COGs
        try:
            upload_mock_cogs(db_farms, cycle.id, logger)
        except Exception as e:
            logger.warning(f"Could not upload mock COGs (MinIO might not be ready): {e}")

        # 6. Service Catalogue
        logger.info("Creating Service Catalogue & Requests...")
        s1 = Service(name="Tractor + Rotavator", rate=2500)
        s2 = Service(name="Laser Land Leveler", rate=4500)
        s3 = Service(name="Drone Spraying", rate=1800)
        p1 = Product(name="Urea Fertilizer 50kg", rate=4000)
        db.add_all([s1, s2, s3, p1])
        db.flush()

        layyah_farms = [f for f in db_farms if f.serviceCenterId == sc1.id]
        from redis_client import enqueue_request
        import time
        for i in range(5):
            if i >= len(layyah_farms): break
            farm = layyah_farms[i]
            sr = ServiceRequest(
                farmId=farm.id, serviceId=s1.id if i % 2 == 0 else s2.id,
                serviceCenterId=sc1.id, basePrice=2500,
                status=ServiceRequestStatus.PENDING if i < 2 else ServiceRequestStatus.IN_PROGRESS
            )
            db.add(sr)
            db.flush()
            enqueue_request(sc1.id, sr.id, time.time())

        db.commit()
        logger.info("Database successfully seeded!")
        logger.info("Login credentials:")
        logger.info(f"  Manager: {manager_email} / {manager_password}")
        logger.info(f"  Chief: {chief_email} / {chief_password}")

    except Exception as e:
        db.rollback()
        logger.error(f"Seeding failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
