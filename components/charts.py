"""Plotly chart builders with a shared dark FinTech theme."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core.services import CLASS_COLORS, CLASS_ORDER

FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"
GRID = "rgba(255,255,255,0.06)"
TEXT = "#8A97AD"


def style(fig: go.Figure, height: int = 340, legend: bool = True) -> go.Figure:
    """Apply the application chart theme."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=TEXT),
        margin=dict(l=10, r=10, t=34, b=10),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=11)),
        hoverlabel=dict(bgcolor="#18233A", bordercolor="#22304C",
                        font=dict(color="#E6EAF2", family=FONT, size=12)),
        title=dict(font=dict(size=13, color="#E6EAF2")),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    return fig


def probability_bars(probabilities: dict) -> go.Figure:
    """Class probabilities from the classifier."""
    order = [c for c in CLASS_ORDER if c in probabilities]
    df = pd.DataFrame({"Class": [c.replace("_", " ") for c in order],
                       "Probability": [probabilities[c] for c in order]})
    fig = px.bar(df, x="Probability", y="Class", orientation="h",
                 color="Class", text="Probability",
                 color_discrete_sequence=[CLASS_COLORS[c] for c in order])
    fig.update_traces(texttemplate="%{text:.1%}", textposition="outside",
                      marker_line_width=0, width=0.55)
    fig.update_xaxes(range=[0, 1.15], tickformat=".0%", title=None)
    fig.update_yaxes(title=None)
    return style(fig, height=210, legend=False)


def allocation_donut(salary: float, existing_emi: float, expenses: float,
                     proposed_emi: float) -> go.Figure:
    """Monthly income allocation after the proposed obligation."""
    remaining = max(salary - existing_emi - expenses - proposed_emi, 0)
    labels = ["Household expenses", "Existing EMI", "Proposed EMI", "Remaining income"]
    values = [expenses, existing_emi, proposed_emi, remaining]
    colors = ["#64748B", "#F59E0B", "#3B82F6", "#22C55E"]

    keep = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    fig = go.Figure(go.Pie(
        labels=[k[0] for k in keep], values=[k[1] for k in keep], hole=0.62,
        marker=dict(colors=[k[2] for k in keep], line=dict(color="#0B1220", width=2)),
        textinfo="percent", textfont=dict(size=11),
        hovertemplate="%{label}<br>₹%{value:,.0f}<extra></extra>"))
    fig.add_annotation(text=f"<b>₹{salary:,.0f}</b><br><span style='font-size:10px'>MONTHLY INCOME</span>",
                       showarrow=False, font=dict(size=15, color="#E6EAF2"))
    return style(fig, height=330)


def capacity_gauge(proposed_emi: float, max_emi: float) -> go.Figure:
    """Requested obligation against the model's safe-capacity estimate."""
    util = (proposed_emi / max_emi * 100) if max_emi > 0 else 0
    colour = "#22C55E" if util <= 80 else ("#F59E0B" if util <= 100 else "#EF4444")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=min(util, 200),
        number={"suffix": "%", "font": {"size": 30, "color": "#E6EAF2"}},
        gauge={
            "axis": {"range": [0, 150], "tickwidth": 1, "tickcolor": TEXT,
                     "tickfont": {"size": 10}},
            "bar": {"color": colour, "thickness": 0.7},
            "bgcolor": "rgba(255,255,255,0.04)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 80], "color": "rgba(34,197,94,0.12)"},
                {"range": [80, 100], "color": "rgba(245,158,11,0.12)"},
                {"range": [100, 150], "color": "rgba(239,68,68,0.12)"},
            ],
            "threshold": {"line": {"color": "#E6EAF2", "width": 2},
                          "thickness": 0.8, "value": 100},
        }))
    return style(fig, height=250, legend=False)


def importance_bars(df: pd.DataFrame, title: str = "") -> go.Figure:
    """Feature importance from the fitted pipeline."""
    d = df.sort_values("importance")
    fig = px.bar(d, x="importance", y="feature", orientation="h",
                 color_discrete_sequence=["#3B82F6"], title=title)
    fig.update_traces(marker_line_width=0)
    fig.update_xaxes(title="Relative importance")
    fig.update_yaxes(title=None)
    return style(fig, height=max(300, 26 * len(d)), legend=False)


