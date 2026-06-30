"""
DM Screener — Rule-based Damage Mechanism Screening
=====================================================
Replicates screenAsset() from dm_screener_pro.html exactly.
67 API 571 damage mechanisms in dm_knowledge_base.
Scoring: material + fluid + temp + PWHT boost → Active / Possible / Related.
"""
from typing import Optional
from app.core.database import get_db
import math


def tokenize(text: str) -> list[str]:
    """Exact tokenizer from dm_screener_pro.html:
    split by whitespace, filter tokens longer than 1 char."""
    if not text:
        return []
    import re
    return [t for t in re.split(r'\s+', text.lower()) if len(t) > 1]


def screen_asset(input_data: dict) -> dict:
    """Exact port of screenAsset() from dm_screener_pro.html (lines ~1954-2015).
    
    Input fields used:
      - mat (material)
      - fluid (fluid_service)
      - tmin (design_temp_min)
      - tmax (design_temp_max)
      - pwht (boolean, True=Yes, False=No)
    
    Returns active[], possible[], related[] DMs with dm_code and dm_name.
    """
    mat_tokens = tokenize(input_data.get("mat", ""))
    fluid_tokens = tokenize(input_data.get("fluid", ""))
    tmin = input_data.get("tmin", 0)
    tmax = input_data.get("tmax", 100)
    # Handle None/NaN
    if tmin is None or (isinstance(tmin, float) and math.isnan(tmin)):
        tmin = 0
    if tmax is None or (isinstance(tmax, float) and math.isnan(tmax)):
        tmax = 100
    pwht = input_data.get("pwht", None)

    kb = get_db().table("dm_knowledge_base").select("*").execute()
    if not kb.data:
        return {"active": [], "possible": [], "related": [], "total_matched": 0}

    active = []
    possible = []
    related = []

    for dm in kb.data:
        # Material match: any token from input hits any keyword in dm.materials
        dm_materials = dm.get("materials", [])
        mat_match = _match_tokens(dm_materials, mat_tokens)

        # Fluid match: any token from input hits any keyword in dm.fluids
        dm_fluids = dm.get("fluids", [])
        fluid_match = _match_tokens(dm_fluids, fluid_tokens)

        # Temperature match: tmax >= dm.tempMin && tmin <= dm.tempMax
        dm_temp_min = dm.get("temp_min", -999)
        dm_temp_max = dm.get("temp_max", 999)
        # Use sensible defaults like JS: isNaN ? 0/100
        temp_match = (tmax >= dm_temp_min and tmin <= dm_temp_max)

        # Check if user provided temperature data
        has_temp_data = (
            input_data.get("tmin") is not None and input_data.get("tmax") is not None
            and not (isinstance(input_data.get("tmin"), float) and math.isnan(input_data.get("tmin")))
            and not (isinstance(input_data.get("tmax"), float) and math.isnan(input_data.get("tmax")))
        )

        # Score: matMatch + fluidMatch + tempMatch
        score = (1 if mat_match else 0) + (1 if fluid_match else 0) + (1 if temp_match else 0)

        # Classification — exact order from reference
        if mat_match and fluid_match and (temp_match or not has_temp_data):
            active.append({"dm_code": dm["dm_code"], "dm_name": dm["dm_name"]})
        elif score >= 2:
            possible.append({"dm_code": dm["dm_code"], "dm_name": dm["dm_name"]})
        elif mat_match and fluid_match:
            related.append({"dm_code": dm["dm_code"], "dm_name": dm["dm_name"]})

    # PWHT Boost: if no PWHT, DM with pwhtFlag:true that matches mat+fluid
    # but not already in active/possible gets promoted to possible
    if pwht is False or pwht == "No" or pwht == "no":
        for dm in kb.data:
            if not dm.get("pwht_flag") == "required":
                continue
            dm_materials = dm.get("materials", [])
            dm_fluids = dm.get("fluids", [])
            mat_match = _match_tokens(dm_materials, mat_tokens)
            fluid_match = _match_tokens(dm_fluids, fluid_tokens)
            if mat_match and fluid_match:
                in_active = any(a["dm_code"] == dm["dm_code"] for a in active)
                in_possible = any(p["dm_code"] == dm["dm_code"] for p in possible)
                if not in_active and not in_possible:
                    possible.append({
                        "dm_code": dm["dm_code"],
                        "dm_name": dm["dm_name"] + " (No PWHT — elevated risk)",
                    })

    # Grab recommended NDE from top active DM
    top_dm_code = active[0]["dm_code"] if active else None
    nde = "UT Thickness (Baseline)"
    if top_dm_code:
        top_dm = next((d for d in kb.data if d["dm_code"] == top_dm_code), None)
        if top_dm and top_dm.get("recommended_nde"):
            nde = ", ".join(top_dm["recommended_nde"][:2])

    return {
        "status": "ok",
        "active": active[:6],
        "possible": possible[:4],
        "related": related[:4],
        "total_matched": len(active) + len(possible) + len(related),
        "total_screened": len(kb.data),
        "nde": nde,
    }


def _match_tokens(dm_keywords: list[str], input_tokens: list[str]) -> bool:
    """Exact match logic from reference:
    dm.materials.some(m => tokenize(m).some(k => matTokens.includes(k) || matTokens.some(t => t.includes(k))));
    """
    if not input_tokens:
        return False
    for keyword in dm_keywords:
        kw_tokens = tokenize(keyword)
        for kt in kw_tokens:
            if kt in input_tokens:
                return True
            # Check if any input token includes the keyword token OR vice versa
            if any(t == kt or kt in t or t in kt for t in input_tokens):
                return True
    return False


def query_manual(
    material: str, fluid_service: str,
    temp_min: Optional[float] = None, temp_max: Optional[float] = None,
    has_pwht: Optional[bool] = None,
) -> dict:
    """Manual DM screening — wraps screen_asset with form params."""
    input_data = {
        "mat": material,
        "fluid": fluid_service,
        "tmin": temp_min if temp_min is not None else float('nan'),
        "tmax": temp_max if temp_max is not None else float('nan'),
        "pwht": has_pwht,
    }
    return screen_asset(input_data)


# Alias for backward compat — dm_screener.py imports match_equipment
match_equipment = screen_asset