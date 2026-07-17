#!/usr/bin/env python3
"""Seed clean demo data for Integra IMS — 3 plants, 43 new equipment, 2150 readings."""

import os, uuid, random
import numpy as np
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://enppairwpjtmrgrvzxio.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "sb_secret_W5llKdtM4NXPWFVrXXdiBQ_0lLMY_PN")
COMPANY_ID = "c704d7e6-07fb-48a2-9152-564434d8653f"
db = create_client(SUPABASE_URL, SUPABASE_KEY)
random.seed(42)
now = datetime.now(timezone.utc).isoformat()

# ── Plant Areas (get existing) ─────────────────────────────────────────────
areas = db.table("plant_areas").select("id, name").eq("company_id", COMPANY_ID).execute()
area_map = {a["name"]: a["id"] for a in areas.data}
print("Areas:", list(area_map.keys()))

# Ensure CDU, OS, Utility exist
NEW_AREAS = ["CDU", "OS", "Utility"]
for area_name in NEW_AREAS:
    if area_name not in area_map:
        r = db.table("plant_areas").insert({
            "id": str(uuid.uuid4()),
            "company_id": COMPANY_ID,
            "name": area_name,
            "description": area_name,
        }).execute()
        area_map[area_name] = r.data[0]["id"]
        print(f"Created area: {area_name}")

# ── Delete ML seed equipment (P-XXXX, V-XXXX, HE-XXXX pattern) ────────────
import re
print("\nDeleting old ML seed equipment...")
all_eq = db.table("equipment").select("id, tag").eq("company_id", COMPANY_ID).execute()
ml_pattern = re.compile(r"^(P|V|HE)-\d{4}$")
ml_ids = [e["id"] for e in all_eq.data if ml_pattern.match(e["tag"])]
print(f"Found {len(ml_ids)} ML seed equipment to delete")

# Delete in batches (cascade will handle CMLs, readings, circuits)
for i in range(0, len(ml_ids), 50):
    batch = ml_ids[i:i+50]
    db.table("equipment").delete().in_("id", batch).execute()
    print(f"  Deleted {min(i+50, len(ml_ids))}/{len(ml_ids)}")

