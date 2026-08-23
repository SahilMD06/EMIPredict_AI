"""PDF generation for the financial assessment report (reportlab)."""
from __future__ import annotations

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from core import services
from utils.formatting import inr, pct

NAVY = colors.HexColor("#0B1220")
BLUE = colors.HexColor("#2563EB")
GREY = colors.HexColor("#64728C")
LINE = colors.HexColor("#D8DEE9")
TONE = {"Eligible": colors.HexColor("#15803D"),
        "High_Risk": colors.HexColor("#B45309"),
        "Not_Eligible": colors.HexColor("#B91C1C")}


def _register_fonts() -> tuple[str, str]:
    """Register a Unicode font so the rupee sign renders.

    Helvetica (a PDF base-14 font) has no glyph for U+20B9 and prints a black box.
    DejaVuSans does, and ships inside matplotlib — already a project dependency —
    so no extra package or bundled font file is required. Falls back to Helvetica
    if it cannot be found, in which case currency is written as "Rs.".
    """
    try:
        import matplotlib
        ttf_dir = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
        regular = os.path.join(ttf_dir, "DejaVuSans.ttf")
        bold = os.path.join(ttf_dir, "DejaVuSans-Bold.ttf")
        if os.path.exists(regular) and os.path.exists(bold):
            if "DejaVuSans" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("DejaVuSans", regular))
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold))
            return "DejaVuSans", "DejaVuSans-Bold"
    except Exception:                              # noqa: BLE001
        pass
    return "Helvetica", "Helvetica-Bold"


FONT_R, FONT_B = _register_fonts()
UNICODE_OK = FONT_R != "Helvetica"


def _money(value) -> str:
    """Currency string that is safe for the active font."""
    text = inr(value)
    return text if UNICODE_OK else text.replace("₹", "Rs. ")


def _styles():
    """Every style sets an explicit leading — reportlab defaults to 12pt
    regardless of font size, which makes larger text overlap."""
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("Brand", fontName=FONT_B, fontSize=17, leading=21,
                         textColor=NAVY, spaceAfter=3))
    s.add(ParagraphStyle("Tag", fontName=FONT_R, fontSize=8.5, leading=11.5,
                         textColor=GREY, spaceAfter=14))
    s.add(ParagraphStyle("H2", fontName=FONT_B, fontSize=10.5, leading=14,
                         textColor=BLUE, spaceBefore=15, spaceAfter=7))
    s.add(ParagraphStyle("Body", fontName=FONT_R, fontSize=9, leading=13.5,
                         textColor=colors.HexColor("#1F2937")))
    # named "Point" because reportlab's sample stylesheet already defines "Bullet"
    s.add(ParagraphStyle("Point", fontName=FONT_R, fontSize=9, leading=13.5,
                         leftIndent=10, textColor=colors.HexColor("#1F2937")))
    s.add(ParagraphStyle("Small", fontName=FONT_R, fontSize=7.6, leading=11,
                         textColor=GREY))
    s.add(ParagraphStyle("Verdict", fontName=FONT_B, fontSize=15, leading=19,
                         alignment=TA_CENTER, spaceBefore=3, spaceAfter=3))
    return s


def _kv_table(rows, widths=(64 * mm, 90 * mm)):
    t = Table([[k, v] for k, v in rows], colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), FONT_R),
        ("FONTNAME", (1, 0), (1, -1), FONT_B),
        ("FONTSIZE", (0, 0), (-1, -1), 8.8),
        ("LEADING", (0, 0), (-1, -1), 11.5),
        ("TEXTCOLOR", (0, 0), (0, -1), GREY),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _section(styles, heading: str, flowable):
    """Keep a heading attached to its table so they never split across pages."""
    return KeepTogether([Paragraph(heading, styles["H2"]), flowable])


