"""Applicant financial profile form — the 22 documented input variables,
grouped into six logical sections.

The form is wrapped in st.form so that editing fields does not trigger a rerun
or a recomputation; the profile is only submitted once, on the CTA click.
"""
from __future__ import annotations

import streamlit as st

from components.cards import section
from core.services import SCENARIOS

EDUCATION = ["High School", "Graduate", "Post Graduate", "Professional"]
EMPLOYMENT = ["Private", "Government", "Self-employed"]
COMPANY = ["MNC", "Large Indian", "Mid-size", "Small", "Startup"]
HOUSE = ["Rented", "Own", "Family"]

PRESETS = {
    "Balanced profile": {},
    "Strong applicant": dict(
        monthly_salary=140_000, credit_score=790, years_of_employment=12.0,
        employment_type="Government", company_type="MNC", house_type="Own",
        monthly_rent=0, existing_loans="No", current_emi_amount=0,
        bank_balance=850_000, emergency_fund=400_000, dependents=1, family_size=3,
        requested_amount=400_000, requested_tenure=48),
    "Marginal applicant": dict(
        monthly_salary=32_000, credit_score=610, years_of_employment=2.0,
        employment_type="Self-employed", company_type="Small", house_type="Rented",
        monthly_rent=12_000, existing_loans="Yes", current_emi_amount=9_000,
        bank_balance=25_000, emergency_fund=8_000, dependents=3, family_size=5,
        requested_amount=600_000, requested_tenure=36),
}

DEFAULTS = dict(
    age=35, gender="Male", marital_status="Married", education="Graduate",
    monthly_salary=75_000, employment_type="Private", years_of_employment=6.0,
    company_type="Mid-size", house_type="Rented", monthly_rent=15_000,
    family_size=3, dependents=1, school_fees=4_000, college_fees=0,
    travel_expenses=5_000, groceries_utilities=13_000, other_monthly_expenses=6_000,
    existing_loans="No", current_emi_amount=0, credit_score=720,
    bank_balance=250_000, emergency_fund=100_000,
    emi_scenario="Vehicle EMI", requested_amount=350_000, requested_tenure=48,
)


def _d(key):
    """Current default for a field: preset override, else base default."""
    preset = PRESETS.get(st.session_state.get("profile_preset", "Balanced profile"), {})
    return preset.get(key, DEFAULTS[key])


def preset_selector() -> None:
    """Optional starting point for demonstrations. Does not alter model behaviour."""
    st.selectbox(
        "Starting profile", list(PRESETS.keys()), key="profile_preset",
        help="Pre-fills the form with a representative profile. Every field remains editable.")


