"""Application shell — stylesheet loading, sidebar navigation and page header."""
from __future__ import annotations

import os

import streamlit as st

from core import services

CSS_PATH = os.path.join("styles", "theme.css")

LOGO_SVG = """
<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 17.5L8.5 11.5L12.5 15L21 5.5" stroke="white" stroke-width="2.1"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M15.5 5.5H21V11" stroke="white" stroke-width="2.1"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

NAV = [
    ("Overview", "Executive dashboard"),
    ("EMI Assessment", "Run a financial risk assessment"),
    ("Analytics", "Portfolio analytics"),
    ("Data Explorer", "Dataset exploration"),
    ("Model Performance", "Model evaluation results"),
    ("Model Monitoring", "MLflow experiments and registry"),
    ("Reports", "Assessment reporting"),
    ("Data Management", "Record administration"),
    ("Settings", "Application configuration"),
]


def load_styles() -> None:
    """Inject the centralized stylesheet once per session run."""
    try:
        with open(CSS_PATH, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Stylesheet not found — the application is running unstyled.")


def render_sidebar() -> str:
    """Brand, navigation and system footer. Returns the selected page name."""
    with st.sidebar:
        st.markdown(
            f"""<div class="brand">
                    <div class="brand-mark">{LOGO_SVG}</div>
                    <div>
                        <div class="brand-name">EMIPredict AI</div>
                        <div class="brand-sub">Financial Risk Intelligence</div>
                    </div>
                </div>""",
            unsafe_allow_html=True)

        st.markdown('<div class="nav-label">Navigation</div>', unsafe_allow_html=True)
        labels = [n[0] for n in NAV]
        default = labels.index(st.session_state.get("nav_page", "Overview"))
        page = st.radio("Navigation", labels, index=default,
                        label_visibility="collapsed", key="nav_radio")
        st.session_state["nav_page"] = page

        bundle = services.load_models()
        meta = bundle.get("meta", {})
        clf_name = meta.get("best_classifier", "—")
        reg_name = meta.get("best_regressor", "—")
        st.markdown(
            f"""<div class="sidebar-foot">
                    <div style="color:#8A97AD;font-weight:600;">EMIPredict AI</div>
                    ML-powered financial assessment<br>
                    <span style="color:#4E5B75;">Classifier:</span> {clf_name}<br>
                    <span style="color:#4E5B75;">Regressor:</span> {reg_name}
                </div>""",
            unsafe_allow_html=True)
    return page


def _chip(label: str, state: str) -> str:
    dot = {"ok": "dot-ok", "warn": "dot-warn", "off": "dot-off"}.get(state, "dot-off")
    return f'<span class="status-chip"><span class="dot {dot}"></span>{label}</span>'


def render_header(title: str, crumb: str = "EMIPredict AI") -> None:
    """Page header with genuine system status derived from application state."""
    bundle = services.load_models()
    models_ok = bundle["error"] is None
    ml = services.mlflow_status()
    data_ok = os.path.exists(services.DATA_PATH)

    chips = [
        _chip("Model Online" if models_ok else "Model Unavailable", "ok" if models_ok else "off"),
        _chip(f"MLflow · {ml['total_runs']} runs" if ml["available"] else "MLflow Unavailable",
              "ok" if ml["available"] else "off"),
        _chip("Dataset Loaded" if data_ok else "Dataset Unavailable", "ok" if data_ok else "warn"),
    ]

    st.markdown(
        f"""<div class="page-head">
                <div>
                    <div class="crumb">{crumb}</div>
                    <h1>{title}</h1>
                </div>
                <div class="status-row">{''.join(chips)}</div>
            </div>""",
        unsafe_allow_html=True)


def goto(page: str) -> None:
    """Programmatic navigation used by call-to-action buttons."""
    st.session_state["nav_page"] = page
    if "nav_radio" in st.session_state:
        st.session_state["nav_radio"] = page
    st.rerun()
