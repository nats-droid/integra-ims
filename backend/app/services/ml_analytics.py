"""
ML Analytics Engine — Integra IMS
Runs XGBoost + SHAP, KMeans, Isolation Forest,
Polynomial Regression, Weibull, Kaplan-Meier.
"""

import logging
import uuid
from datetime import datetime, date
from typing import Any

import numpy as np
import pandas as pd
from lifelines import WeibullFitter, KaplanMeierFitter
from shap import TreeExplainer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from supabase import Client
from xgboost import XGBClassifier, XGBRegressor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "corrosion_rate",
    "thickness_loss_pct",
    "age_years",
    "readings_count",
    "design_pressure",
    "design_temp_max",
]

EQ_TYPE_MAP = {
    "piping": 0,
    "vessel": 1,
    "heat_exchanger": 2,
    "tank": 3,
    "heater": 4,
}

CLUSTER_LABELS = {
    0: "Low CR Stable",
    1: "Medium CR Active",
    2: "High CR Critical",
    3: "Repaired History",
    4: "Outlier",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "+00"


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# 1. Data fetching & feature engineering
# ---------------------------------------------------------------------------

def fetch_ml_data(company_id: str, db: Client) -> pd.DataFrame:
    """Pull equipment + CMLs + readings → one row per equipment with features."""

    # --- Equipment ---
    eq_res = (
        db.table("equipment")
        .select("id, tag, type, design_pressure, design_temp_max, installation_date")
        .eq("company_id", company_id)
        .eq("is_active", True)
        .execute()
    )
    eq_map = {e["id"]: e for e in eq_res.data}

    # --- CML points ---
    cml_res = (
        db.table("cml_points")
        .select("id, equipment_id, nominal_thickness, t_required_manual")
        .eq("company_id", company_id)
        .execute()
    )
    cml_map: dict[str, dict] = {}
    eq_cmls: dict[str, list[str]] = {}
    for c in cml_res.data:
        cml_map[c["id"]] = c
        eq_cmls.setdefault(c["equipment_id"], []).append(c["id"])

    # --- Thickness readings ---
    tr_res = (
        db.table("thickness_readings")
        .select("cml_point_id, reading_mm, reading_date")
        .eq("company_id", company_id)
        .execute()
    )

    readings_by_cml: dict[str, list[dict]] = {}
    for r in tr_res.data:
        readings_by_cml.setdefault(r["cml_point_id"], []).append(r)

    # --- Per-CML feature computation ---
    cml_features: list[dict] = []
    for cml_id, cml_info in cml_map.items():
        readings = readings_by_cml.get(cml_id, [])
        if len(readings) < 2:
            continue

        dates_sorted = sorted(readings, key=lambda r: r["reading_date"])
        years = np.array(
            [float(d["reading_date"][:4]) for d in dates_sorted]
        )
        thicknesses = np.array([_safe_float(d["reading_mm"]) for d in dates_sorted])

        # Corrosion rate via linear regression slope (positive = losing thickness)
        slope, _ = np.polyfit(years, thicknesses, 1)
        cr = abs(slope)

        nominal = _safe_float(cml_info.get("nominal_thickness", 9.27))
        current = thicknesses[-1]
        loss_pct = max((nominal - current) / nominal * 100, 0.0) if nominal > 0 else 0.0

        eq_info = eq_map.get(cml_info["equipment_id"])
        if eq_info is None:
            continue

        install_str = eq_info.get("installation_date", "2000-01-01")
        try:
            install_year = int(str(install_str)[:4])
        except (ValueError, TypeError):
            install_year = 2000
        age = date.today().year - install_year

        cml_features.append(
            {
                "equipment_id": cml_info["equipment_id"],
                "corrosion_rate": cr,
                "thickness_loss_pct": loss_pct,
                "age_years": age,
                "readings_count": len(readings),
                "design_pressure": _safe_float(eq_info.get("design_pressure")),
                "design_temp_max": _safe_float(eq_info.get("design_temp_max")),
                "equipment_type_code": EQ_TYPE_MAP.get(eq_info.get("type", ""), 0),
            }
        )

    if not cml_features:
        return pd.DataFrame(columns=FEATURE_COLS + ["equipment_type_code"])

    # --- Aggregate per equipment (mean CR, max loss, etc.) ---
    df_cml = pd.DataFrame(cml_features)
    df = (
        df_cml.groupby("equipment_id")
        .agg(
            corrosion_rate=("corrosion_rate", "mean"),
            thickness_loss_pct=("thickness_loss_pct", "max"),
            age_years=("age_years", "first"),
            readings_count=("readings_count", "sum"),
            design_pressure=("design_pressure", "first"),
            design_temp_max=("design_temp_max", "first"),
            equipment_type_code=("equipment_type_code", "first"),
        )
        .reset_index()
        .set_index("equipment_id")
    )

    logger.info("fetch_ml_data: %d equipment, %d CMLs", len(df), len(cml_map))
    return df


# ---------------------------------------------------------------------------
# 2. XGBoost + SHAP
# ---------------------------------------------------------------------------

def run_xgboost_shap(df: pd.DataFrame, company_id: str, db: Client) -> int:
    """Train XGBClassifier for risk, run SHAP, insert ml_risk_predictions."""

    if df.empty:
        return 0

    # Label
    def risk_label(cr: float) -> str:
        if cr > 0.5:
            return "critical"
        if cr > 0.2:
            return "high"
        if cr > 0.1:
            return "medium"
        return "low"

    df["risk_level"] = df["corrosion_rate"].apply(risk_label)
    label_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    df["risk_code"] = df["risk_level"].map(label_map)

    X = df[FEATURE_COLS].fillna(0).values
    y = df["risk_code"].values

    # Train
    clf = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        eval_metric="mlogloss",
        random_state=42,
        verbosity=0,
    )
    clf.fit(X, y)

    # Predict probability of high + critical
    proba = clf.predict_proba(X)
    risk_score = proba[:, 2:].sum(axis=1)  # P(high) + P(critical)

    # SHAP
    explainer = TreeExplainer(clf)
    shap_values = explainer.shap_values(X)

    # Delete existing
    db.table("ml_risk_predictions").delete().eq("company_id", company_id).execute()

    # Insert
    rows = []
    for idx, eq_id in enumerate(df.index):
        # shap_values is list of arrays (one per class) or 2D array
        if isinstance(shap_values, list):
            # Multi-class: take mean absolute across all classes
            sv = np.mean([np.abs(s[idx]) for s in shap_values], axis=0)
        else:
            sv = np.abs(shap_values[idx])
        top_idx = int(np.argmax(sv))
        rows.append(
            {
                "id": _uid(),
                "company_id": company_id,
                "equipment_id": eq_id,
                "risk_score": round(float(risk_score[idx]), 4),
                "risk_level": df.at[eq_id, "risk_level"],
                "shap_values": [round(float(v), 4) for v in (sv.tolist() if not isinstance(sv.tolist()[0], list) else [sum(x) for x in zip(*sv.tolist())])],
                "computed_at": _now_iso(),
            }
        )

    if rows:
        db.table("ml_risk_predictions").insert(rows).execute()

    logger.info("run_xgboost_shap: %d predictions inserted", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# 3. KMeans clustering
# ---------------------------------------------------------------------------

def run_kmeans(df: pd.DataFrame, company_id: str, db: Client) -> int:
    """StandardScaler + KMeans(n=5) + PCA(2), insert ml_clusters."""

    if df.empty or len(df) < 5:
        return 0

    X = df[FEATURE_COLS].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=5, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_scaled)

    db.table("ml_clusters").delete().eq("company_id", company_id).execute()

    rows = []
    for idx, eq_id in enumerate(df.index):
        cid = int(labels[idx])
        rows.append(
            {
                "id": _uid(),
                "company_id": company_id,
                "equipment_id": eq_id,
                "cluster_id": cid,
                "cluster_label": CLUSTER_LABELS.get(cid, f"Cluster {cid}"),
                "pca_x": round(float(coords[idx, 0]), 4),
                "pca_y": round(float(coords[idx, 1]), 4),
                "computed_at": _now_iso(),
            }
        )

    if rows:
        db.table("ml_clusters").insert(rows).execute()

    logger.info("run_kmeans: %d clusters inserted", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# 4. Isolation Forest
# ---------------------------------------------------------------------------

def run_isolation_forest(df: pd.DataFrame, company_id: str, db: Client) -> int:
    """IsolationForest → corrosion_anomalies, insert if_score + new anomalies."""

    if df.empty:
        return 0

    X = df[FEATURE_COLS].fillna(0).values
    iso = IsolationForest(contamination=0.05, random_state=42)
    iso.fit(X)
    scores = iso.decision_function(X)  # lower = more anomalous

    flagged_ids = set()
    for idx, eq_id in enumerate(df.index):
        if scores[idx] < 0:
            flagged_ids.add(eq_id)

    # Fetch existing anomalies
    existing = (
        db.table("corrosion_anomalies")
        .select("id, cml_point_id")
        .eq("company_id", company_id)
        .execute()
    )

    # Fetch CMLs for flagged equipment
    cml_res = (
        db.table("cml_points")
        .select("id, equipment_id")
        .eq("company_id", company_id)
        .in_("equipment_id", list(flagged_ids))
        .execute()
    )

    existing_cml_ids = {e["cml_point_id"] for e in existing.data}
    new_cmls = [c for c in cml_res.data if c["id"] not in existing_cml_ids]

    # Build anomaly score map per equipment
    eq_score_map = {
        eq_id: round(float(scores[idx]), 4)
        for idx, eq_id in enumerate(df.index)
        if eq_id in flagged_ids
    }

    # Insert new anomalies
    new_rows = []
    for cml in new_cmls:
        eq_id = cml["equipment_id"]
        score = eq_score_map.get(eq_id, 0.0)
        new_rows.append(
            {
                "id": _uid(),
                "company_id": company_id,
                "cml_point_id": cml["id"],
                "anomaly_score": score,
                "description": f"Isolation Forest anomaly (score={score:.3f})",
                "detected_at": _now_iso(),
                "thickness_reading_id": None,
            }
        )

    if new_rows:
        db.table("corrosion_anomalies").insert(new_rows).execute()

    logger.info(
        "run_isolation_forest: %d flagged, %d new anomalies",
        len(flagged_ids),
        len(new_rows),
    )
    return len(flagged_ids)


# ---------------------------------------------------------------------------
# 5. Polynomial regression trends
# ---------------------------------------------------------------------------

def run_regression_trends(company_id: str, db: Client) -> int:
    """Per CML: degree-2 polynomial fit, R², projected 5/10yr, insert ml_regression_trends."""

    # Fetch CMLs
    cml_res = (
        db.table("cml_points")
        .select("id, equipment_id, nominal_thickness, t_required_manual")
        .eq("company_id", company_id)
        .execute()
    )

    if not cml_res.data:
        return 0

    # Fetch readings
    tr_res = (
        db.table("thickness_readings")
        .select("cml_point_id, reading_mm, reading_date")
        .eq("company_id", company_id)
        .execute()
    )

    readings_by_cml: dict[str, list[dict]] = {}
    for r in tr_res.data:
        readings_by_cml.setdefault(r["cml_point_id"], []).append(r)

    db.table("ml_regression_trends").delete().eq("company_id", company_id).execute()

    current_year = date.today().year
    rows = []

    for cml in cml_res.data:
        readings = readings_by_cml.get(cml["id"], [])
        if len(readings) < 3:
            continue

        dates_sorted = sorted(readings, key=lambda r: r["reading_date"])
        years = np.array([float(d["reading_date"][:4]) for d in dates_sorted]).reshape(
            -1, 1
        )
        thicknesses = np.array([_safe_float(d["reading_mm"]) for d in dates_sorted])

        # Degree-2 polynomial
        poly = PolynomialFeatures(degree=2, include_bias=False)
        X_poly = poly.fit_transform(years)
        reg = LinearRegression()
        reg.fit(X_poly, thicknesses)
        y_pred = reg.predict(X_poly)
        r2 = r2_score(thicknesses, y_pred)

        # Projections
        future_years = np.array(
            [[current_year + 5], [current_year + 10]], dtype=float
        )
        X_future = poly.transform(future_years)
        projections = reg.predict(X_future)

        t_req = _safe_float(cml.get("t_required_manual"))
        rows.append(
            {
                "id": _uid(),
                "company_id": company_id,
                "cml_point_id": cml["id"],
                "equipment_id": cml["equipment_id"],
                "r_squared": round(float(r2), 4),
                "projected_thickness": {"5yr": round(float(projections[0]), 3), "10yr": round(float(projections[1]), 3)},
                "computed_at": _now_iso(),
            }
        )

    if rows:
        db.table("ml_regression_trends").insert(rows).execute()

    logger.info("run_regression_trends: %d trends inserted", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# 6. Weibull analysis
# ---------------------------------------------------------------------------

def run_weibull(company_id: str, db: Client) -> int:
    """Per CML: TTF = years until thickness < t_required at current CR.
    Fit WeibullFitter per equipment. Insert ml_weibull_results."""

    # Fetch CMLs
    cml_res = (
        db.table("cml_points")
        .select("id, equipment_id, nominal_thickness, t_required_manual")
        .eq("company_id", company_id)
        .execute()
    )

    if not cml_res.data:
        return 0

    # Fetch readings
    tr_res = (
        db.table("thickness_readings")
        .select("cml_point_id, reading_mm, reading_date")
        .eq("company_id", company_id)
        .execute()
    )

    readings_by_cml: dict[str, list[dict]] = {}
    for r in tr_res.data:
        readings_by_cml.setdefault(r["cml_point_id"], []).append(r)

    # Per-CML TTF
    eq_ttfs: dict[str, list[float]] = {}

    for cml in cml_res.data:
        readings = readings_by_cml.get(cml["id"], [])
        if len(readings) < 2:
            continue

        dates_sorted = sorted(readings, key=lambda r: r["reading_date"])
        years = np.array([float(d["reading_date"][:4]) for d in dates_sorted])
        thicknesses = np.array([_safe_float(d["reading_mm"]) for d in dates_sorted])

        slope, intercept = np.polyfit(years, thicknesses, 1)
        cr = abs(slope)

        current_thickness = thicknesses[-1]
        t_req = _safe_float(cml.get("t_required_manual"))

        if cr > 0.001 and t_req > 0:
            ttf = max((current_thickness - t_req) / cr, 0.0)
        else:
            ttf = 100.0  # effectively infinite

        eq_id = cml["equipment_id"]
        eq_ttfs.setdefault(eq_id, []).append(ttf)

    # Fit Weibull per equipment
    db.table("ml_weibull_results").delete().eq("company_id", company_id).execute()
    current_year = date.today().year
    rows = []

    for eq_id, ttfs in eq_ttfs.items():
        ttf_arr = np.array(ttfs)
        ttf_arr = ttf_arr[ttf_arr > 0]  # remove zero/negative

        if len(ttf_arr) < 2:
            continue

        try:
            wf = WeibullFitter()
            wf.fit(ttf_arr, event_observed=np.ones(len(ttf_arr)))

            beta = round(float(wf.rho_), 4)  # shape
            eta = round(float(wf.lambda_), 4)  # scale

            # B10, B50 (quantiles)
            b10 = round(float(wf.predict(0.10)), 2)
            b50 = round(float(wf.predict(0.50)), 2)

            # PoF curve: t=0..30 years
            pof_curve = []
            for t in range(31):
                sf = wf.survival_function_at_times([t])
                sf_val = float(np.array(sf).flat[0])
                p = float(1 - sf_val)
                pof_curve.append({"t": t, "pof": round(p, 4)})

            rows.append(
                {
                    "id": _uid(),
                    "company_id": company_id,
                    "beta": beta,
                    "eta": eta,
                    "b10_life": b10,
                    "b50_life": b50,
                    "pof_curve": pof_curve,
                    "computed_at": _now_iso(),
                }
            )
        except Exception as e:
            logger.warning("Weibull failed for %s: %s", eq_id, e)
            continue

    if rows:
        db.table("ml_weibull_results").insert(rows).execute()

    logger.info("run_weibull: %d results inserted", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# 7. Survival analysis (Kaplan-Meier)
# ---------------------------------------------------------------------------

def run_survival(company_id: str, db: Client) -> int:
    """Per CML: years remaining = (current - t_required) / CR.
    event=1 if already failed. KaplanMeierFitter per equipment."""

    # Fetch CMLs
    cml_res = (
        db.table("cml_points")
        .select("id, equipment_id, nominal_thickness, t_required_manual")
        .eq("company_id", company_id)
        .execute()
    )

    if not cml_res.data:
        return 0

    # Fetch readings
    tr_res = (
        db.table("thickness_readings")
        .select("cml_point_id, reading_mm, reading_date")
        .eq("company_id", company_id)
        .execute()
    )

    readings_by_cml: dict[str, list[dict]] = {}
    for r in tr_res.data:
        readings_by_cml.setdefault(r["cml_point_id"], []).append(r)

    # Per-CML survival data
    eq_durations: dict[str, list[float]] = {}
    eq_events: dict[str, list[int]] = {}

    for cml in cml_res.data:
        readings = readings_by_cml.get(cml["id"], [])
        if len(readings) < 2:
            continue

        dates_sorted = sorted(readings, key=lambda r: r["reading_date"])
        years = np.array([float(d["reading_date"][:4]) for d in dates_sorted])
        thicknesses = np.array([_safe_float(d["reading_mm"]) for d in dates_sorted])

        slope, _ = np.polyfit(years, thicknesses, 1)
        cr = abs(slope)
        current_thickness = thicknesses[-1]
        t_req = _safe_float(cml.get("t_required_manual"))

        if cr > 0.001:
            duration = (current_thickness - t_req) / cr
            duration = max(duration, 0.1)
        else:
            duration = 100.0

        event = 1 if current_thickness < t_req else 0

        eq_id = cml["equipment_id"]
        eq_durations.setdefault(eq_id, []).append(duration)
        eq_events.setdefault(eq_id, []).append(event)

    # Fit KM per equipment
    db.table("ml_survival_results").delete().eq("company_id", company_id).execute()
    rows = []

    for eq_id in eq_durations:
        durations = np.array(eq_durations[eq_id])
        events = np.array(eq_events[eq_id])

        if len(durations) < 2:
            continue

        try:
            kmf = KaplanMeierFitter()
            kmf.fit(durations, event_observed=events)

            import math
            def safe_f(v, default=0.0):
                try:
                    f = float(v)
                    return f if math.isfinite(f) else default
                except:
                    return default

            median = safe_f(kmf.median_survival_time_, default=100.0)
            ci = kmf.confidence_interval_survival_function_
            ci_times = ci.index.values
            closest_idx = int(np.argmin(np.abs(ci_times - min(median, float(ci_times.max())))))
            ci_low = round(safe_f(ci.iloc[closest_idx, 0], default=0.0), 2)
            ci_high = round(safe_f(ci.iloc[closest_idx, 1], default=1.0), 2)

            # Survival curve: 30 sample points
            sf = kmf.survival_function_
            max_t = min(float(sf.index.max()), 50.0)
            sample_times = np.linspace(0, max_t, 30)
            survival_curve = []
            import math
            def safe_float(v):
                try:
                    f = float(v)
                    return f if math.isfinite(f) else None
                except:
                    return None
            for t in sample_times:
                s_val = float(np.array(kmf.survival_function_at_times([t])).flat[0])
                sf = safe_float(s_val)
                if sf is not None:
                    survival_curve.append({"t": t, "survival": round(sf, 4)})

            rows.append(
                {
                    "id": _uid(),
                    "company_id": company_id,
                    "median_survival": round(median, 2),
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "survival_curve": survival_curve,
                    "computed_at": _now_iso(),
                }
            )
        except Exception as e:
            logger.warning("KM failed for %s: %s", eq_id, e)
            continue

    if rows:
        db.table("ml_survival_results").insert(rows).execute()

    logger.info("run_survival: %d results inserted", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# 8. Run all ML modules
# ---------------------------------------------------------------------------

def run_all_ml(company_id: str, db: Client) -> dict:
    """Execute all ML modules sequentially, log to ml_run_log."""

    started = datetime.utcnow()
    logger.info("run_all_ml START company=%s", company_id)

    # 1. Fetch data
    df = fetch_ml_data(company_id, db)
    equipment_count = len(df)

    results: dict[str, int | str] = {
        "equipment_count": equipment_count,
        "status": "success",
    }

    try:
        # 2. XGBoost + SHAP
        results["xgboost_shap"] = run_xgboost_shap(df, company_id, db)

        # 3. KMeans
        results["kmeans"] = run_kmeans(df, company_id, db)

        # 4. Isolation Forest
        results["isolation_forest"] = run_isolation_forest(df, company_id, db)

        # 5. Regression trends
        results["regression_trends"] = run_regression_trends(company_id, db)

        # 6. Weibull
        results["weibull"] = run_weibull(company_id, db)

        # 7. Survival
        results["survival"] = run_survival(company_id, db)

    except Exception as e:
        logger.error("run_all_ml FAILED: %s", e)
        results["status"] = f"error: {e}"

    completed = datetime.utcnow()
    duration = round((completed - started).total_seconds(), 2)

    # Log run
    log_row = {
        "id": _uid(),
        "company_id": company_id,
        "started_at": started.isoformat() + "+00",
        "completed_at": completed.isoformat() + "+00",
        "status": str(results["status"]),
        "equipment_count": equipment_count,
        "duration_seconds": duration,
        "error_message": results.get("error"),
    }

    try:
        db.table("ml_run_log").insert(log_row).execute()
    except Exception as e:
        logger.warning("ml_run_log insert failed: %s", e)

    logger.info("run_all_ml DONE in %.1fs — %s", duration, results)
    return results
