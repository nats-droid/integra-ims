"""
INTEGRA — Seed Script (15 Tahun Data Historis)
Populates all database tables with realistic petrochemical plant data.

Usage:
  cd /root/integra/backend
  source venv/bin/activate
  python scripts/seed.py

Environment:
  Reads SUPABASE_URL and SUPABASE_SERVICE_KEY from .env (via python-dotenv)
  or from environment variables.
"""
import os
import sys
import uuid
import random
from datetime import date, timedelta, datetime
from calendar import monthrange
from dotenv import load_dotenv
from supabase import create_client, Client

# ── Load environment ───────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://enppairwpjtmrgrvzxio.supabase.co"
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── Configuration ──────────────────────────────────────────────
START_YEAR = 2011
END_YEAR = 2026
NOW = date.today()
COMPANY_NAME = "PT Integra Petrochemical"
PASSWORD = "Integra2024!"

# ── Helpers ────────────────────────────────────────────────────

def gen_id():
    return str(uuid.uuid4())

def random_date(year_start, year_end, month_bias=6):
    """Random date between Jan 1 of year_start and Dec 31 of year_end."""
    y = random.randint(year_start, year_end)
    m = random.randint(1, 12)
    d = random.randint(1, min(28, monthrange(y, m)[1]))
    return date(y, m, d)

def p(msg):
    print(f"  {msg}")


# ================================================================
# 1. CREATE AUTH USERS
# ================================================================
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("1. MEMBUAT AUTH USERS (Supabase Auth)")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

USERS = [
    {"email": "admin@integra.com",     "password": PASSWORD, "full_name": "Admin System",    "role": "super_admin", "company_id": None},
    {"email": "supervisor@example.com", "password": PASSWORD, "full_name": "Dicki Wiryawan",  "role": "supervisor",  "company_id": None},
    {"email": "engineer1@example.com",  "password": PASSWORD, "full_name": "Bambang Susanto",  "role": "engineer",    "company_id": None},
    {"email": "inspector1@example.com", "password": PASSWORD, "full_name": "Ahmad Fauzi",      "role": "inspector",   "company_id": None},
    {"email": "inspector2@example.com", "password": PASSWORD, "full_name": "Rudi Hartono",     "role": "inspector",   "company_id": None},
]

auth_user_ids = {}
for u in USERS:
    try:
        resp = supabase.auth.admin.create_user({
            "email": u["email"],
            "password": u["password"],
            "email_confirm": True,
            "user_metadata": {
                "full_name": u["full_name"],
                "role": u["role"],
            }
        })
        uid = resp.user.id
        auth_user_ids[u["email"]] = uid
        p(f"✓ {u['email']} ({u['role']}) → {uid[:8]}...")
    except Exception as e:
        if "already exists" in str(e).lower():
            # Fetch existing user
            resp = supabase.auth.admin.list_users()
            for user in resp:
                if user.email == u["email"]:
                    auth_user_ids[u["email"]] = user.id
                    p(f"➤ {u['email']} — already exists, using existing")
                    break
        else:
            p(f"✗ {u['email']}: {e}")


# ================================================================
# 2. SEED COMPANY
# ================================================================
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("2. SEED COMPANY")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

company_id = gen_id()
try:
    supabase.table("companies").upsert({
        "id": company_id,
        "name": COMPANY_NAME,
        "plan_tier": "pro",
        "max_equipment": 200,
        "max_users": 25,
    }).execute()
    p(f"✓ Company: {COMPANY_NAME} ({company_id[:8]}...)")

    # Update user company_ids
    for u in USERS:
        if u["role"] != "super_admin":
            supabase.table("app_users").upsert({
                "id": gen_id(),
                "auth_user_id": auth_user_ids.get(u["email"]),
                "company_id": company_id,
                "role": u["role"],
                "full_name": u["full_name"],
            }).execute()
            p(f"  → app_user: {u['full_name']} ({u['role']})")
except Exception as e:
    p(f"✗ Company: {e}")
    # If company exists, find it
    resp = supabase.table("companies").select("*").limit(1).execute()
    if resp.data:
        company_id = resp.data[0]["id"]
        p(f"➤ Using existing company: {company_id[:8]}...")


