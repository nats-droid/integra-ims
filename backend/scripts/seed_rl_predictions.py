"""
Seed rl_predictions from thickness readings.
Compute corrosion rate per CML via linear regression,
then calculate remaining life = (current_thickness - t_required_manual) / corrosion_rate
"""

import os
import uuid
from datetime import datetime, timezone
import numpy as np
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://enppairwpjtmrgrvzxio.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "sb_secret_W5llKdtM4NXPWFVrXXdiBQ_0lLMY_PN")
COMPANY_ID = "c704d7e6-07fb-48a2-9152-564434d8653f"

db = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_all(table, select, filters={}):
    all_rows = []
    offset = 0
    while True:
        q = db.table(table).select(select)
        for k, v in filters.items():
            q = q.eq(k, v)
        batch = q.range(offset, offset + 999).execute()
        all_rows.extend(batch.data)
        if len(batch.data) < 1000:
            break
        offset += 1000
    return all_rows

print("Fetching CML points...")
cmls = fetch_all("cml_points", "id, equipment_id, nominal_thickness, t_required_manual", {"company_id": COMPANY_ID})
print(f"  {len(cmls)} CMLs")

print("Fetching thickness readings...")
readings = fetch_all("thickness_readings", "cml_point_id, reading_mm, reading_date", {"company_id": COMPANY_ID})
print(f"  {len(readings)} readings")

# Group readings by CML
readings_by_cml = {}
for r in readings:
    readings_by_cml.setdefault(r["cml_point_id"], []).append(r)

# Delete existing rl_predictions for ML equipment (not original 2)
print("Computing RL predictions...")
rows = []
skipped = 0

for cml in cmls:
    cml_id = cml["id"]
    t_req = cml.get("t_required_manual")
    if not t_req or t_req <= 0:
        skipped += 1
        continue

    cml_readings = sorted(readings_by_cml.get(cml_id, []), key=lambda r: r["reading_date"])
    if len(cml_readings) < 2:
        skipped += 1
        continue

    years = np.array([float(r["reading_date"][:4]) for r in cml_readings])
    thicknesses = np.array([float(r["reading_mm"]) for r in cml_readings])

    # Linear regression
    coeffs = np.polyfit(years, thicknesses, 1)
    slope = coeffs[0]  # mm/yr (negative = corrosion)
    corrosion_rate = max(-slope, 0.001)  # ensure positive

    current_thickness = thicknesses[-1]
    remaining_life = (current_thickness - t_req) / corrosion_rate

    if remaining_life < 0:
        remaining_life = 0

    # Cap at 30 years
    remaining_life = min(remaining_life, 30.0)
    confidence_low = max(remaining_life * 0.8, 0)
    confidence_high = min(remaining_life * 1.2, 30.0)

    rows.append({
        "id": str(uuid.uuid4()),
        "company_id": COMPANY_ID,
        "cml_point_id": cml_id,
        "predicted_rl_years": round(remaining_life, 2),
        "confidence_low": round(confidence_low, 2),
        "confidence_high": round(confidence_high, 2),
        "model_version": "seed_v1",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    })

print(f"  Computed: {len(rows)}, Skipped: {skipped}")

# Insert in batches
print("Inserting rl_predictions...")
batch_size = 500
for i in range(0, len(rows), batch_size):
    db.table("rl_predictions").insert(rows[i:i+batch_size]).execute()
    print(f"  {min(i+batch_size, len(rows))}/{len(rows)}")

print(f"DONE — {len(rows)} rl_predictions inserted")
