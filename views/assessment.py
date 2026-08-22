"""EMI Assessment — the primary underwriting workflow.

One grouped profile form drives both production models; results are held in
session state so the Reports page can render them without re-predicting.
"""
from __future__ import annotations

import time

import streamlit as st

from components import cards, charts, forms, shell
from core import services
from utils.formatting import inr, pct
from utils.validation import validate_profile

VERDICT_TEXT = {
    "Eligible": ("ELIGIBLE",
                 "Low risk. The applicant's income, obligations and credit profile "
                 "support the requested facility at standard pricing."),
    "High_Risk": ("HIGH RISK",
                  "Marginal case. Approval is possible with risk-based pricing, a "
                  "longer tenure or a reduced principal."),
    "Not_Eligible": ("NOT ELIGIBLE",
                     "High risk. The requested facility is not recommended on the "
                     "applicant's current financial profile."),
}


def render() -> None:
    shell.render_header("EMI Assessment", "Underwriting")

    bundle = services.load_models()
    if bundle["error"]:
        st.error("Assessment models are unavailable.")
        with st.expander("Technical details"):
            st.code(bundle["error"])
        st.info("Run the training notebook to regenerate the files in `models/`.")
        return

    left, right = st.columns([1.05, 1], gap="large")

    with left:
        st.markdown('<div class="card-title">Customer Financial Profile</div>',
                    unsafe_allow_html=True)
        forms.preset_selector()
        profile, submitted, rate = forms.profile_form()

    if submitted:
        errors, warnings = validate_profile(profile)
        if errors:
            st.session_state.pop("assessment", None)
            with right:
                st.markdown('<div class="card-title">Assessment</div>', unsafe_allow_html=True)
                for e in errors:
                    st.error(e)
            return

        status = right.status("Analysing financial profile...", expanded=False)
        try:
            status.update(label="Generating EMI affordability assessment...")
            result = services.run_assessment(profile)
            result["interest_rate"] = rate
            result["warnings"] = warnings
            st.session_state["assessment"] = result
            status.update(label="Assessment complete.", state="complete")
        except Exception as exc:                   # noqa: BLE001
            status.update(label="Assessment failed.", state="error")
            with right:
                st.error("Unable to complete the assessment. Please verify the inputs "
                         "and try again.")
                with st.expander("Technical details"):
                    st.code(str(exc))
            return

    with right:
        result = st.session_state.get("assessment")
        if not result:
            st.markdown('<div class="card-title">Assessment</div>', unsafe_allow_html=True)
            cards.empty_state(
                "No Assessment Yet",
                "Complete the customer's financial profile and select "
                "“Assess Financial Risk” to generate an AI-powered "
                "eligibility decision and affordability estimate.")
            return
        _render_result(result)

    result = st.session_state.get("assessment")
    if result:
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
        _render_analysis(result)


def _render_result(result: dict) -> None:
    label = result["label"]
    headline, note = VERDICT_TEXT.get(label, (label, ""))
    conf = result["confidence"]

    right_html = (f'<div class="verdict-label">Model confidence</div>'
                  f'<div style="font-size:1.55rem;font-weight:650;">{conf:.1%}</div>')
    cards.verdict(label, headline, note, right_html)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    p = result["profile"]
    max_emi = result["max_monthly_emi"]
    proposed = services.amortized_emi(p["requested_amount"],
                                      result.get("interest_rate", 12.0),
                                      p["requested_tenure"])

    cards.kpi_row([
        {"label": "Maximum Safe EMI", "value": inr(max_emi),
         "sub": "Model-estimated monthly capacity", "tone": "ok"},
        {"label": "Requested EMI", "value": inr(proposed),
         "sub": f"{p['requested_tenure']} months at "
                f"{result.get('interest_rate', 12.0):.1f}% p.a.",
         "tone": "ok" if proposed <= max_emi * 0.8 else
                 ("warn" if proposed <= max_emi else "bad")},
    ])

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    for w in result.get("warnings", []):
        st.warning(w)

    headroom = max_emi - proposed
    if proposed <= max_emi * 0.8:
        st.success(f"The requested instalment sits within safe capacity, leaving "
                   f"{inr(headroom)} of monthly headroom.")
    elif proposed <= max_emi:
        st.warning(f"The requested instalment approaches the safe ceiling — only "
                   f"{inr(headroom)} of headroom remains. Consider a longer tenure.")
    else:
        affordable = services.affordable_principal(
            max_emi, result.get("interest_rate", 12.0), p["requested_tenure"])
        st.error(f"The requested instalment exceeds assessed capacity by "
                 f"{inr(abs(headroom))}. At {result.get('interest_rate', 12.0):.1f}% over "
                 f"{p['requested_tenure']} months, the supportable principal is "
                 f"approximately {inr(affordable)}.")