# ================================================================
# 3. SEED PLANT AREAS (Hierarchical)
# ================================================================
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("3. SEED PLANT AREAS")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

AREAS = [
    # (name, parent_name or None, description)
    ("Olefin Complex",        None, "Utama — produksi olefin dari naphtha"),
    ("Polyethylene Plant",    None, "Produksi polyethylene dari ethylene"),
    ("Utilities",             None, "Steam, cooling water, dan utility lainnya"),
    ("Storage & Offsite",     None, "Storage tank dan loading facilities"),
    ("Cracker Unit",          "Olefin Complex", "Cracking furnace & quench area"),
    ("Separation Unit",       "Olefin Complex", "Distillation train — deethanizer, depropanizer"),
    ("Reactor Unit",          "Polyethylene Plant", "Loop reactor & catalyst area"),
    ("Extrusion Unit",        "Polyethylene Plant", "Extruder & pelletizing"),
    ("Boiler Unit",           "Utilities", "Steam boiler & BFW system"),
    ("Cooling Water Unit",    "Utilities", "Cooling tower & circulation pumps"),
    ("Tank Farm",             "Storage & Offsite", "Ethylene & propylene storage tanks"),
    ("Loading Rack",          "Storage & Offsite", "Truck & ISO tank loading"),
]

area_ids = {}  # name → id
for name, parent, desc in AREAS:
    aid = gen_id()
    parent_id = area_ids.get(parent) if parent else None
    try:
        supabase.table("plant_areas").upsert({
            "id": aid,
            "company_id": company_id,
            "name": name,
            "parent_area_id": parent_id,
            "description": desc,
        }).execute()
        area_ids[name] = aid
        p(f"✓ {name}" + (f" → {parent}" if parent else ""))
    except Exception as e:
        p(f"✗ {name}: {e}")


# ================================================================
# 4. SEED EQUIPMENT
# ================================================================
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("4. SEED EQUIPMENT")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

def get_area_id(name):
    return area_ids.get(name)

