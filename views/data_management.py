"""Data Management — administrative CRUD over the application record store."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import cards, shell
from core import services
from core.services import SCENARIOS
from utils.formatting import num


def _read(con, limit=200) -> pd.DataFrame:
    return pd.read_sql(f"SELECT rowid AS record_id, * FROM records LIMIT {limit}", con)


def render() -> None:
    shell.render_header("Data Management", "Administration")

    try:
        con = services.get_app_db()
    except Exception as exc:                       # noqa: BLE001
        st.error("The record store could not be opened.")
        with st.expander("Technical details"):
            st.code(str(exc))
        return

    total = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    columns = [r[1] for r in con.execute("PRAGMA table_info(records)")]

    cards.kpi_row([
        {"label": "Stored Records", "value": num(total), "sub": "Application record store"},
        {"label": "Columns", "value": num(len(columns)), "sub": "Fields per record"},
        {"label": "Storage", "value": "SQLite", "sub": services.APP_DB},
        {"label": "Operations", "value": "CRUD", "sub": "Create · read · update · delete"},
    ])

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    tab_r, tab_c, tab_u, tab_d = st.tabs(
        ["Browse Records", "Add Record", "Update Record", "Delete Record"])

    # ---------------- read ----------------
    with tab_r:
        c1, c2 = st.columns([1, 3], gap="medium")
        limit = c1.slider("Rows to display", 10, 500, 100, 10)
        search = c2.text_input("Search", placeholder="Filter across all columns…")

        df = _read(con, limit)
        if search:
            mask = df.astype(str).apply(
                lambda col: col.str.contains(search, case=False, na=False))
            df = df[mask.any(axis=1)]
        st.markdown(f"<div style='color:#8A97AD;font-size:0.85rem;margin:8px 0;'>"
                    f"{num(len(df))} records displayed</div>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, height=430, hide_index=True)

    # ---------------- create ----------------
    with tab_c:
        with st.form("create_record"):
            c1, c2, c3 = st.columns(3, gap="medium")
            age = c1.number_input("Age", 21, 65, 32)
            salary = c2.number_input("Monthly salary (₹)", 10_000, 500_000, 60_000, 1_000)
            score = c3.number_input("Credit score", 300, 850, 720)
            scenario = c1.selectbox("Lending product", SCENARIOS)
            amount = c2.number_input("Requested amount (₹)", 10_000, 1_500_000,
                                     250_000, 5_000)
            tenure = c3.number_input("Tenure (months)", 3, 84, 36)
            if st.form_submit_button("Create Record", type="primary"):
                fields = {"age": age, "monthly_salary": salary, "credit_score": score,
                          "emi_scenario": scenario, "requested_amount": amount,
                          "requested_tenure": tenure}
                usable = {k: v for k, v in fields.items() if k in columns}
                if not usable:
                    st.error("The record store has no matching columns.")
                else:
                    cols = ", ".join(usable)
                    marks = ", ".join("?" * len(usable))
                    con.execute(f"INSERT INTO records ({cols}) VALUES ({marks})",
                                tuple(usable.values()))
                    con.commit()
                    st.success("Record created.")
                    st.rerun()

    # ---------------- update ----------------
    with tab_u:
        df = _read(con, 500)
        if df.empty:
            st.info("There are no records to update.")
        else:
            c1, c2, c3 = st.columns([1, 1.2, 1.4], gap="medium")
            rid = c1.selectbox("Record ID", df["record_id"].tolist())
            editable = [c for c in columns]
            col = c2.selectbox("Field", editable)
            current = df.loc[df["record_id"] == rid, col].iloc[0]
            new_value = c3.text_input("New value", value=str(current))

            st.markdown(f"<div style='color:#8A97AD;font-size:0.86rem;margin:8px 0;'>"
                        f"Record {rid} · <code>{col}</code> is currently "
                        f"<b>{current}</b></div>", unsafe_allow_html=True)

            confirm = st.checkbox("Confirm this update", key="confirm_update")
            if st.button("Apply Update", type="primary", disabled=not confirm):
                try:
                    typed = pd.to_numeric(new_value) if str(current).replace(
                        ".", "", 1).replace("-", "", 1).isdigit() else new_value
                    con.execute(f"UPDATE records SET {col}=? WHERE rowid=?", (typed, rid))
                    con.commit()
                    st.success(f"Record {rid} updated — {col} set to {new_value}.")
                    st.rerun()
                except Exception as exc:           # noqa: BLE001
                    st.error("The record could not be updated.")
                    with st.expander("Technical details"):
                        st.code(str(exc))

    # ---------------- delete ----------------
    with tab_d:
        df = _read(con, 500)
        if df.empty:
            st.info("There are no records to delete.")
        else:
            rid = st.selectbox("Record to delete", df["record_id"].tolist(),
                               key="delete_target")
            st.dataframe(df[df["record_id"] == rid], use_container_width=True,
                         hide_index=True)
            st.warning("Deletion is permanent and cannot be undone.")
            confirm = st.checkbox(f"I confirm the deletion of record {rid}",
                                  key="confirm_delete")
            if st.button("Delete Record", disabled=not confirm):
                con.execute("DELETE FROM records WHERE rowid=?", (rid,))
                con.commit()
                st.success(f"Record {rid} deleted.")
                st.rerun()
