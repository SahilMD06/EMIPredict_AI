"""Input validation for the assessment form.

Rules mirror the documented dataset ranges and the cleaning rules applied in the
notebook (Section 2). Nothing here invents business policy — the checks only
confirm that the profile is inside the range the models were trained on.
"""
from __future__ import annotations

# Documented dataset ranges (project specification + notebook Section 2)
RANGES = {
    "age": (21, 65),
    "monthly_salary": (10_000, 500_000),
    "credit_score": (300, 850),
    "requested_amount": (10_000, 1_500_000),
    "requested_tenure": (3, 84),
    "years_of_employment": (0.0, 40.0),
}


def validate_profile(p: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings).

    errors   -> block the assessment (outside the model's supported range)
    warnings -> allow it, but flag an unusual profile to the user
    """
    errors: list[str] = []
    warnings: list[str] = []

    for field, (lo, hi) in RANGES.items():
        v = p.get(field)
        if v is None:
            errors.append(f"{field.replace('_', ' ').title()} is required.")
        elif not (lo <= v <= hi):
            label = field.replace("_", " ").title()
            errors.append(f"{label} must be between {lo:,} and {hi:,}.")

    salary = p.get("monthly_salary") or 0
    expenses = sum(p.get(k, 0) for k in (
        "monthly_rent", "school_fees", "college_fees", "travel_expenses",
        "groceries_utilities", "other_monthly_expenses"))
    current_emi = p.get("current_emi_amount", 0)

    if salary > 0:
        if expenses + current_emi >= salary:
            warnings.append(
                "Declared monthly expenses and existing EMI meet or exceed monthly income. "
                "The profile has no disposable income, which strongly affects the assessment.")
        elif (expenses + current_emi) / salary > 0.75:
            warnings.append(
                "Monthly obligations exceed 75% of income, leaving limited repayment capacity.")

    if p.get("existing_loans") == "No" and current_emi > 0:
        errors.append(
            "Current EMI amount must be zero when the applicant reports no existing loans.")

    if p.get("existing_loans") == "Yes" and current_emi <= 0:
        warnings.append(
            "Existing loans are reported but the current EMI amount is zero. "
            "Confirm the applicant's outstanding obligations.")

    if p.get("house_type") == "Own" and p.get("monthly_rent", 0) > 0:
        warnings.append(
            "Monthly rent is recorded for an owned residence. This was treated as zero "
            "during model training and may distort the assessment.")

    tenure = p.get("requested_tenure") or 1
    requested_emi = (p.get("requested_amount") or 0) / max(tenure, 1)
    if salary > 0 and requested_emi / salary > 1.0:
        warnings.append(
            "The requested financial obligation appears high relative to the provided income.")

    return errors, warnings
