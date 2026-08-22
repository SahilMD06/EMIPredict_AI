# EMIPredict AI — Intelligent Financial Risk Assessment Platform

Dual machine-learning platform for EMI lending decisions, built on **404,800 real-world-style financial records** across 5 EMI products.

| Task | Target variable | Best model | Held-out test result | Business target |
|---|---|---|---|---|
| Classification | `emi_eligibility` (3 classes) | XGBoost Classifier | **Accuracy 95.2%**, F1-macro 0.858, ROC-AUC 0.995 | > 90% ✅ |
| Regression | `max_monthly_emi` (INR) | XGBoost Regressor | **RMSE ₹600**, MAE ₹217, R² 0.994 | RMSE < 2000 ✅ |

## Project structure

```
EMIPredict AI/
├── EMIPredict_AI.ipynb        # Full workflow: cleaning → EDA (15 plots) → FE → 6 models → MLflow → evaluation
├── emi_features.py            # Shared feature-engineering module (notebook + app use the same logic)
│
├── app.py                     # Streamlit entry point: shell + router
├── core/
│   ├── services.py            # Model loading, prediction, dataset access, MLflow reader
│   └── report.py              # PDF assessment report (reportlab)
├── components/                # Reusable UI: shell, cards, charts, forms
├── views/                     # One module per page (9 pages)
├── utils/                     # INR formatting, input validation
├── styles/theme.css           # Centralized design system
├── .streamlit/config.toml     # Dark enterprise theme
│
├── requirements.txt           # Pinned dependencies
├── fix_mlflow_paths.py        # Re-points MLflow artifact paths after moving/cloning
├── emi_prediction_dataset.csv # Source dataset (404,800 x 27)
├── models/                    # Production artifacts (pipelines, label encoder, metrics)
├── eda_plots/                 # The 15 EDA visualizations as PNG
├── artifacts_tmp/             # Diagnostic figures logged during training
├── mlflow.db                  # MLflow tracking store (SQLite backend)
└── mlruns/                    # MLflow-logged models & run artifacts
```

## Quick start

```bash
pip install -r requirements.txt

# 1) Explore experiments (2 experiments, 6 runs, model registry with production aliases)
mlflow ui --backend-store-uri sqlite:///mlflow.db
# open http://localhost:5000

# 2) Run the web application
streamlit run app.py
```

To reproduce everything from scratch, open `EMIPredict_AI.ipynb` and *Run All* (≈10–20 min).
It regenerates cleaned data, all 15 EDA plots, the 6 MLflow runs, the model registry, and `models/`.

> Note: `mlflow.db` ships from the build environment. If MLflow artifact previews don't resolve on
> your machine, simply re-run the notebook once — it rebuilds the tracking store with local paths.

## Methodology

**1. Data quality (Section 2 of the notebook).** The raw file contains injected real-world defects:
corrupted numeric strings (`'64300.0.0'`), 8 gender spelling variants, credit scores outside 300–850,
home owners with positive rent, and ~12K missing values. Each is repaired with a documented rule
(regex repair, label mapping, domain-rule NaN + median imputation, winsorization at 0.5/99.5 pct).

**2. EDA (Section 3).** 15 visualizations with business insights. Key findings: severe class imbalance
(77% / 18% / 4%), salary dominates both targets, credit score is a weak separator, liquidity buffers
and debt-to-income strongly separate classes, no age/gender bias.

**3. Feature engineering (Section 4).** 12 derived underwriting features (debt-to-income,
expense-to-income, affordability ratio, savings-months buffer, credit bands, employment stability,
interactions) in a shared module. Preprocessing (median impute + scaling for 28 numeric, mode impute +
one-hot for 9 categorical) lives in a scikit-learn `ColumnTransformer` fitted on training data only.
Split: 70/15/15 train/validation/test, stratified on eligibility.

**4. Models + MLflow (Section 5).** Three classifiers (Logistic Regression, Random Forest, XGBoost —
all class-weighted) and three regressors (Linear, Random Forest, XGBoost). Every run logs
hyperparameters, metrics, diagnostic plots and the fitted pipeline to MLflow (SQLite backend).
Best models selected on validation macro-F1 (imbalance-robust) and RMSE, then registered as
`EMI_Eligibility_Classifier` and `Max_EMI_Regressor` with the `production` alias.

**5. Evaluation (Section 6).** Final metrics on the untouched test set, per-scenario breakdown
(performance is consistent across all 5 EMI products), feature importance, and error analysis.

## Streamlit application

A nine-page enterprise FinTech interface built on a dark design system, with all
styling centralized in `styles/theme.css`.

1. **Overview** — executive dashboard: platform KPIs, portfolio mix, production model summary
2. **EMI Assessment** — the core underwriting workflow. The 22 inputs are grouped into six
   sections; one submission runs *both* models and returns an eligibility verdict, class
   probabilities, maximum safe EMI, capacity-utilisation gauge, income-allocation breakdown,
   and explainable positive/risk factors derived from the engineered features
3. **Analytics** — portfolio analytics with product and eligibility filters
4. **Data Explorer** — paginated record browser, summary statistics and schema
5. **Model Performance** — all six models compared on validation metrics, held-out test
   results, and feature importance read from the fitted pipelines
6. **Model Monitoring** — MLflow experiments, run metrics and model registry, read directly
   from the SQLite store (no tracking server required)
7. **Reports** — formatted assessment report with PDF and CSV export
8. **Data Management** — CRUD over the record store with confirmation on destructive actions
9. **Settings** — active models, artifact status, dataset and MLflow state, environment versions

**Design notes.** The assessment form is wrapped in `st.form`, so editing fields never
triggers a rerun or recomputation. Models load through `@st.cache_resource` and the dataset
through `@st.cache_data` as a bounded sample — the full 400K-row file is never rendered in
the browser. Results are held in `st.session_state`, so the Reports page renders without
re-predicting. Every metric shown is read from real artifacts; when something is missing
(dataset, model files, MLflow store), the page renders an explicit unavailable state rather
than a placeholder value.

## Deploying to Streamlit Cloud

1. Push this folder to a GitHub repository (the dataset CSV is ~75 MB — under GitHub's 100 MB file
   limit, so it can be committed; exclude `mlartifacts/` and `mlflow.db` via `.gitignore` to keep the
   repo light).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select the repo,
   branch `main`, main file `app.py`.
3. Streamlit Cloud installs `requirements.txt` automatically and serves the public URL.

## Tech stack

Python · pandas · scikit-learn · XGBoost · MLflow (SQLite tracking + model registry) · Streamlit ·
Plotly · seaborn/matplotlib
