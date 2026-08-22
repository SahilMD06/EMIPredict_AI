"""Display formatting helpers (Indian numbering, currency, percentages)."""
from __future__ import annotations


def inr(value, decimals: int = 0) -> str:
    """Format a number as INR using the Indian digit grouping (lakh/crore).

    12345678 -> '₹1,23,45,678'
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"

    sign = "-" if value < 0 else ""
    value = abs(value)
    whole = int(value)
    frac = value - whole

    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail

    if decimals:
        s += f"{frac:.{decimals}f}"[1:]
    return f"{sign}₹{s}"


def inr_compact(value) -> str:
    """Short form for dashboards: ₹1.2 Cr, ₹4.5 L, ₹12.3 K."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"
    a = abs(value)
    sign = "-" if value < 0 else ""
    if a >= 1e7:
        return f"{sign}₹{a/1e7:.2f} Cr"
    if a >= 1e5:
        return f"{sign}₹{a/1e5:.2f} L"
    if a >= 1e3:
        return f"{sign}₹{a/1e3:.1f} K"
    return f"{sign}₹{a:.0f}"


def pct(value, decimals: int = 1) -> str:
    """0.0588 -> '5.9%'"""
    try:
        return f"{float(value) * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def num(value, decimals: int = 0) -> str:
    """Plain thousands-separated number."""
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def humanize(key: str) -> str:
    """'monthly_salary' -> 'Monthly Salary'"""
    return key.replace("_", " ").title()
