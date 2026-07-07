from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import verify_jwt
from app.services import (
    remaining_life,
    anomaly_detection,
    fleet_risk,
    data_quality,
    inspector_quality,
    ai_insight,
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


@router.post("/analytics/dm-validation/{company_id}")
async def compute_dm_validation(
    company_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Validate DM Screener accuracy against field findings
    for all equipment in a company.
    Compares predicted Active DM codes with keywords in
    checklist_answers inspection notes.
    """
    from app.services import dm_accuracy

    result = await dm_accuracy.compute(company_id)
    return result


@router.get("/analytics/dm-validation/{equipment_id}/latest")
async def get_latest_dm_validation(
    equipment_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Get latest DM accuracy validation result for an equipment.
    Returns single row (latest by computed_at) or null.
    """
    from app.core.database import get_db

    db = get_db()
    result = (
        db.table("dm_validation_results")
        .select("*")
        .eq("equipment_id", equipment_id)
        .order("computed_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


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


@router.get("/analytics/inspector-quality/{company_id}")
async def get_inspector_quality(
    company_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Compute inspector quality scores — precise via thickness_reading_id.
    Supervisor view only.
    """
    result = await inspector_quality.compute(company_id)
    return result


# ── AI Insight Endpoints ────────────────────────────────────────────────────

@router.get("/ai/status/{company_id}")
async def get_ai_status(
    company_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Check if LLM is configured for this company.
    Returns {has_key, provider} — never exposes the api_key.
    """
    config = ai_insight.get_company_llm_config(company_id)
    return {"has_key": config["has_key"], "provider": config["provider"]}


class QARequest(BaseModel):
    question: str


@router.post("/ai/insight/{company_id}")
async def generate_ai_insight(
    company_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Generate AI insight for a company.
    Always returns rule_based insights.
    If LLM is configured, also returns ai_narrative.
    """
    from datetime import datetime, timezone

    rule_based = ai_insight.generate_rule_based_insights(company_id)
    config = ai_insight.get_company_llm_config(company_id)
    context_summary = ai_insight.build_context(company_id)
    computed_at = datetime.now(timezone.utc).isoformat()

    ai_narrative = None
    error = None

    if config["has_key"]:
        try:
            prompt = (
                "You are an asset integrity expert for petrochemical plants. "
                "Based on the following data summary, provide a concise narrative "
                "analysis with key risks, recommendations, and priority actions.\n\n"
                f"{context_summary}"
            )
            ai_narrative = ai_insight.call_llm(prompt, config["provider"], config["api_key"])
        except ValueError as e:
            error = str(e)

    return {
        "rule_based": rule_based,
        "ai_narrative": ai_narrative,
        "context_summary": context_summary,
        "computed_at": computed_at,
        "error": error,
    }


@router.post("/ai/qa/{company_id}")
async def ask_ai_question(
    company_id: str,
    body: QARequest,
    user: dict = Depends(verify_jwt),
):
    """
    Q&A endpoint — ask a question about asset integrity.
    Requires LLM API key configured.
    """
    try:
        answer = ai_insight.answer_qa(body.question, company_id)
        return {"answer": answer, "error": None}
    except ValueError as e:
        return {"answer": None, "error": str(e)}
