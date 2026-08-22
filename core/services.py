"""Data, model and MLflow services for EMIPredict AI.

This module is the single access point between the UI layer and the trained
artifacts. The prediction logic is unchanged from the original application:
raw profile -> engineer_features() -> ALL_FEATURES -> fitted sklearn pipeline.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import streamlit as st

from emi_features import engineer_features, ALL_FEATURES

DATA_PATH = "emi_prediction_dataset.csv"
MODEL_DIR = "models"
MLFLOW_DB = "mlflow.db"
APP_DB = "app_data.db"

CLASS_ORDER = ["Eligible", "High_Risk", "Not_Eligible"]
CLASS_COLORS = {"Eligible": "#22C55E", "High_Risk": "#F59E0B", "Not_Eligible": "#EF4444"}
SCENARIOS = ["E-commerce Shopping EMI", "Home Appliances EMI", "Vehicle EMI",
             "Personal Loan EMI", "Education EMI"]


# ============================ model artifacts ============================
@st.cache_resource(show_spinner=False)
def load_models():
    """Load the production pipelines exported by the notebook. Returns None on failure."""
    try:
        clf = joblib.load(os.path.join(MODEL_DIR, "best_classifier.pkl"))
        reg = joblib.load(os.path.join(MODEL_DIR, "best_regressor.pkl"))
        le = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))
        with open(os.path.join(MODEL_DIR, "metadata.json")) as f:
            meta = json.load(f)
        return {"clf": clf, "reg": reg, "le": le, "meta": meta, "error": None}
    except Exception as exc:                       # noqa: BLE001 - surfaced in the UI
        return {"clf": None, "reg": None, "le": None, "meta": {}, "error": str(exc)}


@st.cache_data(show_spinner=False)
def load_model_comparisons():
    """Validation-set comparison tables + held-out test metrics written by the notebook."""
    out = {"clf": None, "reg": None, "test": {}}
    try:
        out["clf"] = pd.read_json(os.path.join(MODEL_DIR, "clf_comparison.json"))
        out["reg"] = pd.read_json(os.path.join(MODEL_DIR, "reg_comparison.json"))
    except Exception:                              # noqa: BLE001
        pass
    try:
        with open(os.path.join(MODEL_DIR, "test_metrics.json")) as f:
            out["test"] = json.load(f)
    except Exception:                              # noqa: BLE001
        pass
    return out


# ============================ dataset ============================
@st.cache_data(show_spinner=False)
def load_sample(n: int = 60_000) -> pd.DataFrame | None:
    """Stratified-ish working sample of the dataset for analytics and exploration.

    The full file has ~400K rows; loading all of it into the browser session is
    unnecessary, so a bounded sample is read and lightly cleaned using the same
    rules as notebook Section 2.
    """
    if not os.path.exists(DATA_PATH):
        return None
    df = pd.read_csv(DATA_PATH, low_memory=False, nrows=250_000)

    for c in ["age", "monthly_salary", "bank_balance"]:
        df[c] = pd.to_numeric(
            df[c].astype(str).str.extract(r"^(-?\d+\.?\d*)")[0], errors="coerce")
    df["gender"] = (df["gender"].astype(str).str.strip().str.lower()
                    .map({"male": "Male", "m": "Male", "female": "Female", "f": "Female"}))
    df.loc[(df["credit_score"] < 300) | (df["credit_score"] > 850), "credit_score"] = np.nan
    df = df.dropna(subset=["age", "monthly_salary", "emi_eligibility"])

    if len(df) > n:
        df = df.sample(n, random_state=42)
    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def dataset_profile() -> dict:
    """Headline dataset facts, counted from the actual file (not hardcoded)."""
    info = {"available": os.path.exists(DATA_PATH), "rows": None, "features": None,
            "scenarios": None, "targets": 2, "size_mb": None}
    if not info["available"]:
        return info
    info["size_mb"] = round(os.path.getsize(DATA_PATH) / 1e6, 1)
    try:
        with open(DATA_PATH, "r", encoding="utf-8", errors="ignore") as f:
            header = f.readline()
            info["rows"] = sum(1 for _ in f)
        cols = [c.strip() for c in header.split(",")]
        info["features"] = len(cols) - 2          # minus the two target columns
        info["columns"] = cols
    except Exception:                              # noqa: BLE001
        pass
    sample = load_sample(20_000)
    if sample is not None and "emi_scenario" in sample:
        info["scenarios"] = int(sample["emi_scenario"].nunique())
    return info


# ============================ prediction ============================
def build_profile_frame(profile: dict) -> pd.DataFrame:
    """Raw 22-variable profile dict -> single-row DataFrame in training column order."""
    return pd.DataFrame([profile])


def run_assessment(profile: dict) -> dict:
    """Run both production models against one applicant profile.

    Identical logic to the original application — no rounding, clipping or
    post-processing is applied to the model outputs.
    """
    bundle = load_models()
    if bundle["error"]:
        raise RuntimeError(bundle["error"])

    clf, reg, le, meta = bundle["clf"], bundle["reg"], bundle["le"], bundle["meta"]
    raw = build_profile_frame(profile)
    engineered = engineer_features(raw)
    X = engineered[ALL_FEATURES]

    proba = clf.predict_proba(X)[0]
    class_names = meta.get("class_names") or list(getattr(le, "classes_", CLASS_ORDER))
    pred_idx = int(np.argmax(proba))
    label = class_names[pred_idx]

    max_emi = float(reg.predict(X)[0])

    return {
        "label": label,
        "confidence": float(proba[pred_idx]),
        "probabilities": {c: float(p) for c, p in zip(class_names, proba)},
        "max_monthly_emi": max_emi,
        "engineered": engineered.iloc[0].to_dict(),
        "profile": dict(profile),
        "models": {"classifier": meta.get("best_classifier", "—"),
                   "regressor": meta.get("best_regressor", "—")},
        "timestamp": datetime.now().strftime("%d %b %Y, %H:%M:%S"),
    }


def amortized_emi(principal: float, annual_rate_pct: float, months: int) -> float:
    """Standard reducing-balance EMI. Used only to express the requested loan as a
    monthly obligation for comparison — it is not a model output."""
    months = max(int(months), 1)
    r = annual_rate_pct / 100 / 12
    if r == 0:
        return principal / months
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)


def affordable_principal(max_emi: float, annual_rate_pct: float, months: int) -> float:
    """Invert the EMI formula to express safe capacity as a loan amount."""
    per_unit = amortized_emi(1.0, annual_rate_pct, months)
    return max_emi / per_unit if per_unit else 0.0


def derive_insights(result: dict) -> tuple[list[str], list[str]]:
    """Explain the assessment using engineered features the models actually consumed.

    Every statement below references a feature present in ALL_FEATURES, so nothing
    is attributed to the model that it did not see.
    """
    e = result["engineered"]
    p = result["profile"]
    positives: list[str] = []
    risks: list[str] = []

    dti = e.get("debt_to_income", 0)
    if dti <= 0.15:
        positives.append(f"Low existing debt-to-income ratio ({dti:.0%} of monthly income).")
    elif dti > 0.35:
        risks.append(f"High existing debt burden ({dti:.0%} of monthly income committed to EMIs).")

    afford = e.get("affordability_ratio", 0)
    if afford >= 0.35:
        positives.append(f"Healthy disposable income ({afford:.0%} of salary remains after obligations).")
    elif afford < 0.15:
        risks.append(f"Limited disposable income ({afford:.0%} of salary remains after obligations).")

    band = e.get("credit_band", "")
    score = p.get("credit_score", 0)
    if band in ("Excellent", "Good"):
        positives.append(f"Strong credit profile — score {int(score)} ({band.lower()} band).")
    elif band in ("Poor", "Fair"):
        risks.append(f"Weaker credit profile — score {int(score)} ({band.lower()} band).")

    months = e.get("savings_months", 0)
    if months >= 6:
        positives.append(f"Solid liquidity buffer covering about {months:.1f} months of outgoings.")
    elif months < 2:
        risks.append(f"Thin emergency reserves — roughly {months:.1f} months of outgoings covered.")

    stability = e.get("employment_stability", 0)
    if stability >= 6:
        positives.append(
            f"Stable employment history ({p.get('years_of_employment', 0):.1f} years, "
            f"{p.get('employment_type', '')}).")
    elif stability < 2:
        risks.append(
            f"Short employment history ({p.get('years_of_employment', 0):.1f} years, "
            f"{p.get('employment_type', '')}).")

    req_ratio = e.get("requested_emi_to_income", 0)
    if req_ratio > 0.4:
        risks.append(f"Requested obligation is large relative to income ({req_ratio:.0%} of monthly salary).")
    elif req_ratio <= 0.2:
        positives.append(f"Requested obligation is modest relative to income ({req_ratio:.0%} of monthly salary).")

    exp_ratio = e.get("expense_to_income", 0)
    if exp_ratio > 0.6:
        risks.append(f"Household expenses consume {exp_ratio:.0%} of monthly income.")

    burden = e.get("dependents_burden", 0)
    if burden >= 0.6:
        risks.append(f"High dependant ratio ({p.get('dependents', 0)} of {p.get('family_size', 0)} household members).")

    return positives, risks


@st.cache_data(show_spinner=False)
def feature_importance(kind: str = "classifier", top_n: int = 12) -> pd.DataFrame | None:
    """Feature importances from the fitted production pipeline (tree models only)."""
    bundle = load_models()
    pipe = bundle["clf"] if kind == "classifier" else bundle["reg"]
    if pipe is None:
        return None
    try:
        names = pipe.named_steps["pre"].get_feature_names_out()
        step = "clf" if kind == "classifier" else "reg"
        est = pipe.named_steps[step]
        if hasattr(est, "feature_importances_"):
            vals = est.feature_importances_
        elif hasattr(est, "coef_"):
            vals = np.abs(np.atleast_2d(est.coef_)).mean(axis=0)
        else:
            return None
        s = (pd.Series(vals, index=[n.split("__", 1)[-1] for n in names])
             .sort_values(ascending=False).head(top_n))
        return s.rename("importance").reset_index().rename(columns={"index": "feature"})
    except Exception:                              # noqa: BLE001
        return None


# ============================ MLflow ============================
@st.cache_data(ttl=60, show_spinner=False)
def mlflow_status() -> dict:
    """Read the MLflow SQLite tracking store directly.

    Reading the store rather than calling a server means the dashboard works
    without `mlflow ui` running. If the store is absent (e.g. excluded from a
    cloud deployment) the caller renders an explicit 'unavailable' state.
    """
    status = {"available": False, "reason": "", "experiments": [],
              "registered": [], "total_runs": 0}

    if not os.path.exists(MLFLOW_DB):
        status["reason"] = "mlflow.db not found in the application directory."
        return status

    try:
        con = sqlite3.connect(f"file:{MLFLOW_DB}?mode=ro", uri=True)
        cur = con.cursor()

        # NOTE: outer result sets are materialised with fetchall() before the loop.
        # Re-executing on the same cursor mid-iteration would discard the outer rows.
        experiments = []
        exp_rows = cur.execute(
            "SELECT experiment_id, name FROM experiments "
            "WHERE lifecycle_stage='active' AND name != 'Default'").fetchall()
        for exp_id, name in exp_rows:
            runs = cur.execute(
                "SELECT run_uuid, name, status, start_time FROM runs "
                "WHERE experiment_id=? AND lifecycle_stage='active' "
                "ORDER BY start_time DESC", (exp_id,)).fetchall()
            run_rows = []
            for run_uuid, run_name, run_status, start in runs:
                metrics = dict(cur.execute(
                    "SELECT key, value FROM metrics WHERE run_uuid=?", (run_uuid,)).fetchall())
                run_rows.append({
                    "run_id": run_uuid,
                    "name": run_name,
                    "status": run_status,
                    "started": datetime.fromtimestamp(start / 1000).strftime("%d %b %Y %H:%M")
                    if start else "—",
                    "metrics": metrics,
                })
            experiments.append({"name": name, "id": exp_id, "runs": run_rows})
            status["total_runs"] += len(run_rows)

        registered = []
        model_rows = cur.execute("SELECT name FROM registered_models").fetchall()
        for name, in model_rows:
            versions = cur.execute(
                "SELECT version, run_id, current_stage FROM model_versions WHERE name=? "
                "ORDER BY version DESC", (name,)).fetchall()
            aliases = {}
            try:
                aliases = dict(cur.execute(
                    "SELECT alias, version FROM registered_model_aliases WHERE name=?",
                    (name,)).fetchall())
            except sqlite3.Error:
                pass
            registered.append({
                "name": name,
                "versions": [{"version": v, "run_id": r, "stage": s} for v, r, s in versions],
                "aliases": aliases,
            })

        con.close()
        status.update({"available": True, "experiments": experiments, "registered": registered})
    except Exception as exc:                       # noqa: BLE001
        status["reason"] = f"Could not read the tracking store: {exc}"
    return status


# ============================ application records (CRUD) ============================
def get_app_db() -> sqlite3.Connection:
    """Connection to the application's own record store, seeded from the dataset."""
    con = sqlite3.connect(APP_DB, check_same_thread=False)
    exists = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='records'").fetchone()
    if not exists:
        seed = load_sample(400)
        if seed is not None:
            keep = ["age", "gender", "marital_status", "education", "monthly_salary",
                    "employment_type", "credit_score", "emi_scenario", "requested_amount",
                    "requested_tenure", "emi_eligibility"]
            cols = [c for c in keep if c in seed.columns]
            seed[cols].head(150).to_sql("records", con, index=False)
        else:
            con.execute(
                "CREATE TABLE records (age INTEGER, monthly_salary REAL, credit_score REAL, "
                "emi_scenario TEXT, requested_amount REAL, requested_tenure INTEGER)")
        con.commit()
    return con


def app_version() -> str:
    meta = load_models().get("meta", {})
    return meta.get("version", "1.0.0")
