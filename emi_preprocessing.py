"""Data preprocessing and cleaning pipeline for the EMIPredict AI dataset.

Every rule in this module mirrors Section 2 of EMIPredict_AI.ipynb. It is packaged
separately so the cleaning logic is reusable and testable outside the notebook —
for a scheduled retraining job, a batch scoring run, or validating a new data drop.

Usage
-----
    from emi_preprocessing import clean_dataset, quality_audit

    raw = pd.read_csv("emi_prediction_dataset.csv", low_memory=False)
    audit_before = quality_audit(raw)
    clean, report = clean_dataset(raw)

Each transformation is deliberate and documented, because a regulated lender must
be able to explain every change made to an applicant's data.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Domain rules (from the project specification)
# ----------------------------------------------------------------------------
NUMERIC_TEXT_COLUMNS = ["age", "monthly_salary", "bank_balance"]

GENDER_MAP = {"male": "Male", "m": "Male", "female": "Female", "f": "Female"}

CREDIT_SCORE_RANGE = (300, 850)
MAX_EMI_RANGE = (500, 50_000)

WINSORIZE_COLUMNS = ["monthly_salary", "bank_balance", "emergency_fund",
                     "current_emi_amount", "monthly_rent"]
WINSORIZE_QUANTILES = (0.005, 0.995)

EXPENSE_COLUMNS = ["monthly_rent", "school_fees", "college_fees",
                   "travel_expenses", "groceries_utilities", "other_monthly_expenses"]


# ----------------------------------------------------------------------------
# Quality assessment
# ----------------------------------------------------------------------------
def repair_numeric(value):
    """Repair values corrupted with duplicated decimal suffixes.

    The raw extract contains entries such as '64300.0.0' and '23400.0.0.0', which
    pandas reads as text and which break the whole column's dtype. The leading
    valid float is the true value.

    >>> repair_numeric("64300.0.0")
    64300.0
    """
    if pd.isna(value):
        return np.nan
    match = re.match(r"^-?\d+(?:\.\d+)?", str(value).strip())
    return float(match.group()) if match else np.nan


def quality_audit(df: pd.DataFrame) -> dict:
    """Profile the defects present in a raw extract, without modifying it."""
    audit = {
        "rows": int(len(df)),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_by_column": {k: int(v) for k, v in
                              df.isna().sum()[df.isna().sum() > 0].items()},
    }

    corrupt = {}
    for col in NUMERIC_TEXT_COLUMNS:
        if col in df.columns and df[col].dtype == object:
            coerced = pd.to_numeric(df[col], errors="coerce")
            corrupt[col] = int((coerced.isna() & df[col].notna()).sum())
    audit["corrupt_numeric_values"] = corrupt

    if "gender" in df.columns:
        audit["gender_variants"] = int(df["gender"].nunique())
    if "credit_score" in df.columns:
        lo, hi = CREDIT_SCORE_RANGE
        audit["invalid_credit_scores"] = int(
            ((df["credit_score"] < lo) | (df["credit_score"] > hi)).sum())
    if {"house_type", "monthly_rent"} <= set(df.columns):
        audit["owners_paying_rent"] = int(
            ((df["house_type"] == "Own") & (df["monthly_rent"] > 0)).sum())
    return audit


# ----------------------------------------------------------------------------
# Cleaning steps
# ----------------------------------------------------------------------------
def fix_numeric_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Step 1 — repair corrupted numeric strings and restore numeric dtypes."""
    repaired = {}
    for col in NUMERIC_TEXT_COLUMNS:
        if col in df.columns and df[col].dtype == object:
            before = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
            df[col] = df[col].map(repair_numeric)
            repaired[col] = int(before.sum())
    if "age" in df.columns:
        df["age"] = df["age"].astype("Int64").astype(int)
    return df, repaired


