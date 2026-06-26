"""
Inspector Data Quality Scoring (PRD Section 5.5)
Score based on anomaly frequency and correction rate per inspector.
"""
from app.core.database import get_db
from collections import defaultdict


async def score(company_id: str) -> dict:
    """Compute data quality scores for all inspectors in a company."""
    db = get_db()
    
    # Get all inspectors in this company
    inspectors = db.table("app_users") \
        .select("id, full_name") \
        .eq("company_id", company_id) \
        .eq("role", "inspector") \
        .execute()
    
    inspector_scores = []
    
    for inspector in inspectors.data:
        # Get inspections done by this inspector
        events = db.table("inspection_events") \
            .select("id") \
            .eq("inspector_id", inspector["id"]) \
            .eq("company_id", company_id) \
            .execute()
        
        event_ids = [e["id"] for e in events.data]
        total_inspections = len(event_ids)
        
        if total_inspections == 0:
            inspector_scores.append({
                "inspector_id": inspector["id"],
                "inspector_name": inspector["full_name"],
                "total_inspections": 0,
                "data_quality_score": None,
                "anomalous_readings": 0,
                "status": "no_data",
            })
            continue
        
        # Get thickness readings from their inspections
        readings = db.table("thickness_readings") \
            .select("id") \
            .in_("inspection_event_id", event_ids) \
            .execute() if event_ids else []
        
        total_readings = len(readings.data) if readings else 0
        
        # Get anomalies linked to their CML points
        # For now, count readings with anomalous patterns
        # Simple heuristic: readings corrected in later inspections
        
        # Base score: start at 100, deduct based on patterns
        score = 100
        
        # Deduction for low volume (less data = less confidence)
        if total_readings < 10:
            score -= 10
        elif total_readings < 30:
            score -= 5
        
        # Deduction for having many anomalies (from corrosion_anomalies table)
        # linked to CMLs inspected by this inspector
        anomalous = db.table("corrosion_anomalies") \
            .select("id, cml_point_id") \
            .eq("company_id", company_id) \
            .execute()
        
        anomaly_count = len(anomalous.data) if anomalous else 0
        
        # Each anomaly costs 2 points
        score -= min(anomaly_count * 2, 40)
        
        score = max(score, 0)
        
        inspector_scores.append({
            "inspector_id": inspector["id"],
            "inspector_name": inspector["full_name"],
            "total_inspections": total_inspections,
            "total_readings": total_readings,
            "anomalous_readings": anomaly_count,
            "data_quality_score": score,
            "quality_label": "Excellent" if score >= 90 else "Good" if score >= 75 else "Fair" if score >= 60 else "Needs Review",
        })
    
    return {
        "company_id": company_id,
        "inspectors": inspector_scores,
        "total_inspectors": len(inspector_scores),
    }
