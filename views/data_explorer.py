"""Data Explorer — efficient exploration of the source dataset."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import cards, shell
from core import services
from utils.formatting import inr, num

PAGE_SIZE = 50


def render() -> None:
    shell.render_header("Data Explorer", "Dataset")

    profile = services.dataset_profile()
    if not profile["available"]:
        cards.empty_state("Dataset Unavailable",
                          "The source dataset could not be found in the application directory.")
        return

    cards.kpi_row([
        {"label": "Total Records", "value": num(profile["rows"]),
         "sub": f"{profile['size_mb']} MB source file"},
        {"label": "Input Features", "value": num(profile["features"]),
         "sub": "Demographic, financial and request variables"},
        {"label": "EMI Scenarios", "value": num(profile["scenarios"]),
         "sub": "Lending products covered"},
        {"label": "Target Variables", "value": "2",
         "sub": "Eligibility class · maximum safe EMI"},
    ])

    st.caption("A bounded sample is loaded into the session for interactive exploration; "
               "the full file is never rendered in the browser.")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    df = services.load_sample()
    if df is None:
        st.error("The dataset could not be read.")
        return

    tab_browse, tab_stats, tab_schema = st.tabs(
        ["Record Browser", "Summary Statistics", "Schema"])

    # ---------------- browser ----------------
    with tab_browse:
        c1, c2, c3 = st.columns([2, 2, 1.4], gap="medium")
        scen = c1.multiselect("Lending product",
                              sorted(df["emi_scenario"].dropna().unique()),
                              placeholder="All products")
        elig = c2.multiselect("Eligibility", services.CLASS_ORDER,
                              placeholder="All classes")
        sort_col = c3.selectbox("Sort by", ["monthly_salary", "credit_score",
                                            "requested_amount", "max_monthly_emi", "age"])

        c4, c5 = st.columns([2, 2], gap="medium")
        sal_min, sal_max = int(df["monthly_salary"].min()), int(df["monthly_salary"].max())
        sal_range = c4.slider("Monthly income range (₹)", sal_min, sal_max,
                              (sal_min, sal_max), step=1000)
        cs_range = c5.slider("Credit score range", 300, 850, (300, 850))

        view = df.copy()
        if scen:
            view = view[view["emi_scenario"].isin(scen)]
        if elig:
            view = view[view["emi_eligibility"].isin(elig)]
        view = view[(view["monthly_salary"].between(*sal_range))]
        view = view[view["credit_score"].between(*cs_range) | view["credit_score"].isna()]
        view = view.sort_values(sort_col, ascending=False)

        total = len(view)
        pages = max((total - 1) // PAGE_SIZE + 1, 1)
        st.markdown(
            f"<div style='color:#8A97AD;font-size:0.85rem;margin:10px 0;'>"
            f"{num(total)} matching records · {pages} pages</div>",
            unsafe_allow_html=True)

        page = st.number_input("Page", 1, pages, 1, key="explorer_page",
                               label_visibility="collapsed")
        start = (int(page) - 1) * PAGE_SIZE
        st.dataframe(view.iloc[start:start + PAGE_SIZE], use_container_width=True,
                     height=460, hide_index=True)

        st.download_button(
            "Download filtered selection (CSV)",
            view.head(5000).to_csv(index=False).encode("utf-8"),
            file_name="emipredict_selection.csv", mime="text/csv")

    # ---------------- statistics ----------------
    with tab_stats:
        num_cols = df.select_dtypes("number").columns.tolist()
        picked = st.multiselect(
            "Variables", num_cols,
            default=[c for c in ["monthly_salary", "credit_score", "current_emi_amount",
                                 "requested_amount", "max_monthly_emi"] if c in num_cols])
        if picked:
            desc = df[picked].describe().T
            desc = desc.rename(columns={"25%": "Q1", "50%": "Median", "75%": "Q3"})
            st.dataframe(desc.style.format("{:,.2f}"), use_container_width=True)
        else:
            st.info("Select one or more variables to view summary statistics.")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            counts = df["emi_eligibility"].value_counts()
            rows = [(k.replace("_", " "), f"{v:,} ({v/len(df):.1%})") for k, v in counts.items()]
            cards.panel("Eligibility class balance", cards.data_rows(rows))
        with c2:
            counts = df["emi_scenario"].value_counts()
            rows = [(k.replace(" EMI", ""), f"{v:,}") for k, v in counts.items()]
            cards.panel("Records per lending product", cards.data_rows(rows))

    # ---------------- schema ----------------
    with tab_schema:
        schema = pd.DataFrame({
            "Column": df.columns,
            "Type": [str(t) for t in df.dtypes],
            "Non-null": [int(df[c].notna().sum()) for c in df.columns],
            "Unique": [int(df[c].nunique()) for c in df.columns],
            "Example": [str(df[c].dropna().iloc[0])[:28] if df[c].notna().any() else "—"
                        for c in df.columns],
        })
        st.dataframe(schema, use_container_width=True, height=560, hide_index=True)