def standardize_categories(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Step 2 — collapse categorical label variants to canonical values."""
    variants = int(df["gender"].nunique()) if "gender" in df.columns else 0
    if "gender" in df.columns:
        df["gender"] = df["gender"].astype(str).str.strip().str.lower().map(GENDER_MAP)
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].str.strip()
    return df, variants


def apply_domain_rules(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Step 3 — enforce the documented domain constraints.

    Credit scores outside 300-850 are impossible, so they are treated as missing
    rather than trusted. Home owners cannot pay rent. The regression target is
    bounded by its documented range.
    """
    counts = {}
    lo, hi = CREDIT_SCORE_RANGE
    invalid = (df["credit_score"] < lo) | (df["credit_score"] > hi)
    df.loc[invalid, "credit_score"] = np.nan
    counts["invalid_credit_scores"] = int(invalid.sum())

    owners_rent = (df["house_type"] == "Own") & (df["monthly_rent"] > 0)
    df.loc[owners_rent, "monthly_rent"] = 0
    counts["owner_rent_zeroed"] = int(owners_rent.sum())

    if "max_monthly_emi" in df.columns:
        lo_t, hi_t = MAX_EMI_RANGE
        out = ((df["max_monthly_emi"] < lo_t) | (df["max_monthly_emi"] > hi_t)).sum()
        df["max_monthly_emi"] = df["max_monthly_emi"].clip(lo_t, hi_t)
        counts["target_values_clipped"] = int(out)
    return df, counts


def impute_missing(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Step 4 — column-specific imputation.

    Strategies differ by column on purpose. Education is categorical, so the mode
    preserves its distribution. Rent depends strongly on housing type, so it is
    imputed within house_type — a global median would assign rent to owners.
    The remaining money columns are right-skewed, so the median is used rather
    than the mean, which the affluent tail would distort.
    """
    filled = {}
    if "education" in df.columns and df["education"].isna().any():
        filled["education"] = int(df["education"].isna().sum())
        df["education"] = df["education"].fillna(df["education"].mode()[0])

    if {"monthly_rent", "house_type"} <= set(df.columns):
        filled["monthly_rent"] = int(df["monthly_rent"].isna().sum())
        df["monthly_rent"] = df.groupby("house_type")["monthly_rent"].transform(
            lambda s: s.fillna(s.median()))

    for col in ["credit_score", "bank_balance", "emergency_fund"]:
        if col in df.columns and df[col].isna().any():
            filled[col] = int(df[col].isna().sum())
            df[col] = df[col].fillna(df[col].median())
    return df, filled


def winsorize(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Step 5 — cap extreme values instead of dropping the records.

    A very high salary or bank balance is a legitimate applicant, not a data
    error. Removing those rows would bias the model against high-income
    customers, so their leverage is limited by capping instead.
    """
    capped = {}
    q_lo, q_hi = WINSORIZE_QUANTILES
    for col in WINSORIZE_COLUMNS:
        if col in df.columns:
            lo, hi = df[col].quantile([q_lo, q_hi])
            capped[col] = int(((df[col] < lo) | (df[col] > hi)).sum())
            df[col] = df[col].clip(lo, hi)
    return df, capped


def drop_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Step 6 — remove exact duplicate records."""
    n = int(df.duplicated().sum())
    return df.drop_duplicates().reset_index(drop=True), n


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------
def clean_dataset(df: pd.DataFrame, verbose: bool = False,
                  final_dedup: bool = False) -> tuple[pd.DataFrame, dict]:
    """Run the full cleaning pipeline.

    Returns the cleaned frame and a report describing every change applied, so the
    transformation is auditable rather than opaque.

    Step order matches the training notebook exactly, so this module reproduces the
    dataset the production models were trained on. Set ``final_dedup=True`` to also
    remove the handful of exact duplicates that winsorization can create; this
    yields marginally cleaner data but no longer matches the notebook row count.
    """
    report = {"before": quality_audit(df)}
    out = df.copy()

    out, report["numeric_repaired"] = fix_numeric_columns(out)
    out, report["gender_variants_before"] = standardize_categories(out)
    out, report["domain_rules"] = apply_domain_rules(out)
    out, report["imputed"] = impute_missing(out)
    out, report["duplicates_dropped"] = drop_duplicates(out)
    out, report["winsorized"] = winsorize(out)

    if final_dedup:
        out, extra = drop_duplicates(out)
        report["duplicates_dropped"] += extra
        report["final_dedup_removed"] = extra

    report["after"] = quality_audit(out)

    if verbose:
        print_report(report)
    return out, report


def print_report(report: dict) -> None:
    """Human-readable before/after summary."""
    b, a = report["before"], report["after"]
    print("DATA QUALITY REPORT")
    print("=" * 58)
    print(f"{'Check':<32}{'Before':>12}{'After':>12}")
    print("-" * 58)
    rows = [
        ("Rows", b["rows"], a["rows"]),
        ("Missing cells", b["missing_cells"], a["missing_cells"]),
        ("Duplicate rows", b["duplicate_rows"], a["duplicate_rows"]),
        ("Corrupt numeric strings",
         sum(b.get("corrupt_numeric_values", {}).values()),
         sum(a.get("corrupt_numeric_values", {}).values())),
        ("Gender label variants", b.get("gender_variants", 0), a.get("gender_variants", 0)),
        ("Invalid credit scores", b.get("invalid_credit_scores", 0),
         a.get("invalid_credit_scores", 0)),
        ("Owners paying rent", b.get("owners_paying_rent", 0), a.get("owners_paying_rent", 0)),
    ]
    for label, before, after in rows:
        print(f"{label:<32}{before:>12,}{after:>12,}")
    print("-" * 58)
    print(f"Values capped (winsorized): {sum(report['winsorized'].values()):,}")
    print(f"Values imputed:             {sum(report['imputed'].values()):,}")

    residual = a["duplicate_rows"]
    if residual:
        print()
        print(f"Note: {residual} exact duplicates are present after cleaning. These are a")
        print("by-product of winsorization — capping extreme values can make two rows that")
        print("differed only in the capped column identical. Deduplication runs before")
        print("winsorization to match the training notebook; pass final_dedup=True to")
        print("clean_dataset() to remove them as well.")


def total_expenses(df: pd.DataFrame) -> pd.Series:
    """Convenience helper: total monthly household expenditure."""
    return df[[c for c in EXPENSE_COLUMNS if c in df.columns]].sum(axis=1)


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "emi_prediction_dataset.csv"
    raw = pd.read_csv(path, low_memory=False)
    cleaned, report = clean_dataset(raw, verbose=True)
    out_path = "emi_dataset_cleaned.csv"
    cleaned.to_csv(out_path, index=False)
    print(f"\nCleaned dataset written to {out_path} ({len(cleaned):,} rows)")
