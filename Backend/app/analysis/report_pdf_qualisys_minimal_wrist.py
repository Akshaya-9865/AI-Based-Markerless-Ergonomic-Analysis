"""
Minimal Qualisys-style report (ONLY parameters your pipeline measures),
INCLUDING WRIST, with ROM tables visible, and WITHOUT "POWERED BY QUALISYS".

Expected PNG names in graphs_dir (from pipeline):
- hip_flex_deg.png
- knee_flex_deg.png
- ankle_dorsi_deg.png
- trunk_tilt_deg.png
- shoulder_flex_deg.png
- elbow_flex_deg.png
- wrist_flex_deg.png   <-- add this in pipeline (instructions below)
- head_flex_deg.png

Usage (pipeline.py):
    from .report_pdf_qualisys_minimal_wrist import build_qualisys_pdf_minimal
"""

from __future__ import annotations

import os
from datetime import date
from typing import Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle


PAGE_W, PAGE_H = A4
M_LEFT = 1.6 * cm
M_RIGHT = 1.6 * cm
M_BOTTOM = 1.2 * cm

CONTENT_W = PAGE_W - M_LEFT - M_RIGHT

# 3-up grid like Qualisys
GAP_X = 0.6 * cm
GAP_Y = 0.7 * cm
CARD_W = (CONTENT_W - 2 * GAP_X) / 3.0
CARD_H = 5.0 * cm
TITLE_H = 0.55 * cm
IMG_H = CARD_H - TITLE_H

C_HEADER = colors.HexColor("#666666")
C_SECTION = colors.HexColor("#6F6F6F")
C_RULE = colors.HexColor("#DDDDDD")
C_LIGHT = colors.HexColor("#F4F4F4")
C_ACCENT = colors.HexColor("#2BB3A5")
C_TEXT = colors.HexColor("#222222")


def _safe_get(d: dict, key: str, default=""):
    v = d.get(key, default)
    return default if v is None else v


def _draw_top_meta_bar(c: canvas.Canvas, subject: dict, recorded_date: str, upload_date: str, rec_id: str, page_no: int, total_pages: int):
    c.setFont("Helvetica", 8.5)
    c.setFillColor(C_HEADER)
    left = _safe_get(subject, "subject_name", "")
    mid = f"UPLOAD DATE {upload_date}    RECORDED {recorded_date}    ID {rec_id}"
    right = f"Page {page_no} of {total_pages}"

    c.drawString(M_LEFT, PAGE_H - 0.8 * cm, left)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 0.8 * cm, mid)
    c.drawRightString(PAGE_W - M_RIGHT, PAGE_H - 0.8 * cm, right)

    c.setStrokeColor(C_RULE)
    c.setLineWidth(1)
    c.line(M_LEFT, PAGE_H - 1.05 * cm, PAGE_W - M_RIGHT, PAGE_H - 1.05 * cm)


def _draw_footer(c: canvas.Canvas, gen_date: str):
    """No 'POWERED BY QUALISYS'."""
    c.setFont("Helvetica", 7.5)
    c.setFillColor(C_HEADER)
    c.drawRightString(PAGE_W - M_RIGHT, M_BOTTOM - 0.25 * cm, f"PDF GENERATED {gen_date}")


def _draw_circle_letter(c: canvas.Canvas, x: float, y: float, letter: str):
    r = 0.36 * cm
    c.setFillColor(colors.white)
    c.setStrokeColor(C_ACCENT)
    c.setLineWidth(2)
    c.circle(x, y, r, stroke=1, fill=1)
    c.setFillColor(C_ACCENT)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x, y - 3, letter)


def _draw_section_title(c: canvas.Canvas, letter: str, title: str, y_top: float) -> float:
    if letter:
        x_circle = M_LEFT + 0.25 * cm
        y_circle = y_top - 0.2 * cm
        _draw_circle_letter(c, x_circle, y_circle, letter)
        x_text = M_LEFT + 1.0 * cm
    else:
        x_text = M_LEFT

    c.setFillColor(C_TEXT)
    c.setFont("Helvetica", 18)
    c.drawString(x_text, y_top - 0.55 * cm, title)

    c.setStrokeColor(C_RULE)
    c.setLineWidth(1)
    c.line(M_LEFT, y_top - 0.9 * cm, PAGE_W - M_RIGHT, y_top - 0.9 * cm)
    return y_top - 1.4 * cm


def _draw_subheader(c: canvas.Canvas, label: str, y: float) -> float:
    if label:
        c.setFillColor(C_SECTION)
        c.setFont("Helvetica", 10)
        c.drawString(M_LEFT, y, label)
        return y - 0.55 * cm
    return y


def _draw_card(c: canvas.Canvas, x: float, y_top: float, title: str, png_path: Optional[str]):
    if title:
        c.setFillColor(C_SECTION)
        c.setFont("Helvetica", 9)
        c.drawCentredString(x + CARD_W / 2, y_top - 0.38 * cm, title)

    img_y_top = y_top - TITLE_H
    img_y = img_y_top - IMG_H
    c.setStrokeColor(C_RULE)
    c.setLineWidth(1)
    c.rect(x, img_y, CARD_W, IMG_H, stroke=1, fill=0)

    if png_path and os.path.exists(png_path) and title:
        c.drawImage(png_path, x, img_y, width=CARD_W, height=IMG_H,
                    preserveAspectRatio=True, anchor="sw", mask="auto")