EQUIPMENT = [
    # (tag, type, fluid_service, material, area_name, design_temp_min, design_temp_max, design_pressure, pwht, risk_category, size, insulation, install_year, manufacturer)
    # --- Olefin — Cracker ---
    ("E-101",    "heater",     "Naphtha/HC",  "HK-40",      "Cracker Unit",   0,  750, 3.5,  True,  "critical", "∅2.5m x 12m",  "Firebrick",     2005, "Foster Wheeler"),
    ("E-102",    "vessel",     "Cracked gas", "1.25Cr-0.5Mo","Cracker Unit",   0,  540, 2.5,  True,  "high",     "∅1.2m x 4m",    "Mineral wool",   2005, "Mitsubishi HI"),
    ("P-101A",   "pump",       "Naphtha",     "316 SS",      "Cracker Unit", -10, 200, 15,   False, "high",     "4\"×6\"×8\"",     None,             2005, "Sulzer"),
    ("P-101B",   "pump",       "Naphtha",     "316 SS",      "Cracker Unit", -10, 200, 15,   False, "high",     "4\"×6\"×8\"",     None,             2005, "Sulzer"),
    ("PL-101",   "piping",     "Cracked gas", "P11 (1.25Cr)","Cracker Unit",   0,  540, 2.5,  True,  "critical", "DN300 Sch80",    "Mineral wool",   2005, "Benteler"),
    # --- Olefin — Separation ---
    ("V-201",    "vessel",     "C2/C3 mix",   "Carbon steel", "Separation Unit", -30, 80, 18,  False, "high",     "∅2.0m x 20m",    "Perlite",        2005, "Linde"),
    ("V-202",    "vessel",     "C3/C4 mix",   "Carbon steel", "Separation Unit", -20, 100, 15, False, "medium",   "∅2.0m x 18m",    "Perlite",        2005, "Linde"),
    ("V-203",    "vessel",     "C4/C5 mix",   "Carbon steel", "Separation Unit", -10, 120, 12, False, "medium",   "∅1.8m x 16m",    "Perlite",        2005, "Linde"),
    ("P-201",    "pump",       "C3 reflux",   "304 SS",      "Separation Unit", -30, 80,  20,  False, "medium",   "3\"×4\"×6\"",      None,             2005, "Flowserve"),
    ("PL-201",   "piping",     "C2H4/C3H6",   "Carbon steel", "Separation Unit", -30, 80, 20,  False, "high",     "DN150 Sch40",    "Perlite",        2005, "Europipe"),
    # --- Polyethylene — Reactor ---
    ("R-301",    "vessel",     "Ethylene/Hexene","316L SS",   "Reactor Unit",   0,  110, 45,  False, "critical", "∅1.5m x 12m",    None,             2008, "Univation"),
    ("V-301",    "vessel",     "PE slurry",   "Carbon steel", "Reactor Unit",   0,  100, 10,  False, "medium",   "∅1.8m x 5m",     None,             2008, "Mitsui"),
    ("P-301",    "pump",       "Reactor loop", "316 SS",      "Reactor Unit",   0,  110, 50,  False, "critical", "6\"×8\"×10\"",      None,             2008, "Sulzer"),
    ("PL-301",   "piping",     "PE slurry",   "316L SS",     "Reactor Unit",   0,  105, 45,  False, "critical", "DN250 Sch80S",   None,             2008, "Sandvik"),
    # --- Polyethylene — Extrusion ---
    ("EX-301",   "other",      "PE melt",     "Nitrided steel","Extrusion Unit", 140, 230, 30, False, "medium",   "∅200mm L/D 30",  None,             2008, "Coperion"),
    ("PL-302",   "piping",     "PE melt",     "Carbon steel", "Extrusion Unit", 140, 230, 30, True,  "medium",   "DN80 Sch80",     "Electric trace", 2008, "Vallourec"),
    # --- Utilities — Boiler ---
    ("B-401",    "heater",     "Steam",       "Carbon steel", "Boiler Unit",    0,  450, 45,  False, "high",     "∅2.0m x 8m",     "Ceramic fiber",  2003, "Babcock"),
    ("PL-401",   "piping",     "HP Steam",    "P22 (2.25Cr)","Boiler Unit",     0,  450, 42,  True,  "critical", "DN200 Sch160",   "Mineral wool",   2003, "Dalmine"),
    # --- Utilities — Cooling Water ---
    ("V-401",    "tank",       "Cooling water","Carbon steel","Cooling Water Unit", 0, 60, 0.5, False, "low",     "∅10m x 4m",     None,             2003, "Chicago Bridge"),
    ("PL-402",   "piping",     "Cooling water","Carbon steel","Cooling Water Unit", 0, 60,  6,  False, "low",     "DN400 Sch20",    None,             2003, "Salzgitter"),
    ("P-401",    "pump",       "Cooling water","Cast iron","Cooling Water Unit",0, 60,  8,   False, "low",     "12\"×14\"×16\"",    None,             2003, "ITT Goulds"),
    # --- Storage & Offsite — Tank Farm ---
    ("T-501",    "tank",       "Ethylene",    "9% Ni steel","Tank Farm",        -104, -90, 1.5, False, "critical", "∅15m x 20m",    "Perlite vacuum", 2006, "CB&I"),
    ("T-502",    "tank",       "Propylene",   "Carbon steel","Tank Farm",        -48, -30, 1.8, False, "high",     "∅12m x 15m",    "Perlite",        2006, "CB&I"),
    ("PL-501",   "piping",     "Ethylene",    "316L SS",     "Tank Farm",        -104, -90, 1.5, False, "critical", "DN150 Sch40S",  "PUF insulation", 2006, "Sandvik"),
    # --- Storage — Loading Rack ---
    ("PL-502",   "piping",     "Ethylene",    "316L SS",     "Loading Rack",    -104, -90, 2.0, False, "high",     "DN100 Sch40S",  "PUF insulation", 2006, "Kubota"),
]

