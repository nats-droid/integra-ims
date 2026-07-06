"""
Inspector Quality Scoring — PRECISE via thickness_reading_id linkage.
Counts only anomalies whose thickness_reading_id belongs to readings
submitted by the inspector (through inspection_events).
"""
from app.core.database import get_db


async def compute(company_id: str) -> dict:
    """Compute quality scores for all inspectors in a company."""
    db = get_db()

    # 1. Get inspectors
    inspectors = db.table("app_users") \
        .select("id, full_name") \
        .eq("company_id", company_id) \
        .eq("role", "inspector") \
        .execute()

    results = []

    for insp in inspectors.data:
        inspector_id = insp["id"]

        # 2. Get inspection events for this inspector
        events = db.table("inspection_events") \
            .select("id") \
            .eq("inspector_id", inspector_id) \
            .execute()
        event_ids = [e["id"] for e in events.data]

        if not event_ids:
            results.append({
                "inspector_id": inspector_id,
                "full_name": insp["full_name"],
                "total_readings": 0,
                "anomaly_count": 0,
                "quality_score": None,
                "badge": "no_data",
            })
            continue

        # 3. Total readings by this inspector
        readings_resp = db.table("thickness_readings") \
            .select("id") \
            .in_("inspection_event_id", event_ids) \
            .execute()
        reading_ids = set(r["id"] for r in readings_resp.data)
        total_readings = len(reading_ids)

        if total_readings == 0:
            results.append({
                "inspector_id": inspector_id,
                "full_name": insp["full_name"],
                "total_readings": 0,
                "anomaly_count": 0,
                "quality_score": None,
                "badge": "no_data",
            })
            continue

        # 4. Anomaly count: precise via thickness_reading_id
        #    Get all anomalies with thickness_reading_id set for this company
        anomalies_resp = db.table("corrosion_anomalies") \
            .select("id, thickness_reading_id") \
            .eq("company_id", company_id) \
            .not_.is_("thickness_reading_id", "null") \
            .execute()

        # Match in Python: anomaly's thickness_reading_id must be in this inspector's reading_ids
        anomaly_count = sum(
            1 for a in anomalies_resp.data
            if a.get("thickness_reading_id") in reading_ids
        )

        # 5. Score
        anomaly_rate = anomaly_count / total_readings
        if anomaly_rate > 1.0:
            anomaly_rate = 1.0
        quality_score = round((1 - anomaly_rate) * 100, 1)

        # 6. Badge
        if quality_score >= 80:
            badge = "good"
        elif quality_score >= 60:
            badge = "fair"
        else:
            badge = "needs_review"

        results.append({
            "inspector_id": inspector_id,
            "full_name": insp["full_name"],
            "total_readings": total_readings,
            "anomaly_count": anomaly_count,
            "quality_score": quality_score,
            "badge": badge,
        })

    return {
        "company_id": company_id,
        "inspectors": results,
        "computed_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
