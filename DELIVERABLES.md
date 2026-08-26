# Deliverables Index — EMIPredict AI

Every deliverable required by the project brief, mapped to the file that satisfies it.

**Live application:** https://emipredict-ai-sahil.streamlit.app
**Repository:** https://github.com/SahilMD06/EMIPredict_AI

---

## 1. Data Processing and Analysis Scripts

| Requirement | Delivered in | Notes |
|---|---|---|
| Data preprocessing and cleaning pipeline for the 400K dataset | `emi_preprocessing.py` · `EMIPredict_AI.ipynb` §2 | Standalone importable module; also runnable as a script (`python emi_preprocessing.py`). Handles 3,962 corrupted numerics, 8 gender variants, 4,776 invalid credit scores, 2,547 logical violations, 12,027 missing cells |
| Feature engineering and transformation modules | `emi_features.py` · `EMIPredict_AI.ipynb` §4 | 12 engineered ratios → 37 model features. Imported by **both** the notebook and the app, preventing training/serving skew |
| Exploratory data analysis scripts and visualizations | `EMIPredict_AI.ipynb` §3 · `eda_plots/` | 15 plots with written insights; PNGs exported for reporting |

## 2. Machine Learning Models and Analysis

| Requirement | Delivered in | Notes |
|---|---|---|
| Minimum 3 classification models with performance comparison | `EMIPredict_AI.ipynb` §5 · `models/clf_comparison.json` | Logistic Regression, Random Forest, XGBoost — compared on 5 metrics |
| Minimum 3 regression models with evaluation metrics | `EMIPredict_AI.ipynb` §5 · `models/reg_comparison.json` | Linear, Random Forest, XGBoost — RMSE, MAE, R², MAPE |
| Best model selection process and justification | `EMIPredict_AI.ipynb` §5.5 · Model Performance Report §2.2, §3.2 | Macro-F1 for classification (imbalance-robust), RMSE for regression (business target) |
| Model performance evaluation and comparison reports | `docs/EMIPredict_AI_Model_Performance_Report.docx` | 8 pages covering all 6 models, per-class behaviour, feature importance |
| MLflow experiment tracking and model registry with all variants | `mlflow.db` · `mlruns/` · app → Model Monitoring | 2 experiments, 6 runs, 2 registered models with `@production` aliases |

## 3. Web Application and Deployment

| Requirement | Delivered in | Notes |
|---|---|---|
| Multi-page Streamlit application with interactive UI | `app.py` · `views/` · `components/` · `styles/theme.css` | 9 pages, custom dark FinTech design system |
| Real-time prediction for classification and regression | app → EMI Assessment | One submission runs both models; verdict, probabilities, max safe EMI, capacity gauge, explainable factors |
| Cloud deployment with public URL | https://emipredict-ai-sahil.streamlit.app | Streamlit Cloud, Python 3.14, auto-redeploy on push |
| GitHub repository with complete codebase and documentation | https://github.com/SahilMD06/EMIPredict_AI | Includes notebook, app, models, MLflow store, docs |

## 4. Documentation and Reports

| Requirement | Delivered in | Pages |
|---|---|---|
| Comprehensive technical documentation (methodology and architecture) | `docs/EMIPredict_AI_Technical_Documentation.docx` | 13 |
| EDA report with business insights and visualizations | `docs/EMIPredict_AI_EDA_Report.docx` | 14 — all 15 plots embedded |
| Model performance analysis and MLflow experiment comparison | `docs/EMIPredict_AI_Model_Performance_Report.docx` | 8 |
| Business impact assessment and recommendations | `docs/EMIPredict_AI_Business_Impact_Assessment.docx` | 7 |

Supporting: `README.md` (setup and overview) · `docs/TEST_PLAN.md` (78 verification cases)

---

## Results against the brief's targets

| Target | Required | Achieved | |
|---|---|---|---|
| Classification accuracy | > 90% | **95.17%** | ✅ |
| Regression RMSE | < ₹2,000 | **₹600.01** | ✅ |
| Classification models | ≥ 3 | 3 | ✅ |
| Regression models | ≥ 3 | 3 | ✅ |
| MLflow tracking + registry | Required | 6 runs, 2 registered models | ✅ |
| Cloud deployment | Required | Live public URL | ✅ |

Both headline results are measured on a held-out test set of ~60,720 records, evaluated once
after model selection was final.

---

## Evaluation rubric coverage

| Criterion | Weight | Where to look |
|---|---|---|
| Data preprocessing completeness and quality assessment | 15% | `emi_preprocessing.py`, notebook §2, Technical Doc §5 |
| ML model development (min 3 per task) | 25% | Notebook §5, Model Performance Report §2–3 |
| Best model selection and justification | 15% | Notebook §5.5, Model Performance Report §2.2 and §3.2 |
| MLflow integration and model registry | 15% | `mlflow.db`, app → Model Monitoring, Model Performance Report §6–7 |
| Streamlit application functionality | 20% | Deployed app, all 9 pages |
| Cloud deployment stability and accessibility | 10% | Public Streamlit Cloud URL |

---

## Running the project

```bash
pip install -r requirements.txt

# Application
streamlit run app.py

# MLflow interface
mlflow ui --backend-store-uri sqlite:///mlflow.db

# Cleaning pipeline standalone
python emi_preprocessing.py emi_prediction_dataset.csv

# Full reproduction
# open EMIPredict_AI.ipynb and Run All  (~15 min)
```

If the project folder is moved or cloned, run `python fix_mlflow_paths.py` once to re-anchor
the MLflow artifact paths.

---

## File structure

```
EMIPredict AI/
├── EMIPredict_AI.ipynb            Full workflow: cleaning → EDA → features → models → MLflow
├── emi_preprocessing.py           Cleaning pipeline (importable + runnable)
├── emi_features.py                Feature engineering (shared by notebook and app)
├── fix_mlflow_paths.py            Re-anchors MLflow artifact paths after a move
│
├── app.py                         Streamlit entry point
├── core/                          Model, data, MLflow and PDF services
├── components/                    Shell, cards, charts, forms
├── views/                         One module per page (9)
├── utils/                         Formatting and validation
├── styles/theme.css               Design system
├── .streamlit/config.toml         Theme configuration
│
├── models/                        Production pipelines + metric files
├── eda_plots/                     15 EDA visualizations
├── mlflow.db, mlruns/             MLflow tracking store and artifacts
├── docs/                          4 reports + test plan
├── emi_prediction_dataset.csv     Source dataset (404,800 × 27)
└── requirements.txt
```