equipment_ids = {}
for eq in EQUIPMENT:
    tag, etype, service, mat, area_name, tmin, tmax, press, pwht, risk, size, insulation, install_year, mfr = eq
    eid = gen_id()
    try:
        supabase.table("equipment").upsert({
            "id": eid,
            "company_id": company_id,
            "tag": tag,
            "type": etype,
            "fluid_service": service,
            "material": mat,
            "area_id": get_area_id(area_name),
            "design_temp_min": tmin,
            "design_temp_max": tmax,
            "design_pressure": press,
            "pwht": pwht,
            "risk_category": risk,
            "size_or_dimension": size,
            "insulation_type": insulation,
            "installation_date": f"{install_year}-01-15",
            "manufacturer": mfr,
            "notes": f"{service} — {area_name}",
        }).execute()
        equipment_ids[tag] = eid
        p(f"✓ {tag:8s} ({etype:8s}) — {area_name}")
    except Exception as e:
        p(f"✗ {tag}: {e}")


# ================================================================
# 5. SEED CIRCUITS
# ================================================================
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("5. SEED CIRCUITS")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

CIRCUITS = [
    # (name, equipment_tag, description, governing_cr)
    ("CL-CRKR-01",  "E-101",  "Cracking furnace tubes — radiant + convection", 0.15),
    ("CL-CRKR-02",  "E-102",  "Transfer line exchanger cracked gas side",       0.10),
    ("CL-CRKR-03",  "P-101A", "Naphtha feed circuit incl. pumps A/B",          0.05),
    ("CL-CRKR-04",  "PL-101", "Main transfer line cracked gas to quench",      0.20),
    ("CL-SEP-01",   "V-201",  "Deethanizer overhead system",                     0.08),
    ("CL-SEP-02",   "V-202",  "Depropanizer system",                             0.06),
    ("CL-SEP-03",   "P-201",  "C3 reflux circuit",                              0.05),
    ("CL-SEP-04",   "PL-201", "Ethylene/propylene product header",              0.04),
    ("CL-REAC-01",  "R-301",  "Loop reactor system incl. circulating pump",     0.12),
    ("CL-REAC-02",  "V-301",  "PE product discharge system",                    0.08),
    ("CL-REAC-03",  "PL-301", "Reactor loop piping incl. jacket lines",         0.10),
    ("CL-EXTR-01",  "EX-301", "Extruder barrel & die system",                   0.03),
    ("CL-EXTR-02",  "PL-302", "Melt piping from extruder to pelletizer",        0.04),
    ("CL-BLR-01",   "B-401",  "Steam drum & boiler tubes",                      0.18),
    ("CL-BLR-02",   "PL-401", "HP steam main header",                           0.07),
    ("CL-CW-01",    "V-401",  "Cooling water basin & distribution",             0.50),
    ("CL-CW-02",    "PL-402", "Cooling water supply/return mains",              0.25),
    ("CL-CW-03",    "P-401",  "Cooling water pump circuit",                     0.20),
    ("CL-TANK-01",  "T-501",  "Ethylene storage — inner vessel vapor side",     0.02),
    ("CL-TANK-02",  "T-502",  "Propylene storage system",                       0.03),
    ("CL-TANK-03",  "PL-501", "Ethylene transfer line to battery limit",        0.05),
    ("CL-LOAD-01",  "PL-502", "Ethylene loading line to truck rack",            0.04),
]

circuit_ids = {}
for name, eq_tag, desc, cr in CIRCUITS:
    cid = gen_id()
    try:
        supabase.table("circuits").upsert({
            "id": cid,
            "company_id": company_id,
            "equipment_id": equipment_ids.get(eq_tag),
            "name": name,
            "description": desc,
            "governing_cr_cache": cr,
        }).execute()
        circuit_ids[name] = cid
        p(f"✓ {name} — {eq_tag}")
    except Exception as e:
        # If duplicate on (company_id, equipment_id, name), skip
        if "duplicate" in str(e).lower():
            # Try to fetch existing
            resp = supabase.table("circuits").select("id").eq("company_id", company_id).eq("name", name).limit(1).execute()
            if resp.data:
                circuit_ids[name] = resp.data[0]["id"]
            p(f"➤ {name} — already exists")
        else:
            p(f"✗ {name}: {e}")