def _render_analysis(result: dict) -> None:
    p = result["profile"]
    e = result["engineered"]
    max_emi = result["max_monthly_emi"]
    proposed = services.amortized_emi(p["requested_amount"],
                                      result.get("interest_rate", 12.0),
                                      p["requested_tenure"])

    tabs = st.tabs(["Risk Analysis", "Financial Profile", "Assessment Insights",
                    "Model Detail"])

    with tabs[0]:
        c1, c2, c3 = st.columns([1, 1, 1.15], gap="medium")
        with c1:
            cards.panel("Risk indicator", cards.risk_meter(result["label"]))
        with c2:
            st.markdown('<div class="card-title">Class probabilities</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(charts.probability_bars(result["probabilities"]),
                            use_container_width=True, config={"displayModeBar": False})
        with c3:
            st.markdown('<div class="card-title">Capacity utilisation</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(charts.capacity_gauge(proposed, max_emi),
                            use_container_width=True, config={"displayModeBar": False})
            st.caption("Requested instalment as a share of the model's safe-capacity "
                       "estimate. Beyond 100% the obligation exceeds assessed capacity.")

    with tabs[1]:
        c1, c2 = st.columns([1, 1.1], gap="medium")
        with c1:
            rows = [
                ("Monthly income", inr(p["monthly_salary"])),
                ("Household expenses", inr(e.get("total_monthly_expenses", 0))),
                ("Existing EMI", inr(p["current_emi_amount"])),
                ("Disposable income", inr(e.get("disposable_income", 0))),
                ("Debt-to-income", pct(e.get("debt_to_income", 0))),
                ("Expense-to-income", pct(e.get("expense_to_income", 0))),
                ("Credit score", f"{int(p['credit_score'])} · {e.get('credit_band', '')}"),
                ("Liquidity buffer", f"{e.get('savings_months', 0):.1f} months"),
                ("Bank balance", inr(p["bank_balance"])),
                ("Emergency fund", inr(p["emergency_fund"])),
            ]
            cards.panel("Financial indicators", cards.data_rows(rows))
        with c2:
            st.markdown('<div class="card-title">Monthly financial allocation</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(
                charts.allocation_donut(
                    p["monthly_salary"], p["current_emi_amount"],
                    e.get("total_monthly_expenses", 0), min(proposed, max_emi)),
                use_container_width=True, config={"displayModeBar": False})
            st.caption("Allocation of monthly income including the proposed instalment, "
                       "capped at the assessed safe capacity.")

    with tabs[2]:
        positives, risks = services.derive_insights(result)
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            cards.panel("Positive factors", cards.factor_list(positives, "pos"))
        with c2:
            cards.panel("Risk factors", cards.factor_list(risks, "neg"))
        st.caption("Factors are derived from the engineered features the models "
                   "consumed for this profile. They describe the applicant's position "
                   "on each feature, not the model's internal decision path.")

    with tabs[3]:
        c1, c2 = st.columns([1, 1.3], gap="medium")
        with c1:
            rows = [
                ("Classification model", result["models"]["classifier"]),
                ("Regression model", result["models"]["regressor"]),
                ("Predicted class", result["label"].replace("_", " ")),
                ("Confidence", pct(result["confidence"])),
                ("Maximum safe EMI", inr(max_emi)),
                ("Assessed at", result["timestamp"]),
            ]
            cards.panel("Assessment metadata", cards.data_rows(rows))
        with c2:
            imp = services.feature_importance("classifier", 10)
            if imp is not None:
                st.markdown('<div class="card-title">Top features — eligibility model</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(charts.importance_bars(imp), use_container_width=True,
                                config={"displayModeBar": False})
                st.caption("Global feature importance from the fitted production "
                           "pipeline, not a per-applicant attribution.")
            else:
                cards.panel("Feature importance",
                            '<div style="color:#64728C;font-size:0.87rem;">'
                            'Feature importance is unavailable for the active model type.'
                            '</div>')

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 3], gap="small")
    if c1.button("Generate Report", type="primary", use_container_width=True):
        shell.goto("Reports")
    if c2.button("Clear Assessment", use_container_width=True):
        st.session_state.pop("assessment", None)
        st.rerun()