def eligibility_distribution(df: pd.DataFrame) -> go.Figure:
    counts = df["emi_eligibility"].value_counts().reindex(CLASS_ORDER).fillna(0)
    fig = px.bar(x=[c.replace("_", " ") for c in counts.index], y=counts.values,
                 color=counts.index, text=counts.values,
                 color_discrete_map={c: CLASS_COLORS[c] for c in CLASS_ORDER})
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", marker_line_width=0)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Applications")
    return style(fig, legend=False)


def scenario_mix(df: pd.DataFrame) -> go.Figure:
    ct = (pd.crosstab(df["emi_scenario"], df["emi_eligibility"], normalize="index") * 100)
    ct = ct.reindex(columns=[c for c in CLASS_ORDER if c in ct.columns])
    fig = go.Figure()
    for cls in ct.columns:
        fig.add_bar(name=cls.replace("_", " "), y=ct.index, x=ct[cls], orientation="h",
                    marker_color=CLASS_COLORS[cls],
                    hovertemplate="%{y}<br>%{x:.1f}%<extra></extra>")
    fig.update_layout(barmode="stack", legend_title_text="")
    fig.update_xaxes(title_text="Share of applications (%)", range=[0, 100])
    fig.update_yaxes(title_text="")
    return style(fig, height=330)


def income_vs_emi(df: pd.DataFrame, n: int = 6000) -> go.Figure:
    d = df.sample(min(n, len(df)), random_state=42)
    fig = px.scatter(d, x="monthly_salary", y="max_monthly_emi", color="emi_eligibility",
                     color_discrete_map=CLASS_COLORS, opacity=0.5,
                     labels={"monthly_salary": "Monthly income (₹)",
                             "max_monthly_emi": "Maximum safe EMI (₹)",
                             "emi_eligibility": "Eligibility"})
    fig.update_traces(marker=dict(size=5, line=dict(width=0)))
    return style(fig, height=380)


def credit_score_box(df: pd.DataFrame) -> go.Figure:
    fig = px.box(df, x="emi_eligibility", y="credit_score", color="emi_eligibility",
                 color_discrete_map=CLASS_COLORS,
                 category_orders={"emi_eligibility": CLASS_ORDER},
                 labels={"emi_eligibility": "", "credit_score": "Credit score"})
    fig.update_traces(marker=dict(size=3), line=dict(width=1.4))
    return style(fig, height=340, legend=False)


def expense_vs_income(df: pd.DataFrame, n: int = 6000) -> go.Figure:
    d = df.sample(min(n, len(df)), random_state=42).copy()
    exp_cols = ["monthly_rent", "school_fees", "college_fees", "travel_expenses",
                "groceries_utilities", "other_monthly_expenses"]
    have = [c for c in exp_cols if c in d.columns]
    d["total_expenses"] = d[have].sum(axis=1)
    fig = px.scatter(d, x="monthly_salary", y="total_expenses", color="emi_eligibility",
                     color_discrete_map=CLASS_COLORS, opacity=0.5,
                     labels={"monthly_salary": "Monthly income (₹)",
                             "total_expenses": "Total monthly expenses (₹)",
                             "emi_eligibility": "Eligibility"})
    fig.update_traces(marker=dict(size=5, line=dict(width=0)))
    return style(fig, height=380)


def metric_comparison(df: pd.DataFrame, metrics: list[str], target: float | None = None,
                      target_label: str = "") -> go.Figure:
    """Grouped bars comparing trained models on the given metrics."""
    palette = ["#3B82F6", "#22C55E", "#A78BFA", "#F59E0B"]
    fig = go.Figure()
    for i, m in enumerate(metrics):
        if m not in df.columns:
            continue
        fig.add_bar(name=m, x=df["model"], y=df[m],
                    marker_color=palette[i % len(palette)],
                    text=[f"{v:,.4g}" for v in df[m]], textposition="outside")
    if target is not None:
        fig.add_hline(y=target, line_dash="dash", line_color="#EF4444",
                      annotation_text=target_label,
                      annotation_font=dict(color="#FCA5A5", size=11))
    fig.update_layout(barmode="group")
    fig.update_xaxes(title=None)
    return style(fig, height=360)