# ================================================================
# 6. SEED CML POINTS
# ================================================================
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("6. SEED CML POINTS")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

CML_POINTS = [
    # (location_label, circuit_name, equipment_tag, nominal_thickness, t_min, retirement_factor, cml_type)

    # Olefin — Cracker
    ("CRKR-TUBE-01",  "CL-CRKR-01", "E-101",  15.0,  13.125,  "ut"),
    ("CRKR-TUBE-02",  "CL-CRKR-01", "E-101",  15.0,  13.125,  "ut"),
    ("CRKR-TLE-01",   "CL-CRKR-02", "E-102",  22.0,  19.25,   "ut"),
    ("CRKR-TLE-02",   "CL-CRKR-02", "E-102",  22.0,  19.25,   "ut"),
    ("CRKR-PMP-01",   "CL-CRKR-03", "P-101A", 12.7,  11.1125, "ut"),
    ("CRKR-PMP-02",   "CL-CRKR-03", "P-101B", 12.7,  11.1125, "ut"),
    ("CRKR-MTL-01",   "CL-CRKR-04", "PL-101", 18.0,  15.75,   "ut"),
    ("CRKR-MTL-02",   "CL-CRKR-04", "PL-101", 18.0,  15.75,   "ut"),
    ("CRKR-MTL-03",   "CL-CRKR-04", "PL-101", 18.0,  15.75,   "ut"),

    # Olefin — Separation
    ("SEP-DEA-01",    "CL-SEP-01",  "V-201",  28.0,  24.5,    "ut"),
    ("SEP-DEA-02",    "CL-SEP-01",  "V-201",  28.0,  24.5,    "ut"),
    ("SEP-DEP-01",    "CL-SEP-02",  "V-202",  26.0,  22.75,   "ut"),
    ("SEP-DEP-02",    "CL-SEP-02",  "V-202",  26.0,  22.75,   "ut"),
    ("SEP-RFX-01",    "CL-SEP-03",  "P-201",  10.0,  8.75,    "ut"),
    ("SEP-PROD-01",   "CL-SEP-04",  "PL-201", 12.0,  10.5,    "ut"),
    ("SEP-PROD-02",   "CL-SEP-04",  "PL-201", 12.0,  10.5,    "ut"),

    # Polyethylene — Reactor
    ("REAC-LOOP-01",  "CL-REAC-01", "R-301",  25.0,  21.875,  "ut"),
    ("REAC-LOOP-02",  "CL-REAC-01", "R-301",  25.0,  21.875,  "ut"),
    ("REAC-LOOP-03",  "CL-REAC-01", "R-301",  25.0,  21.875,  "ut"),
    ("REAC-DISC-01",  "CL-REAC-02", "V-301",  16.0,  14.0,    "ut"),
    ("REAC-PIPE-01",  "CL-REAC-03", "PL-301", 18.0,  15.75,   "ut"),
    ("REAC-PIPE-02",  "CL-REAC-03", "PL-301", 18.0,  15.75,   "ut"),

    # Extrusion
    ("EXTR-BARL-01",  "CL-EXTR-01", "EX-301", 20.0,  17.5,    "manual"),
    ("EXTR-MELT-01",  "CL-EXTR-02", "PL-302", 12.0,  10.5,    "ut"),

    # Utilities — Boiler
    ("BLR-DRUM-01",   "CL-BLR-01",  "B-401",  35.0,  30.625,  "ut"),
    ("BLR-DRUM-02",   "CL-BLR-01",  "B-401",  35.0,  30.625,  "ut"),
    ("BLR-STM-01",    "CL-BLR-02",  "PL-401", 25.0,  21.875,  "ut"),
    ("BLR-STM-02",    "CL-BLR-02",  "PL-401", 25.0,  21.875,  "ut"),
    ("BLR-STM-03",    "CL-BLR-02",  "PL-401", 25.0,  21.875,  "ut"),

    # Utilities — Cooling Water
    ("CW-BASIN-01",   "CL-CW-01",   "V-401",  12.0,  10.5,    "ut"),
    ("CW-HEADER-01",  "CL-CW-02",   "PL-402", 10.0,  8.75,    "ut"),
    ("CW-HEADER-02",  "CL-CW-02",   "PL-402", 10.0,  8.75,    "ut"),
    ("CW-PUMP-01",    "CL-CW-03",   "P-401",  14.0,  12.25,   "ut"),

    # Storage
    ("TNK-C2H4-01",   "CL-TANK-01", "T-501",  30.0,  26.25,   "ut"),
    ("TNK-C2H4-02",   "CL-TANK-01", "T-501",  30.0,  26.25,   "ut"),
    ("TNK-C3H6-01",   "CL-TANK-02", "T-502",  25.0,  21.875,  "ut"),
    ("TNK-PIPE-01",   "CL-TANK-03", "PL-501", 12.0,  10.5,    "ut"),
    ("TNK-PIPE-02",   "CL-TANK-03", "PL-501", 12.0,  10.5,    "ut"),

    # Loading
    ("LOAD-ARM-01",   "CL-LOAD-01", "PL-502", 10.0,  8.75,    "ut"),
    ("LOAD-ARM-02",   "CL-LOAD-01", "PL-502", 10.0,  8.75,    "ut"),
]

