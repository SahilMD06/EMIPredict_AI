"""Shared feature-engineering module for EMIPredict AI (used by notebook + Streamlit app)."""
import numpy as np
import pandas as pd

EXPENSE_COLS = ['monthly_rent','school_fees','college_fees','travel_expenses',
                'groceries_utilities','other_monthly_expenses']

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    sal = d['monthly_salary'].clip(lower=1)
    d['total_monthly_expenses'] = d[EXPENSE_COLS].sum(axis=1)
    d['debt_to_income']       = d['current_emi_amount'] / sal
    d['expense_to_income']    = d['total_monthly_expenses'] / sal
    d['disposable_income']    = d['monthly_salary'] - d['total_monthly_expenses'] - d['current_emi_amount']
    d['affordability_ratio']  = d['disposable_income'] / sal
    d['requested_emi_simple'] = d['requested_amount'] / d['requested_tenure'].clip(lower=1)
    d['requested_emi_to_income'] = d['requested_emi_simple'] / sal
    d['savings_months'] = (d['bank_balance'] + d['emergency_fund']) / (d['total_monthly_expenses'] + d['current_emi_amount']).clip(lower=1)
    d['credit_band'] = pd.cut(d['credit_score'], bins=[299,579,669,739,850],
                              labels=['Poor','Fair','Good','Excellent']).astype(str)
    d['employment_stability'] = d['years_of_employment'] * d['employment_type'].map(
        {'Government':1.2,'Private':1.0,'Self-employed':0.8}).fillna(1.0)
    d['salary_x_credit'] = d['monthly_salary'] * d['credit_score'] / 1e5
    d['dependents_burden'] = d['dependents'] / d['family_size'].clip(lower=1)
    return d

NUMERIC_FEATURES = ['age','monthly_salary','years_of_employment','monthly_rent','family_size',
    'dependents','school_fees','college_fees','travel_expenses','groceries_utilities',
    'other_monthly_expenses','current_emi_amount','credit_score','bank_balance','emergency_fund',
    'requested_amount','requested_tenure','total_monthly_expenses','debt_to_income',
    'expense_to_income','disposable_income','affordability_ratio','requested_emi_simple',
    'requested_emi_to_income','savings_months','employment_stability','salary_x_credit','dependents_burden']

CATEGORICAL_FEATURES = ['gender','marital_status','education','employment_type','company_type',
    'house_type','existing_loans','emi_scenario','credit_band']

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES