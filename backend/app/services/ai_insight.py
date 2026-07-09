"""
AI Insight Service
- LLM config from companies table (llm_provider, llm_api_key)
- Context builder (asset integrity summary)
- LLM callers (Gemini, OpenAI)
- Rule-based insight generator
- Q&A via LLM
"""
import json
import httpx
from datetime import datetime, timezone

from app.core.database import get_db


# ── LLM Config ──────────────────────────────────────────────────────────────

def get_company_llm_config(company_id: str) -> dict:
    """Return {provider, has_key, api_key} from companies table."""
    db = get_db()
    result = (
        db.table("companies")
        .select("llm_provider, llm_api_key")
        .eq("id", company_id)
        .single()
        .execute()
    )
    row = result.data or {}
    provider = row.get("llm_provider")
    api_key = row.get("llm_api_key")
    return {
        "provider": provider,
        "has_key": bool(provider and api_key),
        "api_key": api_key,  # internal use only — never expose in endpoint
    }


# ── Context Builder ─────────────────────────────────────────────────────────

def build_context(company_id: str) -> str:
    """Build a text summary of the company's asset integrity state."""
    db = get_db()

    # Company name
    comp = db.table("companies").select("name").eq("id", company_id).single().execute()
    company_name = (comp.data or {}).get("name", "Unknown")

    # Total equipment + compliance rate
    equip_result = (
        db.table("equipment")
        .select("id, compliance_status")
        .eq("company_id", company_id)
        .execute()
    )
    equips = equip_result.data or []
    total_equip = len(equips)
    compliant = sum(1 for e in equips if e.get("compliance_status") == "compliant")
    compliance_rate = (compliant / total_equip * 100) if total_equip > 0 else 0

    # Overdue inspections
    now_iso = datetime.now(timezone.utc).isoformat()
    plans_result = (
        db.table("inspection_plans")
        .select("id, equipment_id, final_due_date, is_active")
        .eq("company_id", company_id)
        .eq("is_active", True)
        .execute()
    )
    plans = plans_result.data or []
    overdue_count = sum(
        1 for p in plans
        if p.get("final_due_date") and p["final_due_date"] < now_iso
    )

    # Top 3 CML corrosion rate (from rl_predictions)
    rl_result = (
        db.table("rl_predictions")
        .select("cml_point_id, predicted_rl_years, confidence_low")
        .eq("company_id", company_id)
        .order("predicted_rl_years")
        .limit(3)
        .execute()
    )
    top_rl = rl_result.data or []

    # Anomalies count + avg z-score
    anomaly_result = (
        db.table("corrosion_anomalies")
        .select("id, anomaly_score")
        .eq("company_id", company_id)
        .execute()
    )
    anomalies = anomaly_result.data or []
    anomaly_count = len(anomalies)
    avg_score = (
        sum(a.get("anomaly_score", 0) for a in anomalies) / anomaly_count
        if anomaly_count > 0
        else 0
    )

    # Critical RL count (confidence_low < 2 years)
    critical_rl = sum(
        1 for r in (rl_result.data or [])
        if r.get("confidence_low") is not None and r["confidence_low"] < 2.0
    )
    # Also check full RL list for critical count
    all_rl = (
        db.table("rl_predictions")
        .select("confidence_low")
        .eq("company_id", company_id)
        .execute()
    )
    critical_rl_total = sum(
        1 for r in (all_rl.data or [])
        if r.get("confidence_low") is not None and r["confidence_low"] < 2.0
    )

    # Fleet risk latest snapshot
    fleet_result = (
        db.table("fleet_risk_snapshots")
        .select("risk_summary, computed_at")
        .eq("company_id", company_id)
        .order("computed_at", desc=True)
        .limit(1)
        .execute()
    )
    fleet_snapshot = (fleet_result.data or [None])[0]
    fleet_summary = fleet_snapshot.get("risk_summary", {}) if fleet_snapshot else {}
    fleet_areas = fleet_summary.get("areas", [])
    critical_areas = [a for a in fleet_areas if a.get("risk_level") == "critical"]
    high_areas = [a for a in fleet_areas if a.get("risk_level") == "high"]

    # Format top CML lines
    top_cml_lines = ""
    for i, r in enumerate(top_rl, 1):
        rl = r.get("predicted_rl_years", 0)
        cl = r.get("confidence_low")
        top_cml_lines += f"\n  {i}. CML {r['cml_point_id']}: predicted_rl={rl:.1f}yr, RL_low={cl:.1f}yr" if cl else f"\n  {i}. CML {r['cml_point_id']}: predicted_rl={rl:.1f}yr"

    # Fleet risk summary line
    if critical_areas:
        fleet_line = f"CRITICAL: {len(critical_areas)} area(s) at critical risk: {', '.join(a.get('area_name','?') for a in critical_areas)}"
    elif high_areas:
        fleet_line = f"WARNING: {len(high_areas)} area(s) at high risk: {', '.join(a.get('area_name','?') for a in high_areas)}"
    elif fleet_areas:
        fleet_line = "All areas within acceptable risk levels"
    else:
        fleet_line = "No fleet risk data available"

    context = (
        f"ASSET INTEGRITY SUMMARY — {company_name}\n"
        f"=========================================\n"
        f"Total Equipment: {total_equip}\n"
        f"Compliance Rate: {compliance_rate:.1f}%\n"
        f"Overdue Inspections: {overdue_count}\n"
        f"\n"
        f"Top 3 CML Corrosion Rates:{top_cml_lines}\n"
        f"\n"
        f"Active Anomalies: {anomaly_count} (avg anomaly score: {avg_score:.2f})\n"
        f"Critical Remaining Life (<2yr): {critical_rl_total} CML points\n"
        f"\n"
        f"Fleet Risk: {fleet_line}"
    )
    return context