cml_ids = {}
for label, circ_name, eq_tag, nom, tmin, cml_type in CML_POINTS:
    cid = gen_id()
    try:
        supabase.table("cml_points").upsert({
            "id": cid,
            "company_id": company_id,
            "circuit_id": circuit_ids.get(circ_name),
            "equipment_id": equipment_ids.get(eq_tag),
            "location_label": label,
            "nominal_thickness": nom,
            "t_min": tmin,
            "retirement_factor": 0.875,
            "cml_type": cml_type,
        }).execute()
        cml_ids[label] = cid
    except Exception as e:
        if "duplicate" in str(e).lower():
            resp = supabase.table("cml_points").select("id").eq("company_id", company_id).eq("location_label", label).limit(1).execute()
            if resp.data:
                cml_ids[label] = resp.data[0]["id"]
        else:
            p(f"✗ {label}: {e}")
p(f"✓ {len(CML_POINTS)} CML Points seeded")


# ================================================================
# 7. SEED INSPECTION EVENTS & THICKNESS READINGS (15 Tahun)
# ================================================================
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("7. SEED INSPECTION EVENTS & THICKNESS DATA")
print(f"   Periode: {START_YEAR} – {END_YEAR} ({END_YEAR - START_YEAR} tahun)")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# Inspector IDs
inspector_ids = []
for u in USERS:
    if u["role"] in ("inspector", "supervisor"):
        uid = auth_user_ids.get(u["email"])
        if uid:
            resp = supabase.table("app_users").select("id").eq("auth_user_id", uid).limit(1).execute()
            if resp.data:
                inspector_ids.append(resp.data[0]["id"])

engineer_id = None
for u in USERS:
    if u["role"] == "engineer":
        uid = auth_user_ids.get(u["email"])
        if uid:
            resp = supabase.table("app_users").select("id").eq("auth_user_id", uid).limit(1).execute()
            if resp.data:
                engineer_id = resp.data[0]["id"]

# Corrosion rate per circuit: (base_cr_mm_per_year, random_variation)
# Higher CR = faster thinning
CORROSION_RATES = {
    "CL-CRKR-01": (0.15, 0.05),   # Furnace tubes
    "CL-CRKR-02": (0.10, 0.03),
    "CL-CRKR-03": (0.05, 0.02),
    "CL-CRKR-04": (0.20, 0.06),   # Transfer line (high temp sulfidation)
    "CL-SEP-01":  (0.08, 0.03),
    "CL-SEP-02":  (0.06, 0.02),
    "CL-SEP-03":  (0.05, 0.02),
    "CL-SEP-04":  (0.04, 0.015),
    "CL-REAC-01": (0.12, 0.04),
    "CL-REAC-02": (0.08, 0.03),
    "CL-REAC-03": (0.10, 0.03),
    "CL-EXTR-01": (0.03, 0.01),
    "CL-EXTR-02": (0.04, 0.015),
    "CL-BLR-01":  (0.18, 0.06),   # Boiler — high corrosion
    "CL-BLR-02":  (0.07, 0.025),
    "CL-CW-01":   (0.50, 0.15),   # Cooling water — very high
    "CL-CW-02":   (0.25, 0.08),
    "CL-CW-03":   (0.20, 0.06),
    "CL-TANK-01": (0.02, 0.005),  # Cryogenic — minimal
    "CL-TANK-02": (0.03, 0.01),
    "CL-TANK-03": (0.05, 0.015),
    "CL-LOAD-01": (0.04, 0.01),
}

