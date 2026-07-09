from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

from app.api.auth import verify_jwt
from app.core.database import get_db
from supabase import Client
from app.services import (
    remaining_life,
    anomaly_detection,
    fleet_risk,
    data_quality,
    inspector_quality,
    ai_insight,
    notification,
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


@router.post("/ai/config/{company_id}")
async def save_ai_config(
    company_id: str,
    request: Request,
    user: dict = Depends(verify_jwt),
):
    """Save LLM provider and API key for a company."""
    try:
        body = await request.json()
        provider = body.get("provider", "").strip()
        api_key = body.get("api_key", "").strip()

        if not provider or not api_key:
            return JSONResponse(
                status_code=400,
                content={"error": "provider and api_key are required"},
            )

        if provider not in ("gemini", "openai", "openrouter"):
            return JSONResponse(
                status_code=400,
                content={"error": "provider must be gemini or openai"},
            )

        db = get_db()
        db.table("companies").update({
            "llm_provider": provider,
            "llm_api_key": api_key,
        }).eq("id", company_id).execute()

        return {"success": True, "provider": provider}

    except Exception as e:
        logger.error(f"save_ai_config error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


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


# ── Notification Endpoints ──────────────────────────────────────────────────

@router.post("/notifications/run")
async def run_notifications(
    x_cron_secret: str = Header(None, alias="X-Cron-Secret"),
):
    """
    Cron endpoint — generate due-date notifications for all companies.
    No JWT auth. Secured via X-Cron-Secret header.
    """
    import os
    expected = os.getenv("CRON_SECRET", "")
    if not expected:
        raise HTTPException(status_code=500, detail="CRON_SECRET not configured")
    if x_cron_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    result = notification.run_for_all_companies()
    return result


@router.get("/notifications/me")
async def get_my_notifications(
    user: dict = Depends(verify_jwt),
):
    """
    Get notifications for the current user's company.
    Returns notifications list + unread_count.
    Joins inspection_plans to include equipment_id for frontend redirect.
    """
    from app.core.database import get_db

    db = get_db()
    company_id = user.get("company_id")

    # If company_id not in JWT, look up from app_users table
    if not company_id:
        user_id = user.get("user_id")
        if user_id:
            app_user = (
                db.table("app_users")
                .select("company_id")
                .eq("auth_user_id", user_id)
                .maybe_single()
                .execute()
            )
            company_id = (app_user.data or {}).get("company_id")

    if not company_id:
        return {"notifications": [], "unread_count": 0}

    # Fetch notifications
    result = (
        db.table("notifications")
        .select("*")
        .eq("company_id", company_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    notifs = result.data or []

    # Unread count
    unread_result = (
        db.table("notifications")
        .select("id", count="exact")
        .eq("company_id", company_id)
        .eq("is_read", False)
        .execute()
    )
    unread_count = unread_result.count if unread_result.count is not None else 0

    # Join: get equipment_id from inspection_plans for plan-related notifs
    plan_ids = list({n["related_id"] for n in notifs if n.get("related_id")})
    equipment_map: dict[str, str] = {}
    if plan_ids:
        plans_result = (
            db.table("inspection_plans")
            .select("id, equipment_id")
            .in_("id", plan_ids)
            .execute()
        )
        for p in (plans_result.data or []):
            equipment_map[p["id"]] = p.get("equipment_id")

    # Attach equipment_id to each notification
    enriched = []
    for n in notifs:
        enriched.append({
            **n,
            "equipment_id": equipment_map.get(n.get("related_id")),
        })

    return {"notifications": enriched, "unread_count": unread_count}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: dict = Depends(verify_jwt),
):
    """
    Mark a single notification as read.
    Scoped to user's company (RLS safety).
    """
    from app.core.database import get_db

    db = get_db()
    company_id = user.get("company_id")

    # If company_id not in JWT, look up from app_users table
    if not company_id:
        user_id = user.get("user_id")
        if user_id:
            app_user = (
                db.table("app_users")
                .select("company_id")
                .eq("auth_user_id", user_id)
                .maybe_single()
                .execute()
            )
            company_id = (app_user.data or {}).get("company_id")

    if not company_id:
        raise HTTPException(status_code=400, detail="Company not found")

    result = (
        db.table("notifications")
        .update({"is_read": True})
        .eq("id", notification_id)
        .eq("company_id", company_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"success": True}
