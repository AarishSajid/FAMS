import sys
import os
import json
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.advisory import AdvisoryCase
from models.cycle import Cycle
from enums import AdvisoryCaseKind, AdvisorySeverity, IssueType, AdvisoryCaseState

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

def inject_more_advisories():
    db = SessionLocal()
    try:
        cycle = db.query(Cycle).filter(Cycle.active == True).first()
        if not cycle:
            print("No active cycle found. Cannot add advisories.")
            return

        farms_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "lib", "farms.json")
        with open(farms_path, "r") as f:
            farms_data = json.load(f)

        layyah_farms_data = [f for f in farms_data if (f.get("lon") and f.get("lon") < 72.5)]
        flagged_farms_data = [f for f in layyah_farms_data if get_issue(f)]
        
        # Original seeder took the first 9. We'll take the rest up to 50
        additional_farms = flagged_farms_data[9:50]
        
        issue_mapping = {
            "Pest Infestation": IssueType.PEST,
            "Water Stress": IssueType.IRRIGATION,
            "Low Vigour": IssueType.NUTRIENT,
            "Nitrogen Deficiency": IssueType.NUTRIENT,
            "Moisture Excess": IssueType.IRRIGATION
        }

        count = 0
        for f_data in additional_farms:
            numeric_id = int(str(f_data["id"]).replace("farm-", ""))
            
            # Check if this farm already has an advisory for this cycle
            existing = db.query(AdvisoryCase).filter(
                AdvisoryCase.farmId == numeric_id,
                AdvisoryCase.cycleId == cycle.id
            ).first()
            
            if existing:
                continue

            issue = get_issue(f_data)
            
            case = AdvisoryCase(
                cycleId=cycle.id,
                farmId=numeric_id,
                serviceCenterId=1, # Default layyah center id is 1
                kind=AdvisoryCaseKind.FARM_LEVEL,
                issueType=issue_mapping.get(issue, IssueType.PEST),
                severity=get_severity(f_data),
                state=AdvisoryCaseState.RECEIVED,
                text=advisory_text(issue, f_data)
            )
            db.add(case)
            count += 1
            
        db.commit()
        print(f"Successfully injected {count} additional advisories!")
        
    finally:
        db.close()

if __name__ == "__main__":
    inject_more_advisories()