# For each CML point, create inspection events and thickness readings
total_events = 0
total_readings = 0
total_maintenance = 0

for label, circ_name, eq_tag, nominal, tmin, cml_type in CML_POINTS:
    cml_id = cml_ids.get(label)
    if not cml_id:
        continue

    eq_id = equipment_ids.get(eq_tag)
    circ_id = circuit_ids.get(circ_name)

    # Corrosion rate for this circuit
    base_cr, cr_var = CORROSION_RATES.get(circ_name, (0.05, 0.02))

    # Distribution of events: some CML measured every year, some every 2-3 years
    # More frequent for critical/high risk equipment
    risk = None
    for eq in EQUIPMENT:
        if eq[0] == eq_tag:
            risk = eq[8]  # risk_category index
            break

    # High risk → more frequent inspection
    if risk == "critical":
        freq_years = [1]  # annual
    elif risk == "high":
        freq_years = [1, 2]
    elif risk == "medium":
        freq_years = [2, 3]
    else:
        freq_years = [3, 4]

    current_thickness = nominal
    year = START_YEAR

    # Random start — not all CML measured from 2011
    start_offset = random.randint(0, 3)
    year += start_offset

    first_reading = True  # First reading = nominal

    while year <= END_YEAR:
        event_date = date(year, random.randint(3, 11), random.randint(1, 25))

        # Create inspection event
        event_id = gen_id()
        insp_id = random.choice(inspector_ids) if inspector_ids else None
        insp_types = []
        if nominal > 20:
            insp_types = ["external", "internal", "utm"]
        elif cml_type == "manual":
            insp_types = ["visual", "other"]
        else:
            insp_types = ["external", "utm", "cui"]

        try:
            supabase.table("inspection_events").upsert({
                "id": event_id,
                "company_id": company_id,
                "equipment_id": eq_id,
                "inspector_id": insp_id,
                "inspection_type": random.choice(insp_types),
                "event_date": event_date.isoformat(),
                "status": "approved",
                "notes": f"Rutin inspeksi — {eq_tag} {label}"
                    if year % 2 == 0 else f"Additional check — {eq_tag} {label}",
            }).execute()
            total_events += 1
        except Exception as e:
            p(f"  ⚠ events skip [{eq_tag} {label}]: {e}")
            continue

        # Generate thickness reading
        if first_reading:
            # First reading = nominal (new condition)
            measured = nominal + random.uniform(-0.1, 0.3)
            first_reading = False
        else:
            # Apply corrosion since last measurement
            years_since_last = 1 if len(freq_years) == 1 else random.choice(freq_years)
            cr_actual = base_cr + random.gauss(0, cr_var/2)
            cr_actual = max(0.005, cr_actual)  # minimum corrosion

            # Gradual decrease
            corrosion_loss = cr_actual * years_since_last * random.uniform(0.7, 1.3)
            current_thickness -= corrosion_loss

            # Add some measurement noise
            measured = current_thickness + random.gauss(0, 0.05)

            # Clamp: not below 0.5mm and not above nominal
            measured = max(0.5, min(nominal * 1.02, measured))

            # Occasionally inject an anomaly (accelerated corrosion reading)
            if random.random() < 0.05:  # 5% chance per reading
                measured -= random.uniform(0.3, 1.0)
                measured = max(0.5, measured)

        # Create thickness reading
        try:
            supabase.table("thickness_readings").upsert({
                "id": gen_id(),
                "company_id": company_id,
                "cml_point_id": cml_id,
                "inspection_event_id": event_id,
                "reading_date": event_date.isoformat(),
                "reading_mm": round(measured, 2),
                "is_representative": True,
                "notes": f"Reading #{year - START_YEAR + 1} — {label}",
            }).execute()
            total_readings += 1
        except Exception as e:
            p(f"  ⚠ readings skip [{label}]: {e}")
            continue

        # Occasionally create maintenance log (10% of events)
        if random.random() < 0.10:
            try:
                log_types = ["finding", "repair", "replacement"]
                sevs = ["minor", "major"]
                action = random.choice(["found minor corrosion", "cleaned and coated",
                    "replaced gasket", "noted scale deposit", "repaired insulation",
                    "ultrasonic scan completed"])
                severity = random.choice(sevs)
                supabase.table("maintenance_log").upsert({
                    "id": gen_id(),
                    "company_id": company_id,
                    "equipment_id": eq_id,
                    "related_inspection_event_id": event_id,
                    "log_date": event_date.isoformat(),
                    "description": f"{action} — {eq_tag} {label}",
                    "log_type": random.choice(log_types),
                    "severity": severity,
                }).execute()
                total_maintenance += 1
            except Exception as e:
                p(f"  ⚠ maint skip [{eq_tag} {label}]: {e}")
                continue

        # Advance to next year
        year += random.choice(freq_years) if year > START_YEAR + 2 else 1

    # Print progress every 10 CML
    idx = [l for l, _, _, _, _, _ in CML_POINTS].index(label) + 1
    if idx % 10 == 0:
        p(f"  … {idx}/{len(CML_POINTS)} CML — {total_readings} readings so far")