# ── Circuit definitions per plant ──────────────────────────────────────────
CIRCUITS = {
    "CDU": [
        {
            "name": "CDU-CIR-01", "iso": "8\"-CRUDE-CDU-001",
            "fluid": "Crude Oil", "op_temp": 280, "op_pres": 12.5,
            "material": "Carbon Steel A106-B",
            "tags": [
                {"tag": "PL-CDU-001", "type": "piping", "obj": "Pipe", "size": "8\""},
                {"tag": "PL-CDU-002", "type": "piping", "obj": "Elbow", "size": "8\""},
                {"tag": "PL-CDU-003", "type": "piping", "obj": "Reducer", "size": "8\"x6\""},
                {"tag": "PL-CDU-004", "type": "piping", "obj": "Pipe", "size": "8\""},
            ]
        },
        {
            "name": "CDU-CIR-02", "iso": "6\"-OVHD-CDU-002",
            "fluid": "Overhead Vapor", "op_temp": 120, "op_pres": 2.5,
            "material": "SS 316L",
            "tags": [
                {"tag": "PL-CDU-005", "type": "piping", "obj": "Pipe", "size": "6\""},
                {"tag": "PL-CDU-006", "type": "piping", "obj": "Tee", "size": "6\""},
                {"tag": "PL-CDU-007", "type": "piping", "obj": "Elbow", "size": "6\""},
            ]
        },
        {
            "name": "CDU-CIR-03", "iso": "CDU-VESSELS",
            "fluid": "Crude Oil", "op_temp": 320, "op_pres": 15.0,
            "material": "Carbon Steel A516-70",
            "tags": [
                {"tag": "V-CDU-001", "type": "vessel", "obj": "Shell", "size": "ID 2400mm"},
                {"tag": "V-CDU-002", "type": "vessel", "obj": "Shell", "size": "ID 1800mm"},
                {"tag": "E-CDU-001", "type": "other", "obj": "Shell", "size": "AES 600-4"},
                {"tag": "E-CDU-002", "type": "other", "obj": "Shell", "size": "AES 500-4"},
            ]
        },
        {
            "name": "CDU-CIR-04", "iso": "4\"-REFLUX-CDU-004",
            "fluid": "Naphtha", "op_temp": 95, "op_pres": 3.5,
            "material": "Chrome Moly P11",
            "tags": [
                {"tag": "PL-CDU-008", "type": "piping", "obj": "Pipe", "size": "4\""},
                {"tag": "PL-CDU-009", "type": "piping", "obj": "Elbow", "size": "4\""},
                {"tag": "PL-CDU-010", "type": "piping", "obj": "Pipe", "size": "4\""},
                {"tag": "PL-CDU-011", "type": "piping", "obj": "Reducer", "size": "4\"x3\""},
            ]
        },
    ],
    "OS": [
        {
            "name": "OS-CIR-01", "iso": "6\"-PROD-OS-001",
            "fluid": "Hydrocarbon Liquid", "op_temp": 65, "op_pres": 8.0,
            "material": "Carbon Steel A106-B",
            "tags": [
                {"tag": "PL-OS-001", "type": "piping", "obj": "Pipe", "size": "6\""},
                {"tag": "PL-OS-002", "type": "piping", "obj": "Elbow", "size": "6\""},
                {"tag": "PL-OS-003", "type": "piping", "obj": "Tee", "size": "6\""},
                {"tag": "PL-OS-004", "type": "piping", "obj": "Pipe", "size": "6\""},
            ]
        },
        {
            "name": "OS-CIR-02", "iso": "OS-STORAGE",
            "fluid": "Crude Oil", "op_temp": 45, "op_pres": 0.5,
            "material": "Carbon Steel A516-70",
            "tags": [
                {"tag": "T-OS-001", "type": "tank", "obj": "Shell", "size": "D=15m"},
                {"tag": "T-OS-002", "type": "tank", "obj": "Shell", "size": "D=15m"},
                {"tag": "T-OS-003", "type": "tank", "obj": "Shell", "size": "D=12m"},
                {"tag": "V-OS-001", "type": "vessel", "obj": "Shell", "size": "ID 1200mm"},
            ]
        },
        {
            "name": "OS-CIR-03", "iso": "3\"-CHEM-OS-003",
            "fluid": "Caustic", "op_temp": 80, "op_pres": 5.0,
            "material": "SS 304",
            "tags": [
                {"tag": "PL-OS-005", "type": "piping", "obj": "Pipe", "size": "3\""},
                {"tag": "PL-OS-006", "type": "piping", "obj": "Elbow", "size": "3\""},
                {"tag": "PL-OS-007", "type": "piping", "obj": "Pipe", "size": "3\""},
            ]
        },
        {
            "name": "OS-CIR-04", "iso": "OS-HE",
            "fluid": "Cooling Water", "op_temp": 45, "op_pres": 4.0,
            "material": "Carbon Steel A179",
            "tags": [
                {"tag": "E-OS-001", "type": "other", "obj": "Shell", "size": "AES 400-2"},
                {"tag": "E-OS-002", "type": "other", "obj": "Shell", "size": "AES 400-2"},
                {"tag": "E-OS-003", "type": "other", "obj": "Shell", "size": "AES 300-2"},
            ]
        },
    ],
    "Utility": [
        {
            "name": "UTL-CIR-01", "iso": "4\"-STM-UTL-001",
            "fluid": "Steam", "op_temp": 185, "op_pres": 11.0,
            "material": "Carbon Steel A106-B",
            "tags": [
                {"tag": "PL-UTL-001", "type": "piping", "obj": "Pipe", "size": "4\""},
                {"tag": "PL-UTL-002", "type": "piping", "obj": "Elbow", "size": "4\""},
                {"tag": "PL-UTL-003", "type": "piping", "obj": "Tee", "size": "4\""},
                {"tag": "PL-UTL-004", "type": "piping", "obj": "Pipe", "size": "4\""},
            ]
        },
        {
            "name": "UTL-CIR-02", "iso": "6\"-CW-UTL-002",
            "fluid": "Cooling Water", "op_temp": 40, "op_pres": 4.5,
            "material": "Carbon Steel A53-B",
            "tags": [
                {"tag": "PL-UTL-005", "type": "piping", "obj": "Pipe", "size": "6\""},
                {"tag": "PL-UTL-006", "type": "piping", "obj": "Elbow", "size": "6\""},
                {"tag": "PL-UTL-007", "type": "piping", "obj": "Pipe", "size": "6\""},
                {"tag": "PL-UTL-008", "type": "piping", "obj": "Reducer", "size": "6\"x4\""},
            ]
        },
        {
            "name": "UTL-CIR-03", "iso": "UTL-BOILER",
            "fluid": "Steam", "op_temp": 200, "op_pres": 15.0,
            "material": "Carbon Steel A516-70",
            "tags": [
                {"tag": "V-UTL-001", "type": "vessel", "obj": "Shell", "size": "ID 1600mm"},
                {"tag": "E-UTL-001", "type": "other", "obj": "Shell", "size": "AES 500-2"},
                {"tag": "E-UTL-002", "type": "other", "obj": "Shell", "size": "AES 400-2"},
            ]
        },
        {
            "name": "UTL-CIR-04", "iso": "2\"-ACID-UTL-004",
            "fluid": "Acid Service", "op_temp": 60, "op_pres": 6.0,
            "material": "SS 316L",
            "tags": [
                {"tag": "PL-UTL-009", "type": "piping", "obj": "Pipe", "size": "2\""},
                {"tag": "PL-UTL-010", "type": "piping", "obj": "Elbow", "size": "2\""},
                {"tag": "PL-UTL-011", "type": "piping", "obj": "Pipe", "size": "2\""},
            ]
        },
    ],
}

