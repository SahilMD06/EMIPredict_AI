"""Analytics — portfolio-level financial analytics from the source dataset."""
from __future__ import annotations

import streamlit as st

from components import cards, charts, shell
from core import services
from utils.formatting import inr, num, pct


def render() -> None:
    shell.render_header("Analytics", "Portfolio Intelligence")

    df = services.load_sample()
    if df is None:
        cards.empty_state("Dataset Unavailable",
                          "The source dataset could not be found in the application "
                          "directory. Analytics require the dataset file to be present.")
        return

    scenarios = sorted(df["emi_scenario"].dropna().unique())
    c1, c2 = st.columns([2, 2], gap="medium")
    picked_scen = c1.multiselect("Lending product", scenarios, placeholder="All products")
    picked_elig = c2.multiselect("Eligibility", services.CLASS_ORDER,
                                 placeholder="All eligibility classes")

    view = df
    if picked_scen:
        view = view[view["emi_scenario"].isin(picked_scen)]
    if picked_elig:
        view = view[view["emi_eligibility"].isin(picked_elig)]

    if view.empty:
        st.info("No records match the selected filters.")
        return

    eligible_rate = (view["emi_eligibility"] == "Eligible").mean()
    cards.kpi_row([
        {"label": "Applications in view", "value": num(len(view)),
         "sub": f"of {num(len(df))} sampled records"},
        {"label": "Eligibility rate", "value": pct(eligible_rate),
         "sub": "Share classified as eligible",
         "tone": "ok" if eligible_rate > 0.2 else "warn"},
        {"label": "Median income", "value": inr(view["monthly_salary"].median()),
         "sub": "Monthly gross salary"},
        {"label": "Median safe EMI", "value": inr(view["max_monthly_emi"].median()),
         "sub": "Maximum affordable instalment"},
    ])

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    a, b = st.columns(2, gap="medium")
    with a:
        st.markdown('<div class="card-title">Eligibility distribution</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(charts.eligibility_distribution(view), use_container_width=True,
                        config={"displayModeBar": False})
        st.caption("The portfolio is dominated by ineligible applications, which is why "
                   "the models are evaluated on macro-averaged metrics rather than accuracy alone.")
    with b:
        st.markdown('<div class="card-title">Eligibility mix by lending product</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(charts.scenario_mix(view), use_container_width=True,
                        config={"displayModeBar": False})
        st.caption("Small-ticket products approve at materially higher rates than "
                   "vehicle and personal loans.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    c, d = st.columns(2, gap="medium")
    with c:
        st.markdown('<div class="card-title">Income against affordable instalment</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(charts.income_vs_emi(view), use_container_width=True,
                        config={"displayModeBar": False})
    with d:
        st.markdown('<div class="card-title">Credit score by eligibility class</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(charts.credit_score_box(view), use_container_width=True,
                        config={"displayModeBar": False})

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    e, f = st.columns([1.3, 1], gap="medium")
    with e:
        st.markdown('<div class="card-title">Household expenses against income</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(charts.expense_vs_income(view), use_container_width=True,
                        config={"displayModeBar": False})
    with f:
        rows = []
        for scen in sorted(view["emi_scenario"].dropna().unique()):
            sub = view[view["emi_scenario"] == scen]
            rate = (sub["emi_eligibility"] == "Eligible").mean()
            rows.append((scen.replace(" EMI", ""), pct(rate)))
        cards.panel("Eligibility rate by product", cards.data_rows(rows))

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        summary = [
            ("Median credit score", f"{view['credit_score'].median():.0f}"),
            ("Median requested amount", inr(view["requested_amount"].median())),
            ("Median tenure", f"{view['requested_tenure'].median():.0f} months"),
            ("Median bank balance", inr(view["bank_balance"].median())),
        ]
        cards.panel("Portfolio medians", cards.data_rows(summary))
