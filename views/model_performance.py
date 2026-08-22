"""Model Performance — evaluation results for every trained model."""
from __future__ import annotations

import streamlit as st

from components import cards, charts, shell
from core import services
from utils.formatting import inr, pct


def render() -> None:
    shell.render_header("Model Performance", "Machine Learning")

    comps = services.load_model_comparisons()
    clf_df, reg_df, test = comps["clf"], comps["reg"], comps["test"]

    if clf_df is None and reg_df is None:
        cards.empty_state("Evaluation Results Unavailable",
                          "Model comparison files were not found in the models directory. "
                          "They are produced by Section 5 of the training notebook.")
        return

    meta = services.load_models().get("meta", {})
    clf_test = test.get("clf", {})
    reg_test = test.get("reg", {})

    cards.kpi_row([
        {"label": "Best Classifier", "value": meta.get("best_classifier", "—"),
         "sub": f"Accuracy {pct(clf_test.get('accuracy'))} on test set" if clf_test else
                "Selected on validation macro-F1", "tone": "ok"},
        {"label": "Best Regressor", "value": meta.get("best_regressor", "—"),
         "sub": f"RMSE {inr(reg_test.get('rmse'))} on test set" if reg_test else
                "Selected on validation RMSE", "tone": "ok"},
        {"label": "Models Trained", "value": str((len(clf_df) if clf_df is not None else 0) +
                                                 (len(reg_df) if reg_df is not None else 0)),
         "sub": "Across both learning tasks"},
        {"label": "Selection Metric", "value": "Macro-F1 · RMSE",
         "sub": "Imbalance-robust and error-based"},
    ])

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    tab_c, tab_r, tab_i = st.tabs(["Classification Models", "Regression Models",
                                   "Feature Importance"])

    # ---------------- classification ----------------
    with tab_c:
        if clf_df is None:
            st.info("Classification comparison data is unavailable.")
        else:
            st.markdown('<div class="card-title">Validation performance — EMI eligibility'
                        '</div>', unsafe_allow_html=True)
            show = clf_df.rename(columns={
                "model": "Model", "accuracy": "Accuracy", "precision_macro": "Precision",
                "recall_macro": "Recall", "f1_macro": "F1 (macro)",
                "roc_auc_ovr": "ROC-AUC", "train_time_sec": "Train time (s)"})
            st.dataframe(show.set_index("Model").style.format("{:.4f}", na_rep="—")
                         .highlight_max(axis=0, color="rgba(34,197,94,0.18)"),
                         use_container_width=True)

            st.plotly_chart(
                charts.metric_comparison(clf_df, ["accuracy", "f1_macro", "roc_auc_ovr"],
                                         target=0.90, target_label="90% accuracy target"),
                use_container_width=True, config={"displayModeBar": False})

            if clf_test:
                st.markdown('<div class="card-title">Held-out test set — production model'
                            '</div>', unsafe_allow_html=True)
                rows = [("Accuracy", pct(clf_test.get("accuracy"))),
                        ("Precision (macro)", f"{clf_test.get('precision_macro', 0):.4f}"),
                        ("Recall (macro)", f"{clf_test.get('recall_macro', 0):.4f}"),
                        ("F1 (macro)", f"{clf_test.get('f1_macro', 0):.4f}"),
                        ("ROC-AUC (one-vs-rest)", f"{clf_test.get('roc_auc_ovr', 0):.4f}")]
                cards.panel(meta.get("best_classifier", "Classifier"), cards.data_rows(rows))
                st.caption("Macro averaging weights all three eligibility classes equally, "
                           "so performance on the small High Risk class is not masked by "
                           "the majority class.")

    # ---------------- regression ----------------
    with tab_r:
        if reg_df is None:
            st.info("Regression comparison data is unavailable.")
        else:
            st.markdown('<div class="card-title">Validation performance — maximum safe EMI'
                        '</div>', unsafe_allow_html=True)
            show = reg_df.rename(columns={
                "model": "Model", "rmse": "RMSE (₹)", "mae": "MAE (₹)",
                "r2": "R²", "mape": "MAPE", "train_time_sec": "Train time (s)"})
            st.dataframe(show.set_index("Model").style.format("{:.4f}", na_rep="—")
                         .highlight_min(subset=["RMSE (₹)", "MAE (₹)"], axis=0,
                                        color="rgba(34,197,94,0.18)"),
                         use_container_width=True)

            st.plotly_chart(
                charts.metric_comparison(reg_df, ["rmse", "mae"], target=2000,
                                         target_label="RMSE target ₹2,000"),
                use_container_width=True, config={"displayModeBar": False})

            if reg_test:
                rows = [("RMSE", inr(reg_test.get("rmse"))),
                        ("MAE", inr(reg_test.get("mae"))),
                        ("R²", f"{reg_test.get('r2', 0):.4f}"),
                        ("MAPE", pct(reg_test.get("mape")))]
                cards.panel(meta.get("best_regressor", "Regressor"), cards.data_rows(rows))

    # ---------------- importance ----------------
    with tab_i:
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            imp = services.feature_importance("classifier", 14)
            if imp is not None:
                st.markdown('<div class="card-title">Eligibility model</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(charts.importance_bars(imp), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.info("Feature importance is unavailable for the active classifier.")
        with c2:
            imp = services.feature_importance("regressor", 14)
            if imp is not None:
                st.markdown('<div class="card-title">Affordability model</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(charts.importance_bars(imp), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.info("Feature importance is unavailable for the active regressor.")
        st.caption("Importances are read directly from the fitted production pipelines.")