# CML config per equipment type
CML_CONFIG = {
    "piping": {
        "nominal": 9.27, "t_req_factor": 0.6,
        "objects": ["Pipe"]*6 + ["Elbow"]*2 + ["Tee"] + ["Reducer"],
        "location_degs": [0, 90, 180, 270],
    },
    "vessel": {
        "nominal": 16.0, "t_req_factor": 0.65,
        "objects": ["Shell"]*5 + ["Head"]*3 + ["Nozzle"]*2,
        "parts": ["Shell 1", "Shell 2", "Bottom Head", "Top Head", "Nozzle N1", "Nozzle N2", "Nozzle N3", "Nozzle N4", "Skirt", "Nozzle N5"],
    },
    "other": {
        "nominal": 12.7, "t_req_factor": 0.625,
        "objects": ["Shell"]*4 + ["Head"]*2 + ["Nozzle"]*2 + ["Channel"]*2,
        "parts": ["Shell Side", "Channel Head E", "Channel Head F", "Nozzle N1", "Nozzle N2", "Nozzle N3", "Shell Nozzle N1", "Shell Nozzle N2", "Baffle", "Tube Sheet"],
    },
    "tank": {
        "nominal": 10.0, "t_req_factor": 0.7,
        "objects": ["Shell"]*5 + ["Bottom"]*2 + ["Roof"]*2 + ["Nozzle"],
        "parts": ["Shell Course 1", "Shell Course 2", "Shell Course 3", "Shell Course 4", "Bottom Plate", "Annular Plate", "Roof Plate", "Nozzle N1", "Nozzle N2", "Nozzle N3"],
    },
}

INSPECTION_YEARS = [2000, 2005, 2010, 2015, 2020]

# ── Generate new equipment ─────────────────────────────────────────────────
print("\nGenerating new equipment...")
all_new_eq = []
all_circuits = []
all_cmls = []
all_readings = []

