# EMIPredict AI — Test Plan

Manual verification covering every component of the project. Expected values below are the
**actual outputs** of the deployed models, not illustrations — if you get a different number,
something is genuinely wrong.

**Legend:** ✅ pass · ❌ fail · ⬜ not run

---

## 1. Environment and setup

| ID | Test | Steps | Expected result | ⬜ |
|---|---|---|---|---|
| E1 | Dependencies install | `pip install -r requirements.txt` | Completes without error. Warnings about unrelated packages (econml, ortools) are harmless | ⬜ |
| E2 | Core imports | `python -c "import pandas, sklearn, xgboost, mlflow, streamlit, plotly, reportlab; print('ok')"` | Prints `ok` | ⬜ |
| E3 | Project files present | `dir` in the project folder | `app.py`, `emi_features.py`, `models/`, `core/`, `components/`, `views/`, `utils/`, `styles/`, `docs/`, `mlflow.db`, dataset CSV all present | ⬜ |
| E4 | Model artifacts | Check `models/` | 7 files: 3 `.pkl` + 4 `.json`. Classifier ≈1.22 MB, regressor ≈0.99 MB | ⬜ |
| E5 | Dataset integrity | `python -c "import pandas as pd; d=pd.read_csv('emi_prediction_dataset.csv',low_memory=False); print(d.shape)"` | `(404800, 27)` | ⬜ |

---

## 2. Notebook

| ID | Test | Steps | Expected result | ⬜ |
|---|---|---|---|---|
| N1 | Opens with outputs | Open `EMIPredict_AI.ipynb` | All cells show saved outputs; no empty cells | ⬜ |
| N2 | EDA plots present | Scroll Section 3 | Exactly 15 plots, each followed by a written insight | ⬜ |
| N3 | Metrics visible | Scroll Sections 5–6 | Classification and regression comparison tables; test accuracy 0.9517, RMSE 600.01 | ⬜ |
| N4 | Full re-run *(optional, ~15 min)* | Kernel → Restart & Run All | Completes with no errors; regenerates `models/`, `eda_plots/`, MLflow runs | ⬜ |

> After N4 the MLflow store is rebuilt with local paths, and `models/*.pkl` are overwritten.
> If you push those regenerated pickles to GitHub, re-verify test D2 (cloud model loading).

---

## 3. Model correctness

Run the app (`streamlit run app.py`) → **EMI Assessment**. Use the **Starting profile** selector.
Leave the interest rate at its default of 12.0%.

| ID | Test | Input | Expected result | ⬜ |
|---|---|---|---|---|
| M1 | Balanced profile | Preset: *Balanced profile* → Assess | **ELIGIBLE**, confidence **97.2%**, max safe EMI **₹15,990**, requested EMI **₹9,217**, utilisation **58%** | ⬜ |
| M2 | Strong applicant | Preset: *Strong applicant* → Assess | **ELIGIBLE**, confidence **100.0%**, max safe EMI **₹54,303**, utilisation **19%**, green "within safe capacity" message | ⬜ |
| M3 | Marginal applicant | Preset: *Marginal applicant* → Assess | **NOT ELIGIBLE**, confidence **100.0%**, max safe EMI **₹497**, utilisation **4008%**, red message stating the supportable principal | ⬜ |
| M4 | Probabilities sum to 1 | Any assessment → Risk Analysis tab | Three bars; percentages total 100% | ⬜ |
| M5 | Insights respond to input | Compare M2 and M3 → Assessment Insights tab | M2: 6 positive factors, 0 risk. M3: 0 positive, 7 risk factors | ⬜ |
| M6 | Capacity gauge | M3 → Risk Analysis tab | Gauge in the red zone, pinned at its 150% ceiling (actual utilisation is far higher) | ⬜ |

**Known behaviour (not a defect):** in M2 the predicted max EMI of ₹54,303 slightly exceeds the
documented ₹50,000 domain ceiling. Gradient boosting extrapolates marginally beyond the clipped
training range for exceptionally strong profiles. Model output is deliberately left unmodified.

---

## 4. Input validation

| ID | Test | Input | Expected result | ⬜ |
|---|---|---|---|---|
| V1 | Credit score out of range | Not reachable via the slider (300–850 enforced) — confirm the slider cannot exceed 850 | Slider capped at 850 | ⬜ |
| V2 | Contradictory loan data | Existing loans = **No**, Current EMI = **5000** → Assess | Red error: *"Current EMI amount must be zero when the applicant reports no existing loans."* No result rendered | ⬜ |
| V3 | Expenses exceed income | Salary **20,000**, Groceries **25,000** → Assess | Amber warning about no disposable income; assessment still runs | ⬜ |
| V4 | Owner paying rent | Residence = **Own**, Monthly rent = **10,000** → Assess | Amber warning that rent was treated as zero during training | ⬜ |

