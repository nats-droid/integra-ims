"""
Seed script: equipment + CMLs + thickness readings for ML demo.
Generates 1000 piping, 100 vessel, 50 heat exchanger.
~10% equipment get simulated repairs (thickness resets to 90% nominal).
"""

import os
import random
import uuid
from supabase import create_client

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
COMPANY_ID = os.getenv("SEED_COMPANY_ID", "c704d7e6-07fb-48a2-9152-564434d8653f")

AREA_IDS = [
    "d3526569-b949-480c-9a9a-c7c1998ab9ba",  # Olefin Complex
    "d1cfbee5-71e4-4f62-bb28-b5ca7d9c0e37",  # Polyethylene Plant
    "c107c1c9-1e96-49df-a930-3dd04b04e844",  # Utilities
    "d239da01-d732-4037-8afc-b2bb89afbd8f",  # Storage & Offsite
    "c6bab57e-8385-4bed-9a7e-31d0090371c4",  # Cracker Unit
    "a76efddb-d8b3-4090-8063-22e1cac7df68",  # Separation Unit
    "1b8e07f3-59ea-4645-bc0a-11e0541839c2",  # Reactor Unit
    "68148665-2b31-4d00-a228-c0763c23764d",  # Extrusion Unit
    "316ef60e-8b0c-4029-96f4-f51eb1f66375",  # Boiler Unit
    "4aedcf3b-b91f-4810-8123-5bcfcc3c02e6",  # Cooling Water Unit
    "a3da0519-dd33-48f2-b623-649c9ab5e55e",  # Tank Farm
    "51d6eda5-c471-4c5a-9ffd-9a84e75dd070",  # Loading Rack
]

MATERIALS = ["CS", "SS304", "SS316", "CS+clad", "5Cr-0.5Mo", "9Cr-1Mo", "Duplex SS"]
FLUID_SERVICES = ["Steam", "Hydrocarbon", "Cooling Water", "Process Gas", "Chemical",
                  "Condensate", "Nitrogen", "Air", "Acid", "Caustic"]
INSULATION_TYPES = ["Mineral Wool", "Calcium Silicate", "Cellular Glass", "None", "PE Foam"]

INSPECTION_YEARS = [2005, 2010, 2015, 2020, 2025]

NOMINAL = {
    "piping": 9.27,
    "vessel": 16.0,
    "heater": 12.7,
}

# Corrosion rate bands (mm/year)
CR_BANDS = {
    "low":  (0.05, 0.15),
    "med":  (0.15, 0.35),
    "high": (0.35, 0.70),
}
CR_WEIGHTS = [50, 35, 15]  # low, med, high

# Repair: thickness restored to 90% of nominal
REPAIR_FRACTION = 0.9
REPAIR_YEARS = [2010, 2018]

# ---------------------------------------------------------------------------
# DB client
# ---------------------------------------------------------------------------

db = create_client(SUPABASE_URL, SUPABASE_KEY)


def batch_insert(table: str, rows: list[dict], batch_size: int = 500):
    """Insert rows in batches, return total inserted."""
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        r = db.table(table).insert(batch).execute()
        total += len(r.data)
        print(f"  {table}: inserted {total}/{len(rows)}")
    return total


def new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Equipment generator
# ---------------------------------------------------------------------------

def make_equipment(eq_type: str, count: int, prefix: str) -> list[dict]:
    """Generate `count` equipment dicts of `eq_type` with tag prefix."""
    rows = []
    for i in range(1, count + 1):
        area_id = random.choice(AREA_IDS)
        is_repair = i <= int(count * 0.10)  # first 10% = repaired
        rows.append({
            "id": new_id(),
            "company_id": COMPANY_ID,
            "tag": f"{prefix}-{i:04d}",
            "type": eq_type,
            "fluid_service": random.choice(FLUID_SERVICES),
            "material": random.choice(MATERIALS),
            "area_id": area_id,
            "design_temp_min": random.randint(-20, 50),
            "design_temp_max": random.randint(150, 450),
            "design_pressure": round(random.uniform(5, 60), 1),
            "pwht": random.choice([True, False]),
            "risk_category": random.choice(["low", "medium", "high"]),
            "compliance_status": random.choice(["compliant", "non-compliant", "pending"]),
            "size_or_dimension": f"{random.choice(['4','6','8','10','12','16','20','24'])}\" SCH{random.choice([40,80,120])}",
            "insulation_type": random.choice(INSULATION_TYPES),
            "installation_date": f"{random.randint(1980, 2004)}-{random.randint(1,12):02d}-01",
            "manufacturer": random.choice(["Kobe Steel", "Mitsubishi Heavy", "IHI Corp", "BORSIG",
                                          "Alstom", "L&T", "BHEL", "Sulzer"]),
            "serial_number": f"SN-{random.randint(10000, 99999)}",
            "notes": None,
            "is_active": True,
            # internal: tag for later use
            "_repair": is_repair,
        })
    return rows


