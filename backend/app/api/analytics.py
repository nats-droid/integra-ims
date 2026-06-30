from fastapi import APIRouter, Depends

from app.api.auth import verify_jwt
from app.services import (
    remaining_life,
    anomaly_detection,
    fleet_risk,
    dm_validation,
    data_quality,
)

router = APIRouter()


@router.post("/analytics/remaining-life/{cml_point_id}")
async def compute_remaining_life(
    cml_point_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Compute Remaining Life prediction for a CML point.
    Trigger: 'Recalculate' button on Equipment detail page.
    """
    result = await remaining_life.predict(cml_point_id, user["company_id"])
    return result


@router.post("/analytics/anomalies/{cml_point_id}")
async def detect_anomalies(
    cml_point_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Detect corrosion rate anomalies for a CML point.
    Uses z-score / IQR against historical rates.
    """
    result = await anomaly_detection.detect(cml_point_id, user["company_id"])
    return result


@router.post("/analytics/anomalies/recalculate")
async def recalculate_anomalies(
    user: dict = Depends(verify_jwt),
):
    """
    Batch anomaly detection for all CML points owned by the user's company.
    """
    from app.core.database import get_db

    db = get_db()
    company_id = user["company_id"]

    # Get all CML points for this company
    cml_result = db.table("cml_points") \
        .select("id,location_label,equipment_id") \
        .eq("company_id", company_id) \
        .eq("is_active", True) \
        .execute()

    cml_points = cml_result.data

    cml_with_anomalies = 0
    total_anomalies = 0
    skipped = 0
    errors = []

    for cml in cml_points:
        try:
            result = await anomaly_detection.detect(cml["id"], company_id)
            if result.get("status") == "insufficient_data":
                skipped += 1
                continue
            count = result.get("anomaly_count", 0)
            if count > 0:
                cml_with_anomalies += 1
                total_anomalies += count
        except Exception as e:
            errors.append({"cml_point_id": cml["id"], "error": str(e)})

    return {
        "total_cml": len(cml_points),
        "cml_with_anomalies": cml_with_anomalies,
        "total_anomalies": total_anomalies,
        "skipped": skipped,
        "errors": len(errors),
    }


@router.post("/analytics/fleet-risk/{company_id}")
async def compute_fleet_risk(
    company_id: str,
    area_id: str = None,
    user: dict = Depends(verify_jwt),
):
    """
    Compute fleet-wide risk heatmap.
    Combines physical condition signals + DM Screener vulnerability signals.
    """
    result = await fleet_risk.compute(company_id, area_id)
    return result


@router.post("/analytics/dm-validate/{equipment_id}")
async def validate_dm_screener(
    equipment_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Validate DM Screener accuracy vs actual findings.
    Compares predicted DM codes with keywords in checklist_answers/maintenance_log.
    """
    result = await dm_validation.validate(equipment_id, user["company_id"])
    return result


@router.post("/analytics/data-quality/{company_id}")
async def compute_data_quality(
    company_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Compute inspector data quality scoring.
    Based on anomaly frequency and correction rate.
    """
    result = await data_quality.score(company_id)
    return result
