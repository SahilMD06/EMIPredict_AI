"""PDF generation for the financial assessment report (reportlab)."""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from core import services
from utils.formatting import inr, pct

NAVY = colors.HexColor("#0B1220")
BLUE = colors.HexColor("#2563EB")
GREY = colors.HexColor("#64728C")
LINE = colors.HexColor("#D8DEE9")
TONE = {"Eligible": colors.HexColor("#15803D"),
        "High_Risk": colors.HexColor("#B45309"),
        "Not_Eligible": colors.HexColor("#B91C1C")}


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("Brand", fontName="Helvetica-Bold", fontSize=17,
                         textColor=NAVY, spaceAfter=2))
    s.add(ParagraphStyle("Tag", fontName="Helvetica", fontSize=8.5, textColor=GREY,
                         spaceAfter=12))
    s.add(ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=10.5,
                         textColor=BLUE, spaceBefore=13, spaceAfter=6))
    s.add(ParagraphStyle("Body", fontName="Helvetica", fontSize=9,
                         textColor=colors.HexColor("#1F2937"), leading=13.5))
    s.add(ParagraphStyle("Small", fontName="Helvetica", fontSize=7.6,
                         textColor=GREY, leading=10.5))
    s.add(ParagraphStyle("Verdict", fontName="Helvetica-Bold", fontSize=15,
                         alignment=TA_CENTER, spaceBefore=3, spaceAfter=3))
    return s


def _kv_table(rows, widths=(62 * mm, 88 * mm)):
    t = Table([[k, v] for k, v in rows], colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.8),
        ("TEXTCOLOR", (0, 0), (0, -1), GREY),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def build_report(result: dict) -> bytes:
    """Render the assessment result as a PDF and return the bytes."""
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="EMIPredict AI — Financial Assessment Report",
                            author="EMIPredict AI")

    p = result["profile"]
    e = result["engineered"]
    label = result["label"]
    max_emi = result["max_monthly_emi"]
    rate = result.get("interest_rate", 12.0)
    proposed = services.amortized_emi(p["requested_amount"], rate, p["requested_tenure"])

    story = []
    story.append(Paragraph("EMIPredict AI", s["Brand"]))
    story.append(Paragraph("Intelligent Financial Risk Assessment · FinTech &amp; Banking",
                           s["Tag"]))

    # verdict banner
    verdict_tbl = Table([[Paragraph(label.replace("_", " ").upper(),
                                    ParagraphStyle("V", parent=s["Verdict"],
                                                   textColor=TONE.get(label, NAVY)))]],
                        colWidths=[150 * mm])
    verdict_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, TONE.get(label, NAVY)),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    story.append(verdict_tbl)
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Eligibility assessment produced with {result['confidence']:.1%} model confidence. "
        f"Maximum safe monthly EMI: <b>{inr(max_emi)}</b>.", s["Small"]))

    story.append(Paragraph("Customer Profile", s["H2"]))
    story.append(_kv_table([
        ("Age", f"{p['age']} years"),
        ("Gender", p["gender"]),
        ("Marital status", p["marital_status"]),
        ("Education", p["education"]),
        ("Employment", f"{p['employment_type']} · {p['company_type']}"),
        ("Work experience", f"{p['years_of_employment']:.1f} years"),
        ("Household", f"{p['family_size']} members · {p['dependents']} dependants"),
        ("Residence", p["house_type"]),
    ]))

    story.append(Paragraph("Financial Summary", s["H2"]))
    story.append(_kv_table([
        ("Monthly income", inr(p["monthly_salary"])),
        ("Household expenses", inr(e.get("total_monthly_expenses", 0))),
        ("Existing EMI obligations", inr(p["current_emi_amount"])),
        ("Disposable income", inr(e.get("disposable_income", 0))),
        ("Debt-to-income ratio", pct(e.get("debt_to_income", 0))),
        ("Expense-to-income ratio", pct(e.get("expense_to_income", 0))),
        ("Credit score", f"{int(p['credit_score'])} ({e.get('credit_band', '')})"),
        ("Bank balance", inr(p["bank_balance"])),
        ("Emergency fund", inr(p["emergency_fund"])),
        ("Liquidity buffer", f"{e.get('savings_months', 0):.1f} months of outgoings"),
    ]))

    story.append(Paragraph("Loan Request", s["H2"]))
    story.append(_kv_table([
        ("Lending product", p["emi_scenario"]),
        ("Requested amount", inr(p["requested_amount"])),
        ("Requested tenure", f"{p['requested_tenure']} months"),
        ("Assumed interest rate", f"{rate:.1f}% per annum"),
        ("Resulting instalment", inr(proposed)),
    ]))

    story.append(Paragraph("EMI Assessment", s["H2"]))
    headroom = max_emi - proposed
    if proposed <= max_emi * 0.8:
        note = (f"The requested instalment sits within assessed capacity, leaving "
                f"{inr(headroom)} of monthly headroom.")
    elif proposed <= max_emi:
        note = (f"The requested instalment approaches the safe ceiling; only "
                f"{inr(headroom)} of monthly headroom remains.")
    else:
        affordable = services.affordable_principal(max_emi, rate, p["requested_tenure"])
        note = (f"The requested instalment exceeds assessed capacity by "
                f"{inr(abs(headroom))}. The supportable principal at these terms is "
                f"approximately {inr(affordable)}.")
    story.append(_kv_table([
        ("Maximum safe monthly EMI", inr(max_emi)),
        ("Requested monthly instalment", inr(proposed)),
        ("Capacity utilisation", f"{(proposed / max_emi * 100) if max_emi else 0:.0f}%"),
        ("Eligibility decision", label.replace("_", " ")),
    ]))
    story.append(Spacer(1, 5))
    story.append(Paragraph(note, s["Body"]))

    story.append(Paragraph("Class Probabilities", s["H2"]))
    story.append(_kv_table([(k.replace("_", " "), f"{v:.1%}")
                            for k, v in result["probabilities"].items()]))

    positives, risks = services.derive_insights(result)
    story.append(Paragraph("Assessment Insights", s["H2"]))
    if positives:
        story.append(Paragraph("<b>Positive factors</b>", s["Body"]))
        for item in positives:
            story.append(Paragraph(f"• {item}", s["Body"]))
        story.append(Spacer(1, 5))
    if risks:
        story.append(Paragraph("<b>Risk factors</b>", s["Body"]))
        for item in risks:
            story.append(Paragraph(f"• {item}", s["Body"]))

    story.append(Paragraph("Model Information", s["H2"]))
    story.append(_kv_table([
        ("Classification model", result["models"]["classifier"]),
        ("Regression model", result["models"]["regressor"]),
        ("Engineered features", "37"),
        ("Assessment timestamp", result["timestamp"]),
    ]))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "This assessment is generated by a machine-learning model trained on historical "
        "financial profiles. It is decision support for a qualified underwriter and does "
        "not by itself constitute a credit decision or an offer of finance. "
        f"Generated {datetime.now().strftime('%d %B %Y at %H:%M')}.", s["Small"]))

    doc.build(story)
    return buf.getvalue()
