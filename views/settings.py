"""Settings — application, model and system configuration state."""
from __future__ import annotations

import os
import platform
import sys

import streamlit as st

from components import cards, shell
from core import services
from utils.formatting import num


def render() -> None:
    shell.render_header("Settings", "Configuration")

    bundle = services.load_models()
    meta = bundle.get("meta", {})
    ml = services.mlflow_status()
    data = services.dataset_profile()

    tab_app, tab_model, tab_sys = st.tabs(["Application", "Models", "System"])

    with tab_app:
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            cards.panel("Appearance", cards.data_rows([
                ("Theme", "Dark (enterprise)"),
                ("Layout", "Wide"),
                ("Currency format", "INR — Indian digit grouping"),
                ("Stylesheet", "styles/theme.css"),
            ]))
            st.caption("The theme is defined in `.streamlit/config.toml` and "
                       "`styles/theme.css`.")
        with c2:
            st.markdown('<div class="card-title">Session</div>', unsafe_allow_html=True)
            has_assessment = "assessment" in st.session_state
            st.markdown(
                f"<div class='drow'><span class='k'>Active assessment</span>"
                f"<span class='v'>{'Yes' if has_assessment else 'None'}</span></div>",
                unsafe_allow_html=True)
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            if st.button("Clear session assessment", disabled=not has_assessment):
                st.session_state.pop("assessment", None)
                st.success("Session assessment cleared.")
            if st.button("Clear cached data"):
                st.cache_data.clear()
                st.success("Cached dataset and metric files cleared.")
            if st.button("Reload models"):
                # Clears @st.cache_resource so the pipelines are re-read from disk.
                # Useful after replacing artifacts without restarting the process.
                st.cache_resource.clear()
                st.cache_data.clear()
                st.success("Model cache cleared — reloading from disk.")
                st.rerun()

    with tab_model:
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            cards.panel("Active models", cards.data_rows([
                ("Classification model", meta.get("best_classifier", "—")),
                ("Regression model", meta.get("best_regressor", "—")),
                ("Eligibility classes",
                 " · ".join(c.replace("_", " ") for c in meta.get("class_names", []))
                 or "—"),
                ("Load status",
                 cards.badge("Loaded", "ok") if bundle["error"] is None
                 else cards.badge("Unavailable", "bad")),
            ]))
            if bundle["error"]:
                with st.expander("Model load error"):
                    st.code(bundle["error"])
        with c2:
            files = ["best_classifier.pkl", "best_regressor.pkl", "label_encoder.pkl",
                     "metadata.json", "clf_comparison.json", "reg_comparison.json",
                     "test_metrics.json"]
            rows = []
            for f in files:
                path = os.path.join(services.MODEL_DIR, f)
                ok = os.path.exists(path)
                size = f"{os.path.getsize(path)/1e6:.2f} MB" if ok else "missing"
                rows.append((f, size if ok else cards.badge("Missing", "bad")))
            cards.panel("Model artifacts", cards.data_rows(rows))

        st.caption("Models are produced by the training notebook. Retraining regenerates "
                   "every artifact listed above.")

    with tab_sys:
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            cards.panel("Data & tracking", cards.data_rows([
                ("Dataset file",
                 cards.badge("Available", "ok") if data["available"]
                 else cards.badge("Missing", "bad")),
                ("Records", num(data["rows"]) if data["rows"] else "—"),
                ("Dataset size", f"{data['size_mb']} MB" if data["size_mb"] else "—"),
                ("MLflow store",
                 cards.badge("Connected", "ok") if ml["available"]
                 else cards.badge("Unavailable", "mute")),
                ("Tracked runs", num(ml["total_runs"]) if ml["available"] else "—"),
                ("Registered models",
                 num(len(ml["registered"])) if ml["available"] else "—"),
            ]))
            if not ml["available"] and ml["reason"]:
                st.caption(ml["reason"])
        with c2:
            import pandas as pd
            import sklearn
            versions = [
                ("Application", services.app_version()),
                ("Python", platform.python_version()),
                ("Streamlit", st.__version__),
                ("pandas", pd.__version__),
                ("scikit-learn", sklearn.__version__),
            ]
            try:
                import xgboost
                versions.append(("XGBoost", xgboost.__version__))
            except ImportError:
                pass
            cards.panel("Environment", cards.data_rows(versions))
