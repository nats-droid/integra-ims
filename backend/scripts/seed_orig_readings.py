import os, uuid, random
import numpy as np
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://enppairwpjtmrgrvzxio.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "sb_secret_W5llKdtM4NXPWFVrXXdiBQ_0lLMY_PN")
COMPANY_ID = "c704d7e6-07fb-48a2-9152-564434d8653f"
db = create_client(SUPABASE_URL, SUPABASE_KEY)
random.seed(99)

INSPECTION_YEARS = [2005, 2010, 2015, 2020, 2025]

# Get original equipment CMLs
import re
all_eq = db.table("equipment").select("id, tag, type").eq("company_id", COMPANY_ID).execute()
ml_pattern = re.compile(r"^(P|V|HE)-\d{4}$")
orig_ids = [e["id"] for e in all_eq.data if not ml_pattern.match(e["tag"])]

cmls = db.table("cml_points").select("id, equipment_id, nominal_thickness, t_required_manual").filter("equipment_id", "in", f"({','.join(orig_ids)})").execute()
print(f"CMLs to seed: {len(cmls.data)}")

rows = []
for cml in cmls.data:
    nominal = cml.get("nominal_thickness") or 10.0
    t_req = cml.get("t_required_manual") or nominal * 0.875
    base_cr = random.uniform(0.05, 0.3)
    thickness = nominal
    for year in INSPECTION_YEARS:
        loss = base_cr * 5 * random.uniform(0.85, 1.15)
        thickness = max(thickness - loss, t_req * 0.85)
        rows.append({
            "id": str(uuid.uuid4()),
            "company_id": COMPANY_ID,
            "cml_point_id": cml["id"],
            "reading_date": f"{year}-06-15",
            "reading_mm": round(thickness, 3),
            "is_representative": True,
        })

print(f"Inserting {len(rows)} readings...")
for i in range(0, len(rows), 500):
    db.table("thickness_readings").insert(rows[i:i+500]).execute()
    print(f"  {min(i+500, len(rows))}/{len(rows)}")

print(f"DONE — {len(rows)} readings for {len(cmls.data)} CMLs")
