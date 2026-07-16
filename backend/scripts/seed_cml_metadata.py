import os, uuid, random
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://enppairwpjtmrgrvzxio.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "sb_secret_W5llKdtM4NXPWFVrXXdiBQ_0lLMY_PN")
COMPANY_ID = "c704d7e6-07fb-48a2-9152-564434d8653f"

db = create_client(SUPABASE_URL, SUPABASE_KEY)
random.seed(42)

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

# Piping object types (weighted)
PIPING_OBJECTS = ["Pipe"] * 6 + ["Elbow"] * 2 + ["Tee"] + ["Reducer"]
# Equipment object types by equipment type
EQ_OBJECTS = {
    "vessel": ["Shell"] * 4 + ["Head"] * 2 + ["Nozzle"] * 2 + ["Bottom Head"] + ["Top Head"],
    "heat_exchanger": ["Shell"] * 3 + ["Head"] * 2 + ["Nozzle"] * 2 + ["Channel"] * 2 + ["Tube Sheet"],
    "tank": ["Shell"] * 5 + ["Bottom"] * 2 + ["Roof"] + ["Nozzle"] * 2,
}
PARTS = {
    "vessel": ["Shell 1", "Shell 2", "Bottom Head", "Top Head", "Nozzle N1", "Nozzle N2", "Nozzle N3"],
    "heat_exchanger": ["Shell Side", "Channel", "Head E", "Head F", "Nozzle N1", "Nozzle N2"],
    "tank": ["Shell Course 1", "Shell Course 2", "Shell Course 3", "Bottom Plate", "Roof Plate", "Nozzle N1"],
}
LOCATION_DEGS = [0, 90, 180, 270]
FLUID_MAP = {
    "Hydrocarbon Gas": "HC-GAS",
    "Hydrocarbon Liquid": "HC-LIQ",
    "Steam": "STM",
    "Cooling Water": "CW",
    "Caustic": "CAUS",
    "Acid Service": "ACID",
}

print("Fetching equipment...")
equipment = fetch_all("equipment", "id, tag, type, fluid_service", {"company_id": COMPANY_ID})
eq_map = {e["id"]: e for e in equipment}
print(f"  {len(equipment)} equipment")

print("Fetching circuits...")
circuits = fetch_all("circuits", "id, equipment_id, name", {"company_id": COMPANY_ID})
print(f"  {len(circuits)} circuits")

print("Fetching CML points...")
cmls = fetch_all("cml_points", "id, equipment_id, location_label", {"company_id": COMPANY_ID})
print(f"  {len(cmls)} CMLs")

# Update circuits with iso_number + fluid
print("Updating circuits...")
circuit_updates = []
for i, circuit in enumerate(circuits):
    eq = eq_map.get(circuit["equipment_id"], {})
    eq_type = eq.get("type", "piping")
    eq_tag = eq.get("tag", "UNK")
    fluid_service = eq.get("fluid_service", "Hydrocarbon Gas")
    fluid_code = FLUID_MAP.get(fluid_service, "HC")
    
    if eq_type == "piping":
        size = random.choice(["2\"", "3\"", "4\"", "6\"", "8\"", "10\"", "12\""])
        iso_number = f"{size}-{fluid_code}-{eq_tag}-A1A"
    else:
        iso_number = eq_tag
    
    circuit_updates.append({
        "id": circuit["id"],
        "iso_number": iso_number,
        "fluid": fluid_service,
    })

# Batch update circuits
for i in range(0, len(circuit_updates), 100):
    batch = circuit_updates[i:i+100]
    for c in batch:
        db.table("circuits").update({
            "iso_number": c["iso_number"],
            "fluid": c["fluid"],
        }).eq("id", c["id"]).execute()
    print(f"  Circuits: {min(i+100, len(circuit_updates))}/{len(circuit_updates)}")

# Update CML points with location_deg + object_type + part
print("Updating CML points...")
cml_updates = []
for cml in cmls:
    eq = eq_map.get(cml["equipment_id"], {})
    eq_type = eq.get("type", "piping")
    
    if eq_type == "piping":
        object_type = random.choice(PIPING_OBJECTS)
        part = None
        location_deg = random.choice(LOCATION_DEGS)
    else:
        objects = EQ_OBJECTS.get(eq_type, ["Shell"] * 5 + ["Head"] * 3 + ["Nozzle"] * 2)
        object_type = random.choice(objects)
        parts_list = PARTS.get(eq_type, ["Shell", "Head", "Nozzle"])
        part = random.choice(parts_list)
        location_deg = None
    
    cml_updates.append({
        "id": cml["id"],
        "location_deg": location_deg,
        "object_type": object_type,
        "part": part,
    })

# Batch update CMLs
for i in range(0, len(cml_updates), 100):
    batch = cml_updates[i:i+100]
    for c in batch:
        db.table("cml_points").update({
            "location_deg": c["location_deg"],
            "object_type": c["object_type"],
            "part": c["part"],
        }).eq("id", c["id"]).execute()
    print(f"  CMLs: {min(i+100, len(cml_updates))}/{len(cml_updates)}")

print(f"\nDONE — {len(circuit_updates)} circuits, {len(cml_updates)} CMLs updated")