p(f"✓ {total_events} inspection events")
p(f"✓ {total_readings} thickness readings")
p(f"✓ {total_maintenance} maintenance logs")


# ================================================================
# 8. SEED NOTIFICATIONS (some samples)
# ================================================================
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("8. SEED NOTIFICATIONS")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# Create some sample notifications for the supervisor
supervisor_app_id = None
for u in USERS:
    if u["role"] == "supervisor":
        uid = auth_user_ids.get(u["email"])
        if uid:
            resp = supabase.table("app_users").select("id").eq("auth_user_id", uid).limit(1).execute()
            if resp.data:
                supervisor_app_id = resp.data[0]["id"]

if supervisor_app_id:
    notifications = [
        {"type": "approval_required", "title": "Approval Plan Dibutuhkan", "message": "3 inspection plans menunggu approval Anda"},
        {"type": "due_date_soon", "title": "Due Date Mendekat", "message": "E-101 inspection due dalam 30 hari"},
        {"type": "overdue", "title": "Inspeksi Terlewat", "message": "PL-401 HP Steam header inspeksi overdue 15 hari"},
        {"type": "system", "title": "Seed Data Selesai", "message": "Database Integra berhasil dipopulasi dengan 15 tahun data historis"},
    ]
    for notif in notifications:
        try:
            supabase.table("notifications").upsert({
                "id": gen_id(),
                "company_id": company_id,
                "user_id": supervisor_app_id,
                "type": notif["type"],
                "title": notif["title"],
                "message": notif["message"],
                "is_read": False,
            }).execute()
        except Exception as e:
            p(f"  ⚠ notification skip: {e}")
    p(f"✓ {len(notifications)} notifications for supervisor")


# ================================================================
# SUMMARY
# ================================================================
print("\n" + "=" * 50)
print("✅ SEED SCRIPT COMPLETED SUCCESSFULLY")
print("=" * 50)
print(f"  Company:    {COMPANY_NAME}")
print(f"  Areas:      {len(AREAS)} plant areas")
print(f"  Equipment:  {len(EQUIPMENT)} items")
print(f"  Circuits:   {len(CIRCUITS)}")
print(f"  CML Points: {len(CML_POINTS)}")
print(f"  Events:     {total_events} inspection events")
print(f"  Readings:   {total_readings} thickness readings")
print(f"  Maint Logs: {total_maintenance} entries")
print(f"\n  Auth users created (password: {PASSWORD}):")
for u in USERS:
    print(f"    • {u['email']:35s} ({u['role']:12s})")
print()