---

## 5. Application pages

| ID | Page | Check | Expected result | ⬜ |
|---|---|---|---|---|
| P1 | Overview | Load | Three green status chips: Model Online, MLflow · 6 runs, Dataset Loaded | ⬜ |
| P2 | Overview | KPI cards | 404,800 profiles · 95.2% accuracy · ±₹600 · 6 experiments | ⬜ |
| P3 | Overview | CTA buttons | "Start EMI Assessment" navigates to the assessment page; "Explore Analytics" to analytics | ⬜ |
| P4 | Overview | Chart | Stacked bar for 5 products; **no stray "undefined" label** | ⬜ |
| P5 | EMI Assessment | Empty state | Before assessing: "No Assessment Yet" panel on the right | ⬜ |
| P6 | EMI Assessment | Form sections | Six labelled sections (A–F), 22 inputs plus the interest-rate slider | ⬜ |
| P7 | EMI Assessment | Tabs | After assessing: 4 tabs — Risk Analysis, Financial Profile, Assessment Insights, Model Detail | ⬜ |
| P8 | Analytics | Filters | Selecting a product updates all charts and the "applications in view" count | ⬜ |
| P9 | Analytics | Eligibility rates | E-commerce 26.5%, Home Appliances 26.0%, Education 18.0%, Personal 11.1%, Vehicle 10.5% | ⬜ |
| P10 | Data Explorer | KPIs | 404,800 records · 25 features · 5 scenarios · 2 targets | ⬜ |
| P11 | Data Explorer | Pagination | 60,000 records → 1,200 pages; changing page loads new rows | ⬜ |
| P12 | Data Explorer | Tabs | Record Browser, Summary Statistics, Schema all render | ⬜ |
| P13 | Model Performance | Classification table | 3 models; XGBoost best on accuracy 0.9511 and F1 0.8563, highlighted green | ⬜ |
| P14 | Model Performance | Regression table | 3 models; XGBoost RMSE 632.66 lowest, highlighted | ⬜ |
| P15 | Model Performance | Feature importance | Both charts render; classifier led by `requested_emi_to_income` | ⬜ |
| P16 | Model Monitoring | KPIs | 2 experiments · 6 runs · 2 registered models · 2 production aliases | ⬜ |
| P17 | Model Monitoring | Run tables | EMI_Classification 3 runs, EMI_Regression 3 runs, with per-run metrics | ⬜ |
| P18 | Model Monitoring | Registry tab | Both models, version 1, `@production` alias | ⬜ |
| P19 | Reports | Without assessment | "No Assessment Available" + Start Assessment button | ⬜ |
| P20 | Reports | With assessment | KPI cards, two download buttons, full on-screen report | ⬜ |
| P21 | Settings | Three tabs | Application, Models, System all render | ⬜ |
| P22 | Settings | Models tab | Load status **Loaded** (green); all 7 artifacts listed | ⬜ |
| P23 | Settings | System tab | Dataset Available, MLflow Connected, 6 runs, 2 registered models | ⬜ |

---

## 6. Report export

| ID | Test | Steps | Expected result | ⬜ |
|---|---|---|---|---|
| R1 | PDF generates | Assess → Reports → Download Assessment Report (PDF) | File downloads, ~45 KB, opens without error | ⬜ |
| R2 | Rupee renders | Open the PDF | `₹` displays correctly — **no black boxes (■)** | ⬜ |
| R3 | Layout correct | Open the PDF | Title and subtitle do not overlap; section headings stay attached to their tables | ⬜ |
| R4 | Content complete | Open the PDF | Verdict banner, Customer Profile, Financial Summary, Loan Request, EMI Assessment, Class Probabilities, Insights, Model Information, disclaimer | ⬜ |
| R5 | Figures match UI | Compare PDF against the on-screen result | Verdict, confidence, max EMI and probabilities identical | ⬜ |
| R6 | CSV export | Download Record (CSV) | Single row containing all inputs plus predictions and engineered ratios | ⬜ |

---

## 7. MLflow