# ── LLM Callers ─────────────────────────────────────────────────────────────

def call_llm(prompt: str, provider: str, api_key: str) -> str:
    """Call LLM API and return text response. Raises ValueError on errors."""
    timeout = httpx.Timeout(35.0, connect=10.0)

    if provider == "gemini":
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/gemini-2.0-flash:generateContent"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.3},
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
        except httpx.TimeoutException:
            raise ValueError("timeout")

        if resp.status_code in (400, 401, 403):
            raise ValueError("invalid_api_key")
        if resp.status_code == 429:
            raise ValueError("rate_limit")
        if resp.status_code != 200:
            raise ValueError("llm_error")

        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise ValueError("llm_error")

    elif provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are an asset integrity expert for petrochemical plants."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
            "temperature": 0.3,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
        except httpx.TimeoutException:
            raise ValueError("timeout")

        if resp.status_code in (400, 401, 403):
            raise ValueError("invalid_api_key")
        if resp.status_code == 429:
            raise ValueError("rate_limit")
        if resp.status_code != 200:
            raise ValueError("llm_error")

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise ValueError("llm_error")

    else:
        raise ValueError(f"llm_error: unsupported provider '{provider}'")


# ── Rule-Based Insights ─────────────────────────────────────────────────────

def generate_rule_based_insights(company_id: str) -> list[dict]:
    """Generate rule-based insight cards from data (no LLM needed)."""
    db = get_db()
    insights: list[dict] = []

    # --- Executive Summary ---
    equip_result = (
        db.table("equipment")
        .select("id, compliance_status")
        .eq("company_id", company_id)
        .execute()
    )
    equips = equip_result.data or []
    total_equip = len(equips)
    compliant = sum(1 for e in equips if e.get("compliance_status") == "compliant")
    compliance_rate = (compliant / total_equip * 100) if total_equip > 0 else 0

    insights.append({
        "type": "info",
        "title": "Executive Summary",
        "body": f"{total_equip} equipment tracked. Compliance rate: {compliance_rate:.1f}%.",
        "metrics": [
            {"label": "Total Equipment", "value": str(total_equip)},
            {"label": "Compliance Rate", "value": f"{compliance_rate:.1f}%"},
        ],
    })

    # --- Critical Equipment (RL < 2yr) ---
    rl_result = (
        db.table("rl_predictions")
        .select("cml_point_id, confidence_low, predicted_rl_years")
        .eq("company_id", company_id)
        .execute()
    )
    critical_cmls = [
        r for r in (rl_result.data or [])
        if r.get("confidence_low") is not None and r["confidence_low"] < 2.0
    ]

    if critical_cmls:
        worst = min(critical_cmls, key=lambda r: r["confidence_low"])
        insights.append({
            "type": "crit",
            "title": "Critical Equipment",
            "body": f"{len(critical_cmls)} CML point(s) have remaining life < 2 years. "
                    f"Shortest: {worst['confidence_low']:.1f} years (CML {worst['cml_point_id']}).",
            "metrics": [
                {"label": "Critical CMLs", "value": str(len(critical_cmls))},
                {"label": "Shortest RL", "value": f"{worst['confidence_low']:.1f} yr"},
            ],
        })

    # --- Anomaly Alert ---
    anomaly_result = (
        db.table("corrosion_anomalies")
        .select("id, anomaly_score")
        .eq("company_id", company_id)
        .execute()
    )
    anomalies = anomaly_result.data or []
    if anomalies:
        avg_score = sum(a.get("anomaly_score", 0) for a in anomalies) / len(anomalies)
        insights.append({
            "type": "warn",
            "title": "Anomaly Alert",
            "body": f"{len(anomalies)} active corrosion anomalies detected. Average anomaly score: {avg_score:.2f}.",
            "metrics": [
                {"label": "Active Anomalies", "value": str(len(anomalies))},
                {"label": "Avg Anomaly Score", "value": f"{avg_score:.2f}"},
            ],
        })

    # --- Fleet Risk ---
    fleet_result = (
        db.table("fleet_risk_snapshots")
        .select("risk_summary, computed_at")
        .eq("company_id", company_id)
        .order("computed_at", desc=True)
        .limit(1)
        .execute()
    )
    fleet_snapshot = (fleet_result.data or [None])[0]
    if fleet_snapshot:
        summary = fleet_snapshot.get("risk_summary", {})
        areas = summary.get("areas", [])
        critical = [a for a in areas if a.get("risk_level") == "critical"]
        high = [a for a in areas if a.get("risk_level") == "high"]

        if critical:
            insights.append({
                "type": "crit",
                "title": "Fleet Risk: Critical",
                "body": f"{len(critical)} area(s) at critical risk: {', '.join(a.get('area_name','?') for a in critical)}.",
                "metrics": [
                    {"label": "Critical Areas", "value": str(len(critical))},
                    {"label": "Total Areas", "value": str(len(areas))},
                ],
            })
        elif high:
            insights.append({
                "type": "warn",
                "title": "Fleet Risk: High",
                "body": f"{len(high)} area(s) at high risk: {', '.join(a.get('area_name','?') for a in high)}.",
                "metrics": [
                    {"label": "High-Risk Areas", "value": str(len(high))},
                    {"label": "Total Areas", "value": str(len(areas))},
                ],
            })
        elif areas:
            insights.append({
                "type": "ok",
                "title": "Fleet Risk: Normal",
                "body": "All plant areas within acceptable risk levels.",
                "metrics": [
                    {"label": "Total Areas", "value": str(len(areas))},
                ],
            })

    # --- All Compliant ---
    if compliance_rate > 80:
        insights.append({
            "type": "ok",
            "title": "Compliance Status",
            "body": f"Compliance rate at {compliance_rate:.1f}% — above 80% threshold.",
            "metrics": [
                {"label": "Compliance", "value": f"{compliance_rate:.1f}%"},
            ],
        })

    return insights


# ── Q&A ─────────────────────────────────────────────────────────────────────

def answer_qa(question: str, company_id: str) -> str:
    """Answer a question using LLM with asset integrity context."""
    config = get_company_llm_config(company_id)
    if not config["has_key"]:
        raise ValueError("no_api_key")

    context = build_context(company_id)
    prompt = (
        "You are an asset integrity expert for petrochemical plants. Be concise and precise.\n\n"
        f"{context}\n\n"
        f"Question: {question}"
    )
    return call_llm(prompt, config["provider"], config["api_key"])
