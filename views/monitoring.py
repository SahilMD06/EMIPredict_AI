"""Model Monitoring — MLflow experiment tracking and model registry."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import cards, shell
from core import services
from utils.formatting import num

CLF_METRICS = ["accuracy", "precision_macro", "recall_macro", "f1_macro", "roc_auc_ovr"]
REG_METRICS = ["rmse", "mae", "r2", "mape"]


def render() -> None:
    shell.render_header("Model Monitoring", "MLflow")

    status = services.mlflow_status()

    if not status["available"]:
        cards.empty_state(
            "MLflow connection unavailable",
            status["reason"] or "The MLflow tracking store could not be read.")
        st.caption("The application reads the MLflow SQLite store directly, so no "
                   "tracking server needs to be running. If this deployment excludes "
                   "`mlflow.db`, experiment history is not available here.")
        return

    experiments = status["experiments"]
    registered = status["registered"]

    cards.kpi_row([
        {"label": "Experiments", "value": num(len(experiments)),
         "sub": "Tracked training experiments", "tone": "ok"},
        {"label": "Total Runs", "value": num(status["total_runs"]),
         "sub": "Logged with parameters and metrics"},
        {"label": "Registered Models", "value": num(len(registered)),
         "sub": "Versioned in the model registry", "tone": "ok"},
        {"label": "Production Aliases",
         "value": num(sum(len(m["aliases"]) for m in registered)),
         "sub": "Promoted model versions"},
    ])

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    tab_exp, tab_reg = st.tabs(["Experiment Runs", "Model Registry"])

    with tab_exp:
        for exp in experiments:
            st.markdown(f'<div class="card-title">{exp["name"]} · '
                        f'{len(exp["runs"])} runs</div>', unsafe_allow_html=True)
            if not exp["runs"]:
                st.info("This experiment has no active runs.")
                continue

            metric_keys = CLF_METRICS if "Classification" in exp["name"] else REG_METRICS
            rows = []
            for run in exp["runs"]:
                row = {"Run": run["name"], "Status": run["status"],
                       "Started": run["started"]}
                for k in metric_keys:
                    if k in run["metrics"]:
                        row[k] = run["metrics"][k]
                if "train_time_sec" in run["metrics"]:
                    row["train_time_sec"] = run["metrics"]["train_time_sec"]
                rows.append(row)

            table = pd.DataFrame(rows)
            numeric = [c for c in table.columns if c in metric_keys + ["train_time_sec"]]
            styler = table.style.format({c: "{:.4f}" for c in numeric}, na_rep="—")
            if "f1_macro" in numeric:
                styler = styler.highlight_max(subset=["f1_macro"],
                                              color="rgba(34,197,94,0.18)")
            elif "rmse" in numeric:
                styler = styler.highlight_min(subset=["rmse"],
                                              color="rgba(34,197,94,0.18)")
            st.dataframe(styler, use_container_width=True, hide_index=True)
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        st.caption("Run the MLflow interface with "
                   "`mlflow ui --backend-store-uri sqlite:///mlflow.db` for artifacts, "
                   "parameter detail and run comparison plots.")

    with tab_reg:
        if not registered:
            st.info("No models are currently registered.")
        for model in registered:
            alias_html = " ".join(
                cards.badge(f"@{a} → v{v}", "ok") for a, v in model["aliases"].items())
            latest = model["versions"][0] if model["versions"] else None
            rows = [
                ("Latest version", f"v{latest['version']}" if latest else "—"),
                ("Total versions", str(len(model["versions"]))),
                ("Source run", (latest["run_id"][:16] + "…") if latest else "—"),
                ("Aliases", alias_html or "None"),
            ]
            cards.panel(model["name"], cards.data_rows(rows))
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        st.caption("Registered versions carry the production alias used to promote a "
                   "specific run's model into serving.")