def _draw_rom_table(c: canvas.Canvas, y_top: float, rows: List[List[str]]) -> float:
    data = [["", "Max", "Min", "Range"]] + (rows or [["-", "-", "-", "-"]])
    col_widths = [CONTENT_W * 0.40, CONTENT_W * 0.20, CONTENT_W * 0.20, CONTENT_W * 0.20]

    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_HEADER),
        ("TEXTCOLOR", (0, 1), (-1, -1), C_TEXT),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT]),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, C_RULE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, C_RULE),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, C_RULE),
    ]))
    tw, th = tbl.wrap(CONTENT_W, PAGE_H)
    y = y_top - th
    tbl.drawOn(c, M_LEFT, y)
    return y - 0.5 * cm


def _draw_measurements_page(c: canvas.Canvas, subject: dict, recorded_date: str, rec_id: str):
    c.setFillColor(C_TEXT)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(M_LEFT, PAGE_H - 2.1 * cm, f"{_safe_get(subject,'subject_name','')}")

    c.setFillColor(C_HEADER)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(M_LEFT, PAGE_H - 3.1 * cm, "MEASUREMENTS")

    labels = [
        ("RECORDED", recorded_date),
        ("ID", rec_id),
        ("DATE OF BIRTH", _safe_get(subject, "dob", "")),
        ("SEX", _safe_get(subject, "sex", "")),
        ("HEIGHT", f"{(_safe_get(subject,'height_cm',0)/100):.2f} m" if _safe_get(subject,'height_cm',None) else _safe_get(subject,'height_m','')),
        ("BODY MASS", f"{_safe_get(subject,'weight_kg','')} kg (Calculated)"),
    ]
    y = PAGE_H - 4.2 * cm
    for k, v in labels:
        c.setFillColor(C_HEADER)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(M_LEFT, y, k)
        c.setFillColor(C_TEXT)
        c.setFont("Helvetica", 11)
        c.drawString(M_LEFT, y - 0.55 * cm, str(v))
        y -= 1.55 * cm


def _draw_grid_plots_with_rom(
    c: canvas.Canvas,
    letter: str,
    title: str,
    section_label: str,
    plots: List[Tuple[str, str]],
    graphs_dir: str,
    rom_rows: List[List[str]],
):
    """
    Draw plots in 3 columns, multiple rows if needed.
    Then draw ROM table below. (Keeps ROM visible even with 4 plots)
    """
    y = PAGE_H - 2.0 * cm
    y = _draw_section_title(c, letter, title, y_top=y)
    y = _draw_subheader(c, section_label, y)

    x0 = M_LEFT
    row_top = y

    # draw cards
    for i, (plot_title, fname) in enumerate(plots):
        col = i % 3
        row = i // 3
        x = x0 + col * (CARD_W + GAP_X)
        y_top = row_top - row * (CARD_H + GAP_Y)
        png = os.path.join(graphs_dir, fname) if fname else None
        _draw_card(c, x, y_top, plot_title, png)

    nrows = (len(plots) + 2) // 3
    y = row_top - nrows * (CARD_H + GAP_Y) + 0.2 * cm

    c.setStrokeColor(C_RULE)
    c.setLineWidth(1)
    c.line(M_LEFT, y, PAGE_W - M_RIGHT, y)
    y -= 0.6 * cm

    c.setFillColor(C_SECTION)
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W / 2, y, "Range of Motion")
    y -= 0.6 * cm

    _draw_rom_table(c, y, rom_rows)


def build_qualisys_pdf_minimal(
    out_pdf: str,
    subject: dict,
    analysis_date: str,
    graphs_dir: str,
    rom: Dict[str, List[List[str]]],
    *,
    recorded_date: Optional[str] = None,
    upload_date: Optional[str] = None,
    rec_id: str = "1",
) -> None:
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)

    rec_date = recorded_date or _safe_get(subject, "recording_date", str(date.today()))
    up_date = upload_date or analysis_date or str(date.today())
    gen_date = analysis_date or str(date.today())

    c = canvas.Canvas(out_pdf, pagesize=A4)
    total_pages = 4

    # Page 1
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, 1, total_pages)
    _draw_measurements_page(c, subject, rec_date, rec_id)
    _draw_footer(c, gen_date)
    c.showPage()

    # Page 2: Lower
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, 2, total_pages)
    _draw_grid_plots_with_rom(
        c, "L", "Lower Body Kinematics", "LEFT SIDE",
        [
            ("Hip Flexion", "hip_flex_deg.png"),
            ("Knee Flexion", "knee_flex_deg.png"),
            ("Ankle Dorsiflexion (Proxy)", "ankle_dorsi_deg.png"),
        ],
        graphs_dir,
        rom_rows=rom.get("lower", []),
    )
    _draw_footer(c, gen_date)
    c.showPage()

    # Page 3: Upper (now includes WRIST)
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, 3, total_pages)
    _draw_grid_plots_with_rom(
        c, "U", "Upper Body Kinematics", "LEFT SIDE",
        [
            ("Trunk Anterior Tilt wrt Pelvis", "trunk_tilt_deg.png"),
            ("Shoulder Flexion", "shoulder_flex_deg.png"),
            ("Elbow Flexion", "elbow_flex_deg.png"),
            ("Wrist Flexion (Proxy)", "wrist_flex_deg.png"),
            ("", ""), ("", ""),  # keep grid shape tidy (optional)
        ],
        graphs_dir,
        rom_rows=rom.get("upper", []),
    )
    _draw_footer(c, gen_date)
    c.showPage()

    # Page 4: Head
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, 4, total_pages)
    c.setFillColor(C_SECTION)
    c.setFont("Helvetica", 10)
    c.drawString(M_LEFT, PAGE_H - 2.0 * cm, "HEAD")
    _draw_grid_plots_with_rom(
        c, "", "Head Kinematics", "",
        [
            ("Head Flexion (Head-Trunk)", "head_flex_deg.png"),
            ("", ""), ("", ""),
        ],
        graphs_dir,
        rom_rows=rom.get("head", []),
    )
    _draw_footer(c, gen_date)
    c.save()
