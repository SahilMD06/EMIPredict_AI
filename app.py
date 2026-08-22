"""EMIPredict AI — Intelligent Financial Risk Assessment Platform.

Streamlit entry point. This module is a thin shell: it configures the page,
loads the stylesheet, renders navigation and routes to a view module.

Layout
    app.py              application shell and router
    core/               model, data, MLflow and reporting services
    components/         reusable UI building blocks
    views/              one module per page
    utils/              formatting and validation helpers
    styles/theme.css    centralized design system

The prediction path (engineer_features -> ALL_FEATURES -> fitted pipeline) is
unchanged from the original application; see core/services.run_assessment.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="EMIPredict AI — Financial Risk Intelligence",
    page_icon="assets/favicon.png" if False else ":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components import shell                       # noqa: E402
from views import (analytics, assessment, data_explorer, data_management,  # noqa: E402
                   model_performance, monitoring, overview, reports, settings)

ROUTES = {
    "Overview": overview.render,
    "EMI Assessment": assessment.render,
    "Analytics": analytics.render,
    "Data Explorer": data_explorer.render,
    "Model Performance": model_performance.render,
    "Model Monitoring": monitoring.render,
    "Reports": reports.render,
    "Data Management": data_management.render,
    "Settings": settings.render,
}


def main() -> None:
    shell.load_styles()
    page = shell.render_sidebar()
    view = ROUTES.get(page, overview.render)

    try:
        view()
    except Exception as exc:                       # noqa: BLE001
        st.error("Something went wrong")
        st.write("Unable to render this page. Please try again, or return to the "
                 "Overview dashboard.")
        with st.expander("Technical details"):
            st.exception(exc)


if __name__ == "__main__":
    main()
