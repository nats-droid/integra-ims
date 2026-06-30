"""
Remaining Life with Confidence Band — Per CML Point
====================================================
Approach:
  1. Short-term rate: last 2 readings → linear corrosion rate
  2. Long-term rate: all readings via OLS (statsmodels) → slope + 95% CI
  3. Governing rate: max(short-term, long-term) — conservative
  4. RL = (current_thickness - t_required) / governing_rate
  5. Confidence band: propagate CI on slope → CI on RL
     - confidence_high = uses LOWEST rate within CI (longest RL)
     - confidence_low  = uses HIGHEST rate within CI (shortest RL)

t_required = t_required_manual (engineer input from pressure design calc)
  — NOT t_min (which includes corrosion allowance, used by /plans logic)

is_low_confidence = True when readings < 3 (long-term OLS unreliable)
  → confidence_low/high = None, governing_rate = short-term only
"""

import statsmodels.api as sm
import numpy as np
from datetime import datetime
from typing import Optional


def _calc_short_term_rate(readings: list) -> Optional[float]:
    """Corrosion rate from last 2 readings (mm/year)."""
    if len(readings) < 2:
        return None
    r1, r2 = readings[-2], readings[-1]
    d1 = datetime.fromisoformat(r1["reading_date"]).toordinal()
    d2 = datetime.fromisoformat(r2["reading_date"]).toordinal()
    days = d2 - d1
    if days <= 0:
        return None
    thickness_loss = r1["reading_mm"] - r2["reading_mm"]
    rate = (thickness_loss / days) * 365.0
    return max(rate, 0.0)


def _calc_long_term_ols(readings: list) -> dict:
    """
    OLS regression: thickness ~ time (ordinal days).
    Returns slope (mm/year), CI bounds, R².
    Slope is typically negative (thickness decreasing) — we negate for CR.
    """
    base = datetime.fromisoformat(readings[0]["reading_date"]).toordinal()
    days = np.array([
        datetime.fromisoformat(r["reading_date"]).toordinal() - base
        for r in readings
    ], dtype=float)
    thickness = np.array([r["reading_mm"] for r in readings], dtype=float)

    X = sm.add_constant(days)
    model = sm.OLS(thickness, X).fit()

    slope_per_day = model.params[1]
    cr_long_term = -slope_per_day * 365.0  # mm/year, positive = corroding

    # 95% CI on slope
    ci = model.conf_int(alpha=0.05)
    slope_ci_low_per_day = ci[1, 0]   # more negative = faster corrosion
    slope_ci_high_per_day = ci[1, 1]  # less negative = slower corrosion

    cr_ci_low = -slope_ci_high_per_day * 365.0   # slowest rate in CI
    cr_ci_high = -slope_ci_low_per_day * 365.0    # fastest rate in CI

    # Clamp negatives to 0 (net thickening)
    cr_long_term = max(cr_long_term, 0.0)
    cr_ci_low = max(cr_ci_low, 0.0)
    cr_ci_high = max(cr_ci_high, 0.0)

    return {
        "cr_long_term": round(cr_long_term, 6),
        "cr_ci_low": round(cr_ci_low, 6),
        "cr_ci_high": round(cr_ci_high, 6),
        "r_squared": round(float(model.rsquared), 4),
        "n_points": len(readings),
    }


def calculate_cml_confidence(readings: list, t_required: Optional[float]) -> dict:
    """
    Calculate remaining life with confidence band for a single CML point.

    Args:
        readings: list of {reading_date, reading_mm}, sorted ascending
        t_required: minimum required thickness from design calc (mm)
                    MUST be provided — no fallback to t_min

    Returns dict with all fields. If t_required is None, returns
    status="missing_t_required" without calculating RL.
    """
    result = {
        "status": "success",
        "corrosion_rate_short_term": None,
        "corrosion_rate_long_term": None,
        "governing_rate": None,
        "predicted_rl_years": None,
        "confidence_low": None,
        "confidence_high": None,
        "is_low_confidence": len(readings) < 3,
        "model_version": "ols_v1",
        "current_thickness": None,
        "t_required": t_required,
        "n_readings": len(readings),
    }

    # Gate: t_required must be provided
    if t_required is None:
        result["status"] = "missing_t_required"
        result["message"] = (
            "t_required belum diisi untuk CML ini — input manual diperlukan "
            "sebelum Remaining Life dapat dihitung"
        )
        return result

    if not readings:
        result["status"] = "no_readings"
        return result

    current_thickness = readings[-1]["reading_mm"]
    result["current_thickness"] = current_thickness

    # Short-term rate
    short_term = _calc_short_term_rate(readings)
    result["corrosion_rate_short_term"] = round(short_term, 6) if short_term is not None else None

    # Long-term OLS (>= 3 readings)
    if len(readings) >= 3:
        ols = _calc_long_term_ols(readings)
        result["corrosion_rate_long_term"] = ols["cr_long_term"]
        result["r_squared"] = ols["r_squared"]
        ci_low_rate = ols["cr_ci_low"]
        ci_high_rate = ols["cr_ci_high"]
    else:
        ci_low_rate = None
        ci_high_rate = None

    # Governing rate: max(short-term, long-term)
    if len(readings) >= 3 and short_term is not None:
        governing = max(short_term, result["corrosion_rate_long_term"])
    elif short_term is not None:
        governing = short_term
    else:
        result["status"] = "insufficient_data"
        return result

    result["governing_rate"] = round(governing, 6)

    # Predicted RL: (t_actual - t_required) / governing_rate
    remaining_thickness = current_thickness - t_required
    if governing > 0 and remaining_thickness > 0:
        result["predicted_rl_years"] = round(remaining_thickness / governing, 2)
    elif remaining_thickness <= 0:
        result["predicted_rl_years"] = 0.0
    else:
        result["predicted_rl_years"] = 50.0  # cap for zero corrosion

    # Confidence band (>= 3 readings + valid CI)
    if ci_low_rate is not None and ci_high_rate is not None and remaining_thickness > 0:
        if ci_high_rate > 0:
            result["confidence_low"] = round(remaining_thickness / ci_high_rate, 2)
        else:
            result["confidence_low"] = 50.0
        if ci_low_rate > 0:
            result["confidence_high"] = round(remaining_thickness / ci_low_rate, 2)
        else:
            result["confidence_high"] = 50.0

    return result
