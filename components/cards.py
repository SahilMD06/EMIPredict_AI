"""Reusable presentational card components."""
from __future__ import annotations

import streamlit as st

TONE_CLASS = {"neutral": "", "ok": "ok", "warn": "warn", "bad": "bad"}
BADGE_CLASS = {"ok": "badge-ok", "warn": "badge-warn", "bad": "badge-bad",
               "info": "badge-info", "mute": "badge-mute"}


def kpi(label: str, value: str, sub: str = "", tone: str = "neutral") -> None:
    """Single KPI tile. Call inside a column."""
    st.markdown(
        f"""<div class="kpi {TONE_CLASS.get(tone, '')}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-sub">{sub}</div>
            </div>""",
        unsafe_allow_html=True)


def kpi_row(items: list[dict]) -> None:
    """Render a row of KPI tiles from [{label, value, sub, tone}, ...]."""
    cols = st.columns(len(items), gap="medium")
    for col, item in zip(cols, items):
        with col:
            kpi(item.get("label", ""), item.get("value", "—"),
                item.get("sub", ""), item.get("tone", "neutral"))


def card_open(title: str = "") -> None:
    head = f'<div class="card-title">{title}</div>' if title else ""
    st.markdown(f'<div class="card">{head}', unsafe_allow_html=True)


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def panel(title: str, body_html: str) -> None:
    """Self-contained card with pre-rendered HTML body."""
    head = f'<div class="card-title">{title}</div>' if title else ""
    st.markdown(f'<div class="card">{head}{body_html}</div>', unsafe_allow_html=True)


def data_rows(pairs: list[tuple[str, str]]) -> str:
    """Key/value rows as HTML, for use inside panel()."""
    return "".join(
        f'<div class="drow"><span class="k">{k}</span><span class="v">{v}</span></div>'
        for k, v in pairs)


def factor_list(items: list[str], kind: str = "pos") -> str:
    """Bulleted positive/risk factor list as HTML."""
    if not items:
        return '<div class="factor" style="color:#64728C;">No notable factors identified.</div>'
    mark = {"pos": "mark-pos", "neg": "mark-neg"}.get(kind, "mark-neu")
    return "".join(
        f'<div class="factor"><span class="factor-mark {mark}"></span><span>{i}</span></div>'
        for i in items)


def verdict(label: str, headline: str, note: str, right_html: str = "") -> None:
    """Large decision banner for the assessment result."""
    cls = {"Eligible": "v-ok", "High_Risk": "v-warn", "Not_Eligible": "v-bad"}.get(label, "v-warn")
    st.markdown(
        f"""<div class="verdict {cls}">
                <div>
                    <div class="verdict-label">Eligibility Assessment</div>
                    <div class="verdict-value">{headline}</div>
                    <div class="verdict-note">{note}</div>
                </div>
                <div style="text-align:right;">{right_html}</div>
            </div>""",
        unsafe_allow_html=True)


def risk_meter(label: str) -> str:
    """Three-segment risk indicator. Position reflects the classification result,
    and the level is stated in text so meaning is not carried by colour alone."""
    level = {"Eligible": 0, "High_Risk": 1, "Not_Eligible": 2}.get(label, 1)
    tone = ["on-ok", "on-warn", "on-bad"][level]
    segs = "".join(
        f'<div class="meter-seg {tone if i <= level else ""}"></div>' for i in range(3))
    name = ["Low", "Moderate", "High"][level]
    return (f'<div class="meter">{segs}</div>'
            f'<div class="meter-scale"><span>Low</span><span>Moderate</span><span>High</span></div>'
            f'<div style="margin-top:12px;font-size:0.9rem;color:#E6EAF2;">'
            f'Assessed risk level: <strong>{name}</strong></div>')


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="badge {BADGE_CLASS.get(kind, "badge-info")}">{text}</span>'


def empty_state(title: str, message: str) -> None:
    st.markdown(
        f"""<div class="empty">
                <h3>{title}</h3>
                <p>{message}</p>
            </div>""",
        unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f'<div class="sect">{title}</div>', unsafe_allow_html=True)