def build_report(result: dict) -> bytes:
    """Render the assessment result as a PDF and return the bytes."""
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="EMIPredict AI - Financial Assessment Report",
                            author="EMIPredict AI")
    frame_width = doc.width

    p = result["profile"]
    e = result["engineered"]
    label = result["label"]
    max_emi = result["max_monthly_emi"]
    rate = result.get("interest_rate", 12.0)
    proposed = services.amortized_emi(p["requested_amount"], rate, p["requested_tenure"])

    story = []
    story.append(Paragraph("EMIPredict AI", s["Brand"]))
    story.append(Paragraph(
        "Intelligent Financial Risk Assessment &nbsp;|&nbsp; FinTech &amp; Banking",
        s["Tag"]))

    # verdict banner
    verdict_tbl = Table([[Paragraph(label.replace("_", " ").upper(),
                                    ParagraphStyle("V", parent=s["Verdict"],
                                                   textColor=TONE.get(label, NAVY)))]],
                        colWidths=[frame_width])
    verdict_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, TONE.get(label, NAVY)),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    story.append(verdict_tbl)
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"Eligibility assessment produced with {result['confidence']:.1%} model confidence. "
        f"Maximum safe monthly EMI: <b>{_money(max_emi)}</b>.", s["Small"]))

    story.append(_section(s, "Customer Profile", _kv_table([
        ("Age", f"{p['age']} years"),
        ("Gender", p["gender"]),
        ("Marital status", p["marital_status"]),
        ("Education", p["education"]),
        ("Employment", f"{p['employment_type']} · {p['company_type']}"),
        ("Work experience", f"{p['years_of_employment']:.1f} years"),
        ("Household", f"{p['family_size']} members, {p['dependents']} dependants"),
        ("Residence", p["house_type"]),
    ])))

    story.append(_section(s, "Financial Summary", _kv_table([
        ("Monthly income", _money(p["monthly_salary"])),
        ("Household expenses", _money(e.get("total_monthly_expenses", 0))),
        ("Existing EMI obligations", _money(p["current_emi_amount"])),
        ("Disposable income", _money(e.get("disposable_income", 0))),
        ("Debt-to-income ratio", pct(e.get("debt_to_income", 0))),
        ("Expense-to-income ratio", pct(e.get("expense_to_income", 0))),
        ("Credit score", f"{int(p['credit_score'])} ({e.get('credit_band', '')})"),
        ("Bank balance", _money(p["bank_balance"])),
        ("Emergency fund", _money(p["emergency_fund"])),
        ("Liquidity buffer", f"{e.get('savings_months', 0):.1f} months of outgoings"),
    ])))

    story.append(_section(s, "Loan Request", _kv_table([
        ("Lending product", p["emi_scenario"]),
        ("Requested amount", _money(p["requested_amount"])),
        ("Requested tenure", f"{p['requested_tenure']} months"),
        ("Assumed interest rate", f"{rate:.1f}% per annum"),
        ("Resulting instalment", _money(proposed)),
    ])))

    headroom = max_emi - proposed
    if proposed <= max_emi * 0.8:
        note = (f"The requested instalment sits within assessed capacity, leaving "
                f"{_money(headroom)} of monthly headroom.")
    elif proposed <= max_emi:
        note = (f"The requested instalment approaches the safe ceiling; only "
                f"{_money(headroom)} of monthly headroom remains.")
    else:
        affordable = services.affordable_principal(max_emi, rate, p["requested_tenure"])
        note = (f"The requested instalment exceeds assessed capacity by "
                f"{_money(abs(headroom))}. The supportable principal at these terms is "
                f"approximately {_money(affordable)}.")
    story.append(_section(s, "EMI Assessment", _kv_table([
        ("Maximum safe monthly EMI", _money(max_emi)),
        ("Requested monthly instalment", _money(proposed)),
        ("Capacity utilisation", f"{(proposed / max_emi * 100) if max_emi else 0:.0f}%"),
        ("Eligibility decision", label.replace("_", " ")),
    ])))
    story.append(Spacer(1, 6))
    story.append(Paragraph(note, s["Body"]))

    story.append(_section(s, "Class Probabilities", _kv_table(
        [(k.replace("_", " "), f"{v:.1%}") for k, v in result["probabilities"].items()])))

    positives, risks = services.derive_insights(result)
    insight_block = [Paragraph("Assessment Insights", s["H2"])]
    if positives:
        insight_block.append(Paragraph("<b>Positive factors</b>", s["Body"]))
        insight_block += [Paragraph(f"&bull; {i}", s["Point"]) for i in positives]
        insight_block.append(Spacer(1, 6))
    if risks:
        insight_block.append(Paragraph("<b>Risk factors</b>", s["Body"]))
        insight_block += [Paragraph(f"&bull; {i}", s["Point"]) for i in risks]
    if not positives and not risks:
        insight_block.append(Paragraph("No notable factors identified.", s["Body"]))
    story.append(KeepTogether(insight_block))

    story.append(_section(s, "Model Information", _kv_table([
        ("Classification model", result["models"]["classifier"]),
        ("Regression model", result["models"]["regressor"]),
        ("Engineered features", "37"),
        ("Assessment timestamp", result["timestamp"]),
    ])))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "This assessment is generated by a machine-learning model trained on historical "
        "financial profiles. It is decision support for a qualified underwriter and does "
        "not by itself constitute a credit decision or an offer of finance. "
        f"Generated {datetime.now().strftime('%d %B %Y at %H:%M')}.", s["Small"]))

    doc.build(story)
    return buf.getvalue()
