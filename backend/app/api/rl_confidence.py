"""
RL Confidence Band API
=======================
POST /api/v1/rl-confidence/calculate/{cml_point_id}  — single CML
POST /api/v1/rl-confidence/recalculate               — batch all CMLs for company

Does NOT touch inspection_plans.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from app.core.database import get_db
from app.api.auth import verify_jwt
from app.services.rl_confidence import calculate_cml_confidence
from supabase import Client

router = APIRouter(prefix="/api/v1/rl-confidence", tags=["RL Confidence"])


def _resolve_company_id(user: dict, db: Client) -> str:
    """Get company_id from JWT or fallback to app_users lookup."""
    company_id = user.get("company_id")
    if not company_id:
        user_id = user.get("user_id")
        if user_id:
            user_row = db.table("app_users").select("company_id").eq("auth_user_id", user_id).execute()
            if user_row.data:
                company_id = user_row.data[0].get("company_id")
    return company_id


def _upsert_prediction(db: Client, cml_point_id: str, company_id: str, calc: dict):
    """Upsert calc result to rl_predictions. Only called for successful calculations."""
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "cml_point_id": cml_point_id,
        "company_id": company_id,
        "predicted_rl_years": calc["predicted_rl_years"],
        "confidence_low": calc["confidence_low"],
        "confidence_high": calc["confidence_high"],
        "model_version": calc["model_version"],
        "computed_at": now,
    }
    existing = (
        db.table("rl_predictions")
        .select("id")
        .eq("cml_point_id", cml_point_id)
        .eq("company_id", company_id)
        .execute()
    )
    if existing.data:
        db.table("rl_predictions").update(row).eq("id", existing.data[0]["id"]).execute()
    else:
        db.table("rl_predictions").insert(row).execute()


@router.post("/calculate/{cml_point_id}")
async def calculate_single(
    cml_point_id: str,
    user: dict = Depends(verify_jwt),
    db: Client = Depends(get_db),
):
    """Calculate RL with confidence band for one CML point, upsert to rl_predictions."""
    company_id = _resolve_company_id(user, db)
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id missing from token and user profile")

    # Get CML metadata
    cml_resp = (
        db.table("cml_points")
        .select("id, t_min, t_required_manual, nominal_thickness, retirement_factor, location_label, circuit_id")
        .eq("id", cml_point_id)
        .eq("company_id", company_id)
        .execute()
    )
    if not cml_resp.data:
        raise HTTPException(status_code=404, detail="CML point not found")
    cml = cml_resp.data[0]

    t_required = cml.get("t_required_manual")

    # Get readings
    readings_resp = (
        db.table("thickness_readings")
        .select("reading_date, reading_mm")
        .eq("cml_point_id", cml_point_id)
        .eq("company_id", company_id)
        .order("reading_date")
        .execute()
    )
    readings = readings_resp.data or []

    # Calculate
    calc = calculate_cml_confidence(readings, t_required)

    # Handle non-success statuses
    if calc["status"] == "missing_t_required":
        return {
            "cml_point_id": cml_point_id,
            "cml_label": cml.get("location_label"),
            "status": "missing_t_required",
            "message": calc["message"],
            "saved_to_db": False,
        }

    if calc["status"] in ("no_readings", "insufficient_data"):
        return {
            "cml_point_id": cml_point_id,
            "cml_label": cml.get("location_label"),
            "status": calc["status"],
            "n_readings": len(readings),
            "saved_to_db": False,
        }

    # Success — upsert
    _upsert_prediction(db, cml_point_id, company_id, calc)

    return {
        "cml_point_id": cml_point_id,
        "cml_label": cml.get("location_label"),
        **calc,
        "saved_to_db": True,
    }


@router.post("/recalculate")
async def recalculate_all(
    user: dict = Depends(verify_jwt),
    db: Client = Depends(get_db),
):
    """Batch recalculate RL for ALL CML points belonging to the user's company.
    Skips CMLs without t_required_manual (does not error/stop).
    Does NOT touch inspection_plans.
    """
    company_id = _resolve_company_id(user, db)
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id missing from token and user profile")

    # Get all CML points for this company
    cmls = (
        db.table("cml_points")
        .select("id, t_required_manual, location_label")
        .eq("company_id", company_id)
        .execute()
    )
    if not cmls.data:
        return {"calculated": 0, "skipped": [], "errors": [], "total_cml": 0}

    calculated = 0
    skipped = []
    errors = []

    for cml in cmls.data:
        cml_id = cml["id"]
        label = cml.get("location_label", cml_id[:8])
        t_required = cml.get("t_required_manual")

        # Skip if t_required not set
        if t_required is None:
            skipped.append({
                "cml_point_id": cml_id,
                "cml_label": label,
                "reason": "missing_t_required",
            })
            continue

        # Get readings
        try:
            readings_resp = (
                db.table("thickness_readings")
                .select("reading_date, reading_mm")
                .eq("cml_point_id", cml_id)
                .eq("company_id", company_id)
                .order("reading_date")
                .execute()
            )
            readings = readings_resp.data or []

            calc = calculate_cml_confidence(readings, t_required)

            if calc["status"] == "success":
                _upsert_prediction(db, cml_id, company_id, calc)
                calculated += 1
            elif calc["status"] == "missing_t_required":
                # Shouldn't happen (we checked above), but handle gracefully
                skipped.append({
                    "cml_point_id": cml_id,
                    "cml_label": label,
                    "reason": "missing_t_required",
                })
            else:
                # no_readings, insufficient_data
                skipped.append({
                    "cml_point_id": cml_id,
                    "cml_label": label,
                    "reason": calc["status"],
                })
        except Exception as e:
            errors.append({
                "cml_point_id": cml_id,
                "cml_label": label,
                "error": str(e),
            })

    return {
        "calculated": calculated,
        "skipped": skipped,
        "errors": errors,
        "total_cml": len(cmls.data),
    }
