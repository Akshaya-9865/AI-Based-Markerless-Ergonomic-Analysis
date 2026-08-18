"""
Qualisys-style PDF report generator (Lower Body, Upper Body, Head + ROM),
matching the uploaded reference report layout.

Drop-in usage:
    from app.analysis.report_pdf_qualisys import build_qualisys_pdf

    build_qualisys_pdf(
        out_pdf=...,
        subject=subject_dict,
        analysis_date="YYYY-MM-DD",
        graphs_dir=...,
        rom=rom_dict
    )

Assumptions:
- You already generate PNG graphs into `graphs_dir`.
- This module arranges them into a Qualisys-like multi-panel layout:
  Page 1: Measurements (cover)
  Page 2: Lower Body Kinematics (Pelvis/Hip/Knee/Ankle) + ROM table
  Page 3: Upper Body Kinematics (Thorax/Shoulder/Elbow/Wrist)
  Page 4: Head (Head Flex/Lateral/Rotation) + ROM table
- NO kinetics included (per your requirements).

Expected PNG filenames in graphs_dir (edit GRAPH_MAP if yours differ):
Lower:
  pelvis_anterior_tilt.png (optional)
  hip_flexion.png
  knee_flexion.png
  ankle_dorsiflexion.png
Upper:
  thorax_anterior_tilt_wrt_pelvis.png
  shoulder_flexion.png
  elbow_flexion.png
  wrist_flexion.png
Head:
  head_flexion.png
  head_lateral_flexion.png
  head_rotation.png
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


# -----------------------------
# Customize these to your PNG names
# -----------------------------
GRAPH_MAP = {
    "lower": [
        ("PELVIS", [
            ("Pelvic Anterior Tilt", "pelvis_anterior_tilt.png"),
            ("Pelvic Up Obliquity", "pelvis_up_obliquity.png"),
            ("Pelvic Internal Rotation", "pelvis_internal_rotation.png"),
        ]),
        ("HIP", [
            ("Hip Flexion", "hip_flexion.png"),
            ("Hip Adduction", "hip_adduction.png"),
            ("Hip Internal Rotation", "hip_internal_rotation.png"),
        ]),
        ("KNEE", [
            ("Knee Flexion", "knee_flexion.png"),
            ("Knee Varus", "knee_varus.png"),
            ("Knee Internal Rotation", "knee_internal_rotation.png"),
        ]),
        ("ANKLE", [
            ("Ankle Dorsiflexion", "ankle_dorsiflexion.png"),
            ("Ankle Inversion", "ankle_inversion.png"),
        ]),
    ],
    "upper": [
        ("THORAX", [
            ("Thorax Anterior Tilt wrt Pelvis", "thorax_anterior_tilt_wrt_pelvis.png"),
            ("Thorax Up Obliquity wrt Pelvis", "thorax_up_obliquity_wrt_pelvis.png"),
            ("Thorax Internal Rotation wrt Pelvis", "thorax_internal_rotation_wrt_pelvis.png"),
        ]),
        ("SHOULDER", [
            ("Shoulder Flexion", "shoulder_flexion.png"),
            ("Shoulder Adduction", "shoulder_adduction.png"),
            ("Shoulder Internal Rotation", "shoulder_internal_rotation.png"),
        ]),
        ("ELBOW", [
            ("Elbow Flexion", "elbow_flexion.png"),
            ("Elbow Internal Rotation", "elbow_internal_rotation.png"),
        ]),
        ("WRIST", [
            ("Wrist Flexion", "wrist_flexion.png"),
            ("Wrist Adduction", "wrist_adduction.png"),
        ]),
    ],
    "head": [
        ("HEAD", [
            ("Head Flexion", "head_flexion.png"),
            ("Head Lateral Flexion", "head_lateral_flexion.png"),
            ("Head Rotation", "head_rotation.png"),
        ]),
    ],
}


# -----------------------------
# Layout constants (A4)
# -----------------------------
PAGE_W, PAGE_H = A4
M_LEFT = 1.6 * cm
M_RIGHT = 1.6 * cm
M_TOP = 1.2 * cm
M_BOTTOM = 1.2 * cm

CONTENT_W = PAGE_W - M_LEFT - M_RIGHT

# Chart panel geometry
COLS_3 = 3
GAP_X = 0.6 * cm
GAP_Y = 0.8 * cm

# Each small chart "card"
CARD_W_3 = (CONTENT_W - (COLS_3 - 1) * GAP_X) / COLS_3
CARD_H = 5.1 * cm   # close to Qualisys panels
TITLE_H = 0.55 * cm
IMG_H = CARD_H - TITLE_H

# 2-column row cards (ANKLE has 2 charts)
COLS_2 = 2
CARD_W_2 = (CONTENT_W - (COLS_2 - 1) * GAP_X) / COLS_2

# Colors approximating Qualisys style
C_HEADER = colors.HexColor("#666666")
C_SECTION = colors.HexColor("#6F6F6F")
C_RULE = colors.HexColor("#DDDDDD")
C_LIGHT = colors.HexColor("#F4F4F4")
C_ACCENT = colors.HexColor("#2BB3A5")   # teal-ish circle like Qualisys icon
C_TEXT = colors.HexColor("#222222")


def _safe_get(d: dict, key: str, default=""):
    v = d.get(key, default)
    return default if v is None else v


def _draw_top_meta_bar(c: canvas.Canvas, subject: dict, recorded_date: str, upload_date: str, rec_id: str, page_no: int, total_pages: int):
    """Top thin bar like Qualisys (name + dates + ID + page count)."""
    c.setFont("Helvetica", 8.5)
    c.setFillColor(C_HEADER)
    left = _safe_get(subject, "subject_name", "")
    mid = f"UPLOAD DATE {upload_date}    RECORDED {recorded_date}    ID {rec_id}"
    right = f"Page {page_no} of {total_pages}"

    c.drawString(M_LEFT, PAGE_H - 0.8 * cm, left)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 0.8 * cm, mid)
    c.drawRightString(PAGE_W - M_RIGHT, PAGE_H - 0.8 * cm, right)

    # subtle rule line
    c.setStrokeColor(C_RULE)
    c.setLineWidth(1)
    c.line(M_LEFT, PAGE_H - 1.05 * cm, PAGE_W - M_RIGHT, PAGE_H - 1.05 * cm)


def _draw_footer(c: canvas.Canvas, gen_date: str):
    c.setFont("Helvetica", 7.5)
    c.setFillColor(C_HEADER)
    c.drawString(M_LEFT, M_BOTTOM - 0.25 * cm, "POWERED BY QUALISYS")
    c.drawRightString(PAGE_W - M_RIGHT, M_BOTTOM - 0.25 * cm, f"PDF GENERATED {gen_date}")


def _draw_circle_letter(c: canvas.Canvas, x: float, y: float, letter: str):
    """Teal circle with letter inside (L/U) like reference."""
    r = 0.36 * cm
    c.setFillColor(colors.white)
    c.setStrokeColor(C_ACCENT)
    c.setLineWidth(2)
    c.circle(x, y, r, stroke=1, fill=1)
    c.setFillColor(C_ACCENT)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x, y - 3, letter)


def _draw_section_title(c: canvas.Canvas, letter: str, title: str, y_top: float) -> float:
    """Returns next y after title."""
    if letter:
        x_circle = M_LEFT + 0.25 * cm
        y_circle = y_top - 0.2 * cm
        _draw_circle_letter(c, x_circle, y_circle, letter)
        x_text = M_LEFT + 1.0 * cm
    else:
        x_text = M_LEFT

    c.setFillColor(C_TEXT)
    c.setFont("Helvetica", 18)
    if title:
        c.drawString(x_text, y_top - 0.55 * cm, title)

        # underline
        c.setStrokeColor(C_RULE)
        c.setLineWidth(1)
        c.line(M_LEFT, y_top - 0.9 * cm, PAGE_W - M_RIGHT, y_top - 0.9 * cm)
        return y_top - 1.4 * cm
    return y_top


def _draw_subheader(c: canvas.Canvas, label: str, y: float) -> float:
    c.setFillColor(C_SECTION)
    c.setFont("Helvetica", 10)
    c.drawString(M_LEFT, y, label)
    return y - 0.55 * cm


def _draw_card(c: canvas.Canvas, x: float, y_top: float, w: float, title: str, png_path: Optional[str]):
    """Draw one mini-plot card. y_top is top edge of card."""
    # card title
    c.setFillColor(C_SECTION)
    c.setFont("Helvetica", 9)
    c.drawCentredString(x + w / 2, y_top - 0.38 * cm, title)

    # image frame
    img_y_top = y_top - TITLE_H
    img_y = img_y_top - IMG_H
    c.setStrokeColor(C_RULE)
    c.setLineWidth(1)
    c.rect(x, img_y, w, IMG_H, stroke=1, fill=0)

    if png_path and os.path.exists(png_path):
        # Keep aspect; fit into frame
        c.drawImage(png_path, x, img_y, width=w, height=IMG_H, preserveAspectRatio=True, anchor='sw', mask='auto')


def _draw_rom_table(c: canvas.Canvas, y_top: float, rows: List[List[str]]) -> float:
    """
    rows: [[label, max, min, range], ...]
    """
    data = [["", "Max", "Min", "Range"]] + rows
    table_w = CONTENT_W
    col_widths = [table_w * 0.40, table_w * 0.20, table_w * 0.20, table_w * 0.20]

    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_HEADER),
        ("TEXTCOLOR", (0, 1), (-1, -1), C_TEXT),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT]),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, C_RULE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, C_RULE),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, C_RULE),
    ]))

    tw, th = tbl.wrap(CONTENT_W, PAGE_H)
    y = y_top - th
    tbl.drawOn(c, M_LEFT, y)
    return y - 0.6 * cm


def _draw_measurements_page(c: canvas.Canvas, subject: dict, recorded_date: str, upload_date: str, rec_id: str, version: str, revision: str, built: str):
    # Title block
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

    # Version block at bottom right
    c.setFillColor(C_HEADER)
    c.setFont("Helvetica", 8.5)
    c.drawRightString(PAGE_W - M_RIGHT, 3.2 * cm, f"Version: {version}")
    c.drawRightString(PAGE_W - M_RIGHT, 2.7 * cm, f"Revision: {revision}")
    c.drawRightString(PAGE_W - M_RIGHT, 2.2 * cm, f"Built: {built}")


def _draw_kinematics_page(c: canvas.Canvas, letter: str, title: str, groups: List[Tuple[str, List[Tuple[str, str]]]], graphs_dir: str, rom_rows: Optional[List[List[str]]] = None):
    y = PAGE_H - 2.0 * cm
    y = _draw_section_title(c, letter, title, y_top=y)

    for group_name, items in groups:
        y = _draw_subheader(c, group_name, y)

        cols = 3 if len(items) >= 3 else 2
        card_w = CARD_W_3 if cols == 3 else CARD_W_2

        x0 = M_LEFT
        row_top = y
        for i, (plot_title, fname) in enumerate(items):
            col = i % cols
            row = i // cols
            x = x0 + col * (card_w + GAP_X)
            y_top = row_top - row * (CARD_H + GAP_Y)
            png = os.path.join(graphs_dir, fname)
            _draw_card(c, x, y_top, card_w, plot_title, png)

        nrows = (len(items) + cols - 1) // cols
        y = row_top - nrows * (CARD_H + GAP_Y) + 0.2 * cm

        c.setStrokeColor(C_RULE)
        c.setLineWidth(1)
        c.line(M_LEFT, y, PAGE_W - M_RIGHT, y)
        y -= 0.6 * cm

    if rom_rows:
        c.setFillColor(C_SECTION)
        c.setFont("Helvetica", 9)
        c.drawCentredString(PAGE_W / 2, y, "Range of Motion")
        y -= 0.6 * cm
        _draw_rom_table(c, y, rom_rows)


def build_qualisys_pdf(
    out_pdf: str,
    subject: dict,
    analysis_date: str,
    graphs_dir: str,
    rom: Dict[str, List[List[str]]],
    *,
    recorded_date: Optional[str] = None,
    upload_date: Optional[str] = None,
    rec_id: str = "1",
    version: str = "3.15.1+0000",
    revision: str = "local",
    built: str = "local",
) -> None:
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)

    rec_date = recorded_date or _safe_get(subject, "recording_date", str(date.today()))
    up_date = upload_date or _safe_get(subject, "recording_date", str(date.today()))
    gen_date = analysis_date or str(date.today())

    c = canvas.Canvas(out_pdf, pagesize=A4)
    total_pages = 4

    # Page 1
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, page_no=1, total_pages=total_pages)
    _draw_measurements_page(c, subject, rec_date, up_date, rec_id, version, revision, built)
    _draw_footer(c, gen_date)
    c.showPage()

    # Page 2: Lower
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, page_no=2, total_pages=total_pages)
    _draw_kinematics_page(c, "L", "Lower Body Kinematics", GRAPH_MAP["lower"], graphs_dir, rom_rows=rom.get("lower"))
    _draw_footer(c, gen_date)
    c.showPage()

    # Page 3: Upper
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, page_no=3, total_pages=total_pages)
    _draw_kinematics_page(c, "U", "Upper Body Kinematics", GRAPH_MAP["upper"], graphs_dir, rom_rows=rom.get("upper"))
    _draw_footer(c, gen_date)
    c.showPage()

    # Page 4: Head + ROM
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, page_no=4, total_pages=total_pages)
    # "HEAD" label
    c.setFillColor(C_SECTION)
    c.setFont("Helvetica", 10)
    c.drawString(M_LEFT, PAGE_H - 2.0 * cm, "HEAD")
    _draw_kinematics_page(c, "", "", GRAPH_MAP["head"], graphs_dir, rom_rows=rom.get("upper_head"))
    _draw_footer(c, gen_date)

    c.save()