def profile_form() -> tuple[dict, bool]:
    """Render the grouped form. Returns (profile, submitted)."""
    with st.form("assessment_form", border=False):
        section("Section A · Personal Information")
        c1, c2 = st.columns(2, gap="medium")
        age = c1.slider("Age", 21, 65, _d("age"),
                        help="Applicant age in years. Supported range: 21–65.")
        gender = c2.selectbox("Gender", ["Male", "Female"],
                              index=["Male", "Female"].index(_d("gender")))
        marital_status = c1.selectbox("Marital status", ["Single", "Married"],
                                      index=["Single", "Married"].index(_d("marital_status")))
        education = c2.selectbox("Education", EDUCATION,
                                 index=EDUCATION.index(_d("education")),
                                 help="Highest completed qualification.")

        section("Section B · Employment & Income")
        c1, c2 = st.columns(2, gap="medium")
        monthly_salary = c1.number_input(
            "Monthly salary (₹)", 10_000, 500_000, _d("monthly_salary"), 1_000,
            help="Gross monthly income before deductions.")
        employment_type = c2.selectbox("Employment type", EMPLOYMENT,
                                       index=EMPLOYMENT.index(_d("employment_type")),
                                       help="Employment category — affects the employment "
                                            "stability feature used by the models.")
        years_of_employment = c1.number_input(
            "Years of employment", 0.0, 40.0, float(_d("years_of_employment")), 0.5,
            help="Total work experience in years.")
        company_type = c2.selectbox("Company type", COMPANY,
                                    index=COMPANY.index(_d("company_type")),
                                    help="Size and type of the employing organisation.")

        section("Section C · Housing & Family")
        c1, c2 = st.columns(2, gap="medium")
        house_type = c1.selectbox("Residence type", HOUSE,
                                  index=HOUSE.index(_d("house_type")))
        monthly_rent = c2.number_input(
            "Monthly rent (₹)", 0, 100_000, _d("monthly_rent"), 500,
            help="Enter 0 for an owned or family residence.")
        family_size = c1.slider("Family size", 1, 10, _d("family_size"),
                                help="Total household members.")
        dependents = c2.slider("Dependants", 0, 6, _d("dependents"),
                               help="Household members financially dependent on the applicant.")

        section("Section D · Monthly Expenses")
        c1, c2 = st.columns(2, gap="medium")
        school_fees = c1.number_input("School fees (₹/month)", 0, 50_000,
                                      _d("school_fees"), 500)
        college_fees = c2.number_input("College fees (₹/month)", 0, 60_000,
                                       _d("college_fees"), 500)
        travel_expenses = c1.number_input("Travel expenses (₹/month)", 0, 50_000,
                                          _d("travel_expenses"), 500,
                                          help="Commuting and transport costs.")
        groceries_utilities = c2.number_input("Groceries & utilities (₹/month)", 0, 100_000,
                                              _d("groceries_utilities"), 500,
                                              help="Essential living expenses.")
        other_monthly_expenses = c1.number_input("Other expenses (₹/month)", 0, 60_000,
                                                 _d("other_monthly_expenses"), 500,
                                                 help="Insurance, subscriptions and "
                                                      "miscellaneous obligations.")

        section("Section E · Existing Financial Obligations")
        c1, c2 = st.columns(2, gap="medium")
        existing_loans = c1.selectbox("Existing loans", ["No", "Yes"],
                                      index=["No", "Yes"].index(_d("existing_loans")))
        current_emi_amount = c2.number_input(
            "Current EMI amount (₹/month)", 0, 100_000, _d("current_emi_amount"), 500,
            help="Total monthly instalments already being serviced. "
                 "Must be 0 when no existing loans are reported.")
        credit_score = c1.slider("Credit score", 300, 850, _d("credit_score"),
                                 help="Creditworthiness score used in the financial "
                                      "risk assessment. Supported range: 300–850.")
        bank_balance = c2.number_input("Bank balance (₹)", 0, 5_000_000,
                                       _d("bank_balance"), 5_000,
                                       help="Current account balance.")
        emergency_fund = c1.number_input("Emergency fund (₹)", 0, 3_000_000,
                                         _d("emergency_fund"), 5_000,
                                         help="Liquid savings held for contingencies.")

        section("Section F · Loan Request")
        c1, c2 = st.columns(2, gap="medium")
        emi_scenario = c1.selectbox("EMI scenario", SCENARIOS,
                                    index=SCENARIOS.index(_d("emi_scenario")),
                                    help="Lending product the application relates to.")
        requested_amount = c2.number_input(
            "Requested amount (₹)", 10_000, 1_500_000, _d("requested_amount"), 5_000,
            help="Principal requested by the applicant.")
        requested_tenure = c1.slider("Requested tenure (months)", 3, 84,
                                     _d("requested_tenure"),
                                     help="Preferred repayment period.")
        interest_rate = c2.slider(
            "Assumed interest rate (% p.a.)", 8.0, 24.0, 12.0, 0.5,
            help="Used only to express the requested loan as a monthly instalment "
                 "for comparison. It is not a model input.")

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Assess Financial Risk", type="primary",
                                          use_container_width=True)

    profile = dict(
        age=age, gender=gender, marital_status=marital_status, education=education,
        monthly_salary=monthly_salary, employment_type=employment_type,
        years_of_employment=years_of_employment, company_type=company_type,
        house_type=house_type, monthly_rent=monthly_rent, family_size=family_size,
        dependents=dependents, school_fees=school_fees, college_fees=college_fees,
        travel_expenses=travel_expenses, groceries_utilities=groceries_utilities,
        other_monthly_expenses=other_monthly_expenses, existing_loans=existing_loans,
        current_emi_amount=current_emi_amount, credit_score=credit_score,
        bank_balance=bank_balance, emergency_fund=emergency_fund,
        emi_scenario=emi_scenario, requested_amount=requested_amount,
        requested_tenure=requested_tenure,
    )
    return profile, submitted, interest_rate
