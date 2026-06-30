"""
Corrosion Anomaly Detection (PRD Section 5.2)
Trigger-agnostic — uses z-score against CML's own historical corrosion rate distribution.

Approach: Calculate corrosion rate between consecutive readings,
then flag readings where rate deviates significantly from the CML's own history.
"""
import numpy as np
from app.core.database import get_db
from datetime import datetime


async def detect(cml_point_id: str, company_id: str) -> dict:
    """Detect anomalies in corrosion rate for a CML point."""
    db = get_db()
    
    result = db.table("thickness_readings") \
        .select("id, reading_date, reading_mm, notes") \
        .eq("cml_point_id", cml_point_id) \
        .eq("company_id", company_id) \
        .order("reading_date") \
        .execute()
    
    readings = result.data
    
    if not readings or len(readings) < 3:
        return {
            "cml_point_id": cml_point_id,
            "status": "insufficient_data",
            "message": "Minimum 3 readings required",
            "anomalies": [],
        }
    
    # Calculate corrosion rates between consecutive readings
    rates = []
    for i in range(1, len(readings)):
        d1 = datetime.fromisoformat(readings[i]["reading_date"]).date()
        d2 = datetime.fromisoformat(readings[i-1]["reading_date"]).date()
        days_diff = (d1 - d2).days
        if days_diff <= 0:
            continue
        thickness_diff = readings[i-1]["reading_mm"] - readings[i]["reading_mm"]
        rate_mm_year = (thickness_diff / days_diff) * 365
        rates.append({
            "reading_id": readings[i]["id"],
            "reading_date": readings[i]["reading_date"],
            "reading_mm": readings[i]["reading_mm"],
            "rate_mm_year": round(rate_mm_year, 4),
            "days_since_last": days_diff,
        })
    
    if not rates:
        return {
            "cml_point_id": cml_point_id,
            "status": "no_data",
            "message": "Insufficient data to calculate rates",
            "anomalies": [],
        }
    
    if len(rates) < 2:
        return {
            "cml_point_id": cml_point_id,
            "status": "insufficient_data",
            "message": "At least 2 inter-reading intervals required for anomaly detection",
            "anomalies": [],
        }
    
    rate_values = np.array([r["rate_mm_year"] for r in rates])
    
    # Z-score method
    mean_rate = np.mean(rate_values)
    std_rate = np.std(rate_values, ddof=1)
    
    if std_rate == 0:
        return {
            "cml_point_id": cml_point_id,
            "status": "uniform",
            "message": "No variation in corrosion rate — uniform readings",
            "anomalies": [],
        }
    
    anomalies = []
    for r in rates:
        z_score = abs((r["rate_mm_year"] - mean_rate) / std_rate)
        if z_score > 2.0:  # Above 2 standard deviations
            anomalies.append({
                "reading_date": r["reading_date"],
                "reading_mm": r["reading_mm"],
                "rate_mm_year": r["rate_mm_year"],
                "anomaly_score": round(float(z_score), 2),
                "description": f"Corrosion rate {r['rate_mm_year']:.4f} mm/year (mean: {mean_rate:.4f}) — deviation {z_score:.1f}σ",
            })
    
    # Replace anomalies — delete old, insert new (dedup-safe)
    existing = db.table("corrosion_anomalies") \
        .select("id") \
        .eq("cml_point_id", cml_point_id) \
        .eq("company_id", company_id) \
        .execute()
    for row in existing.data:
        db.table("corrosion_anomalies").delete().eq("id", row["id"]).execute()
    
    if anomalies:
        payload = [{
            "company_id": company_id,
            "cml_point_id": cml_point_id,
            "anomaly_score": a["anomaly_score"],
            "description": a["description"],
        } for a in anomalies]
        db.table("corrosion_anomalies").insert(payload).execute()
    
    return {
        "cml_point_id": cml_point_id,
        "status": "success",
        "total_readings": len(readings),
        "mean_cr_mm_year": round(float(mean_rate), 4),
        "std_cr_mm_year": round(float(std_rate), 4),
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
    }