# ---------------------------------------------------------------------------
# Circuits & CMLs generator
# ---------------------------------------------------------------------------

def make_cmls_and_circuits(equipment_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Create one circuit per equipment + 10 CMLs per equipment.
    Returns (circuit_rows, cml_rows).
    """
    circuit_rows = []
    cml_rows = []

    for eq in equipment_rows:
        circ_id = new_id()
        circuit_rows.append({
            "id": circ_id,
            "company_id": COMPANY_ID,
            "name": f"CL-{eq['tag']}",
            "equipment_id": eq["id"],
        })

        nominal = NOMINAL.get(eq["type"], 9.27)
        t_min = round(nominal * random.uniform(0.5, 0.7), 2)

        for cml_idx in range(1, 11):
            cml_rows.append({
                "id": new_id(),
                "company_id": COMPANY_ID,
                "circuit_id": circ_id,
                "equipment_id": eq["id"],
                "location_label": f"{eq['tag']}-CML{cml_idx:02d}",
                "nominal_thickness": nominal,
                "t_min": t_min,
                "retirement_factor": round(nominal * 0.3, 2),
                "cml_type": "ut",
                "is_active": True,
                "t_required_manual": t_min,
                # internal
                "_repair": eq["_repair"],
            })

    return circuit_rows, cml_rows


# ---------------------------------------------------------------------------
# Thickness readings generator
# ---------------------------------------------------------------------------

def pick_cr() -> float:
    """Pick a corrosion rate from weighted bands."""
    band = random.choices(list(CR_BANDS.keys()), weights=CR_WEIGHTS, k=1)[0]
    lo, hi = CR_BANDS[band]
    return round(random.uniform(lo, hi), 4)


def make_readings(cml_rows: list[dict]) -> list[dict]:
    """Generate thickness readings per CML per inspection year.
    Repaired CMLs get thickness reset to 90% nominal at 2010 and 2018.
    """
    readings = []
    for cml in cml_rows:
        nominal = cml["nominal_thickness"]
        is_repaired = cml["_repair"]
        cr = pick_cr()

        # Start from nominal at installation (assume ~year 2000)
        current = nominal
        prev_year = 2000

        for year in INSPECTION_YEARS:
            elapsed = year - prev_year
            current = current - cr * elapsed
            current = max(current, 0.5)  # floor at 0.5mm

            # Apply repair if this CML is repaired and year aligns
            if is_repaired and year in REPAIR_YEARS:
                current = nominal * REPAIR_FRACTION

            readings.append({
                "id": new_id(),
                "company_id": COMPANY_ID,
                "cml_point_id": cml["id"],
                "inspection_event_id": None,
                "reading_date": f"{year}-{random.randint(3, 11):02d}-{random.randint(1, 28):02d}",
                "reading_mm": round(current, 2),
                "is_representative": (year == INSPECTION_YEARS[-1]),
                "notes": None,
            })

            prev_year = year

            # If repair at 2018, start 2018 as new base for next interval
            if is_repaired and year == REPAIR_YEARS[-1]:
                # Already set current above; continue degrading from 2018 to next year
                pass

    return readings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating equipment...")
    piping = make_equipment("piping", 1000, "P")
    vessel = make_equipment("vessel", 100, "V")
    hex = make_equipment("heater", 50, "HE")
    all_equipment = piping + vessel + hex
    print(f"  Total equipment: {len(all_equipment)}")

    # Strip internal _repair key before insert
    equipment_insert = [
        {k: v for k, v in eq.items() if not k.startswith("_")}
        for eq in all_equipment
    ]
    for eq in equipment_insert: eq.pop("_repair", None)

    print("Inserting equipment...")
    batch_insert("equipment", equipment_insert)

    print("Generating circuits & CMLs...")
    circuits, cmls = make_cmls_and_circuits(all_equipment)
    print(f"  Circuits: {len(circuits)}, CMLs: {len(cmls)}")

    print("Inserting circuits...")
    batch_insert("circuits", circuits)

    print("Inserting CML points...")
    cml_insert = [{k: v for k, v in c.items() if not k.startswith("_")} for c in cmls]
    for cml in cml_insert: cml.pop("_repair", None)
    batch_insert("cml_points", cml_insert)

    print("Generating thickness readings...")
    readings = make_readings(cmls)
    print(f"  Readings: {len(readings)}")

    print("Inserting thickness readings...")
    batch_insert("thickness_readings", readings)

    print()
    print("=== DONE ===")
    print(f"Equipment: {len(all_equipment)}")
    print(f"Circuits:  {len(circuits)}")
    print(f"CMLs:      {len(cmls)}")
    print(f"Readings:  {len(readings)}")
    print(f"Repaired:  ~{int(len(all_equipment) * 0.10)} equipment")


if __name__ == "__main__":
    main()