| ID | Test | Steps | Expected result | ⬜ |
|---|---|---|---|---|
| F1 | Server starts | `mlflow ui --backend-store-uri sqlite:///mlflow.db` | Starts on http://127.0.0.1:5000 | ⬜ |
| F2 | Experiments listed | Model training tab → sidebar | EMI_Classification and EMI_Regression, 3 runs each | ⬜ |
| F3 | Metrics logged | Open XGBoostClassifier run → Metrics | accuracy 0.9511, f1_macro 0.8563, roc_auc_ovr 0.9946, train_time_sec | ⬜ |
| F4 | Artifacts load | Same run → Artifacts | `cm_XGBoostClassifier.png` listed; clicking it renders the confusion matrix | ⬜ |
| F5 | Registry | Model registry | Both models, v1, `@production` alias, source-run link | ⬜ |
| F6 | Run comparison | Select all 3 classification runs → Compare | Side-by-side metric table and parallel-coordinates plot | ⬜ |
| F7 | Path repair | Move/rename the project folder, then `python fix_mlflow_paths.py` | Reports paths updated and verified; artifacts load again after restart | ⬜ |

---

## 8. Data management (CRUD)

| ID | Test | Steps | Expected result | ⬜ |
|---|---|---|---|---|
| C1 | Read | Data Management → Browse Records | 150 seeded records; row slider and search both filter | ⬜ |
| C2 | Create | Add Record → fill → Create Record | Success message; stored-record count increases by 1 | ⬜ |
| C3 | Update | Update Record → pick ID and field → tick confirm → Apply | Success message; new value visible in Browse Records | ⬜ |
| C4 | Update guard | Update Record without ticking confirm | Apply button disabled | ⬜ |
| C5 | Delete guard | Delete Record without ticking confirm | Delete button disabled; permanence warning shown | ⬜ |
| C6 | Delete | Tick confirm → Delete Record | Record removed; count decreases | ⬜ |

---

## 9. Error handling and resilience

| ID | Test | Steps | Expected result | ⬜ |
|---|---|---|---|---|
| X1 | Missing dataset | Rename `emi_prediction_dataset.csv` temporarily → open Analytics | "Dataset Unavailable" panel, **no traceback**. Restore the file afterwards | ⬜ |
| X2 | Missing models | Rename `models/` temporarily → open EMI Assessment | Friendly error + collapsible technical details, no crash. Restore afterwards | ⬜ |
| X3 | Missing MLflow store | Rename `mlflow.db` temporarily → open Model Monitoring | "MLflow connection unavailable" with the reason. Restore afterwards | ⬜ |
| X4 | Cache recovery | Settings → Application → Reload models | Success message; models reload from disk | ⬜ |
| X5 | Session isolation | Assess → Settings → Clear session assessment → Reports | Reports returns to its empty state | ⬜ |

---

## 10. Performance

| ID | Test | Steps | Expected result | ⬜ |
|---|---|---|---|---|
| Y1 | First load | Open the app, time it | Under ~20 s cold (dataset sampling), noticeably faster on subsequent loads | ⬜ |
| Y2 | Form editing | Change several form fields | **No page rerun** between edits — the form only submits on the button | ⬜ |
| Y3 | Prediction latency | Click Assess | Result appears in roughly a second | ⬜ |
| Y4 | Page switching | Move between pages | Near-instant; models are not reloaded (cached) | ⬜ |
| Y5 | Browser memory | Open Data Explorer | Table stays responsive; only 50 rows render per page | ⬜ |

---

## 11. Deployment

| ID | Test | Steps | Expected result | ⬜ |
|---|---|---|---|---|
| D1 | App reachable | Open the Streamlit Cloud URL | Loads without error | ⬜ |
| D2 | Models load in cloud | Check the header | **Model Online** (this specifically catches the dill-serialisation issue) | ⬜ |
| D3 | MLflow in cloud | Check the header | **MLflow · 6 runs** | ⬜ |
| D4 | Prediction in cloud | Run an assessment | Same result as locally for the same input (compare against M1) | ⬜ |
| D5 | PDF in cloud | Download the report | Generates correctly with rupee symbols intact | ⬜ |
| D6 | Redeploy on push | Push a commit | Cloud rebuilds automatically; verify the change is live | ⬜ |
| D7 | Repo completeness | Clone into a fresh folder, install, run | App starts and models load from the cloned files alone | ⬜ |

---

## Results summary

| Section | Total | Passed | Failed |
|---|---|---|---|
| 1. Environment | 5 | | |
| 2. Notebook | 4 | | |
| 3. Model correctness | 6 | | |
| 4. Input validation | 4 | | |
| 5. Application pages | 23 | | |
| 6. Report export | 6 | | |
| 7. MLflow | 7 | | |
| 8. CRUD | 6 | | |
| 9. Error handling | 5 | | |
| 10. Performance | 5 | | |
| 11. Deployment | 7 | | |
| **Total** | **78** | | |

---

## Priority subset

Short on time? These twelve cover the highest-risk paths:

**E5, M1, M3, V2, P1, P13, P16, R1, R2, F5, D2, D4**
