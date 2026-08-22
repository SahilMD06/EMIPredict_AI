"""Reports — formatted assessment report with PDF and CSV export."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from components import cards, shell
from core import services
from utils.formatting import inr, pct


def render() -> None:
    shell.render_header("Reports", "Assessment Reporting")

    result = st.session_state.get("assessment")
    if not result:
        cards.empty_state(
            "No Assessment Available",
            "Reports are generated from a completed assessment. Run an assessment "
            "first, then return here to review and export it.")
        if st.button("Start Assessment", type="primary"):
            shell.goto("EMI Assessment")
        return

    p = result["profile"]
    e = result["engineered"]
    max_emi = result["max_monthly_emi"]
    rate = result.get("interest_rate", 12.0)
    proposed = services.amortized_emi(p["requested_amount"], rate, p["requested_tenure"])

    cards.kpi_row([
        {"label": "Eligibility Decision", "value": result["label"].replace("_", " "),
         "sub": f"{result['confidence']:.1%} model confidence",
         "tone": {"Eligible": "ok", "High_Risk": "warn",
                  "Not_Eligible": "bad"}.get(result["label"], "neutral")},
        {"label": "Maximum Safe EMI", "value": inr(max_emi),
         "sub": "Model-estimated monthly capacity"},
        {"label": "Requested Instalment", "value": inr(proposed),
         "sub": f"{p['requested_tenure']} months at {rate:.1f}% p.a."},
        {"label": "Assessed", "value": result["timestamp"].split(",")[0],
         "sub": result["timestamp"].split(",")[-1].strip()},
    ])

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ---------------- export ----------------
    c1, c2, _ = st.columns([1.2, 1.2, 2.6], gap="small")

    pdf_bytes, pdf_error = None, None
    try:
        from core.report import build_report
        pdf_bytes = build_report(result)
    except ImportError:
        pdf_error = ("PDF export requires the reportlab package. "
                     "Install it with: pip install reportlab")
    except Exception as exc:                       # noqa: BLE001
        pdf_error = f"The report could not be generated: {exc}"

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    if pdf_bytes:
        c1.download_button("Download Assessment Report (PDF)", pdf_bytes,
                           file_name=f"emipredict_assessment_{stamp}.pdf",
                           mime="application/pdf", type="primary",
                           use_container_width=True)
    else:
        c1.button("PDF Unavailable", disabled=True, use_container_width=True)

    record = {**p,
              "predicted_eligibility": result["label"],
              "model_confidence": round(result["confidence"], 4),
              "max_monthly_emi": round(max_emi, 2),
              "requested_monthly_instalment": round(proposed, 2),
              "assumed_interest_rate_pct": rate,
              "debt_to_income": round(e.get("debt_to_income", 0), 4),
              "expense_to_income": round(e.get("expense_to_income", 0), 4),
              "disposable_income": round(e.get("disposable_income", 0), 2),
              "savings_months": round(e.get("savings_months", 0), 2),
              "credit_band": e.get("credit_band", ""),
              "classification_model": result["models"]["classifier"],
              "regression_model": result["models"]["regressor"],
              "assessed_at": result["timestamp"]}
    c2.download_button("Download Record (CSV)",
                       pd.DataFrame([record]).to_csv(index=False).encode("utf-8"),
                       file_name=f"emipredict_record_{stamp}.csv", mime="text/csv",
                       use_container_width=True)

    if pdf_error:
        st.warning(pdf_error)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ---------------- on-screen report ----------------
    st.markdown('<div class="card-title">Financial Assessment Report</div>',
                unsafe_allow_html=True)

    a, b = st.columns(2, gap="medium")
    with a:
        cards.panel("Customer profile", cards.data_rows([
            ("Age", f"{p['age']} years"),
            ("Gender", p["gender"]),
            ("Marital status", p["marital_status"]),
            ("Education", p["education"]),
            ("Employment", f"{p['employment_type']} · {p['company_type']}"),
            ("Work experience", f"{p['years_of_employment']:.1f} years"),
            ("Household", f"{p['family_size']} members · {p['dependents']} dependants"),
            ("Residence", p["house_type"]),
        ]))
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        cards.panel("Loan request", cards.data_rows([
            ("Lending product", p["emi_scenario"]),
            ("Requested amount", inr(p["requested_amount"])),
            ("Requested tenure", f"{p['requested_tenure']} months"),
            ("Assumed rate", f"{rate:.1f}% p.a."),
            ("Resulting instalment", inr(proposed)),
        ]))
    with b:
        cards.panel("Financial summary", cards.data_rows([
            ("Monthly income", inr(p["monthly_salary"])),
            ("Household expenses", inr(e.get("total_monthly_expenses", 0))),
            ("Existing EMI", inr(p["current_emi_amount"])),
            ("Disposable income", inr(e.get("disposable_income", 0))),
            ("Debt-to-income", pct(e.get("debt_to_income", 0))),
            ("Expense-to-income", pct(e.get("expense_to_income", 0))),
            ("Credit score", f"{int(p['credit_score'])} · {e.get('credit_band', '')}"),
            ("Bank balance", inr(p["bank_balance"])),
            ("Emergency fund", inr(p["emergency_fund"])),
            ("Liquidity buffer", f"{e.get('savings_months', 0):.1f} months"),
        ]))

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    positives, risks = services.derive_insights(result)
    c, d = st.columns(2, gap="medium")
    with c:
        cards.panel("Positive factors", cards.factor_list(positives, "pos"))
    with d:
        cards.panel("Risk factors", cards.factor_list(risks, "neg"))

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    cards.panel("Model information", cards.data_rows([
        ("Classification model", result["models"]["classifier"]),
        ("Regression model", result["models"]["regressor"]),
        ("Predicted class", result["label"].replace("_", " ")),
        ("Model confidence", pct(result["confidence"])),
        ("Assessment timestamp", result["timestamp"]),
    ]))

    st.caption("This assessment is decision support for a qualified underwriter. It does "
               "not by itself constitute a credit decision or an offer of finance.")