for plant_name, circuits in CIRCUITS.items():
    area_id = area_map.get(plant_name)
    if not area_id:
        print(f"WARNING: area {plant_name} not found, skipping")
        continue

    for circuit_def in circuits:
        circuit_id = str(uuid.uuid4())
        
        for tag_def in circuit_def["tags"]:
            eq_id = str(uuid.uuid4())
            eq_type = tag_def["type"]
            cfg = CML_CONFIG.get(eq_type, CML_CONFIG["piping"])
            
            # Equipment
            all_new_eq.append({
                "id": eq_id,
                "company_id": COMPANY_ID,
                "tag": tag_def["tag"],
                "type": eq_type,
                "fluid_service": circuit_def["fluid"],
                "material": circuit_def["material"],
                "area_id": area_id,
                "design_temp_min": 0,
                "design_temp_max": round(circuit_def["op_temp"] * 1.1, 1),
                "design_pressure": round(circuit_def["op_pres"] * 1.25, 2),
                "pwht": False,
                "risk_category": "low",
                "compliance_status": "compliant",
                "size_or_dimension": tag_def.get("size", ""),
                "insulation_type": "",
                "installation_date": f"{random.randint(1995, 2000)}-01-01",
                "manufacturer": "",
                "serial_number": "",
                "notes": "",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            })
            
            # Circuit (one per tag for now, grouped by circuit_def)
            all_circuits.append({
                "id": str(uuid.uuid4()),
                "company_id": COMPANY_ID,
                "equipment_id": eq_id,
                "name": circuit_def["name"],
                "description": circuit_def["iso"],
                "iso_number": circuit_def["iso"],
                "fluid": circuit_def["fluid"],
                "operating_temp": circuit_def["op_temp"],
                "operating_pressure": circuit_def["op_pres"],
                "material": circuit_def["material"],
                "created_at": now,
                "updated_at": now,
            })
            
            # 10 CML per equipment
            nominal = cfg["nominal"]
            t_req = round(nominal * cfg["t_req_factor"], 2)
            base_cr = random.uniform(0.05, 0.45)
            
            for j in range(10):
                cml_id = str(uuid.uuid4())
                obj = cfg["objects"][j % len(cfg["objects"])]
                part = cfg["parts"][j % len(cfg["parts"])] if "parts" in cfg else None
                loc_deg = random.choice(cfg["location_degs"]) if "location_degs" in cfg else None
                
                all_cmls.append({
                    "id": cml_id,
                    "company_id": COMPANY_ID,
                    "equipment_id": eq_id,
                    "circuit_id": all_circuits[-1]["id"],
                    "location_label": f"{tag_def['tag']}-CML{j+1:02d}",
                    "nominal_thickness": nominal,
                    "t_required_manual": t_req,
                    "t_min": t_req,
                    "retirement_factor": 0.0,
                    "cml_type": "ut",
                    "object_type": obj,
                    "part": part,
                    "location_deg": loc_deg,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                })
                
                # 5 readings per CML
                thickness = nominal
                cr_variation = base_cr * random.uniform(0.8, 1.2)
                for year in INSPECTION_YEARS:
                    loss = cr_variation * 5 * random.uniform(0.85, 1.15)
                    thickness = max(thickness - loss, t_req * 0.75)
                    all_readings.append({
                        "id": str(uuid.uuid4()),
                        "company_id": COMPANY_ID,
                        "cml_point_id": cml_id,
                        "reading_date": f"{year}-06-15",
                        "reading_mm": round(thickness, 3),
                        "is_representative": year == INSPECTION_YEARS[-1],
                        "created_at": now,
                    })

print(f"Equipment to insert: {len(all_new_eq)}")
print(f"Circuits to insert: {len(all_circuits)}")
print(f"CMLs to insert: {len(all_cmls)}")
print(f"Readings to insert: {len(all_readings)}")

# ── Insert ─────────────────────────────────────────────────────────────────
def batch_insert(table, rows, batch_size=100):
    for i in range(0, len(rows), batch_size):
        db.table(table).insert(rows[i:i+batch_size]).execute()
        print(f"  {table}: {min(i+batch_size, len(rows))}/{len(rows)}")

print("\nInserting equipment...")
batch_insert("equipment", all_new_eq)
print("Inserting circuits...")
batch_insert("circuits", all_circuits)
print("Inserting CMLs...")
batch_insert("cml_points", all_cmls)
print("Inserting readings...")
batch_insert("thickness_readings", all_readings)

print(f"\n=== DONE ===")
print(f"Equipment: {len(all_new_eq)}")
print(f"Circuits:  {len(all_circuits)}")
print(f"CMLs:      {len(all_cmls)}")
print(f"Readings:  {len(all_readings)}")
