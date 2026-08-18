
"""
Qualisys-like minimal report with:
- NO extra empty boxes
- NO Date of Birth field
- Weight and BMI shown as separate lines
- Adaptive plot layout (3-up for 3 plots, 2x2 for 4 plots, full-width for 1 plot)
- ROM table replaces any 'nan' with 'N/A'
- No "Powered by Qualisys"

Expected PNG names in graphs_dir (from pipeline):
- hip_flex_deg.png
- knee_flex_deg.png
- ankle_dorsi_deg.png
- trunk_tilt_deg.png
- shoulder_flex_deg.png
- elbow_flex_deg.png
- wrist_flex_deg.png
- head_flex_deg.png
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
M_TOP = 1.1 * cm

CONTENT_W = PAGE_W - M_LEFT - M_RIGHT

C_HEADER = colors.HexColor("#666666")
C_RULE = colors.HexColor("#DDDDDD")
C_LIGHT = colors.HexColor("#F4F4F4")
C_ACCENT = colors.HexColor("#2BB3A5")
C_TEXT = colors.HexColor("#222222")
C_SECTION = colors.HexColor("#6F6F6F")


def _safe_get(d: dict, key: str, default=""):
    v = d.get(key, default)
    return default if v is None else v


def _fmt_nan(s: str) -> str:
    # Replace 'nan' tokens commonly produced by formatting
    if s is None:
        return "N/A"
    ss = str(s)
    if "nan" in ss.lower():
        return "N/A"
    return ss


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


def _draw_rom_table(c: canvas.Canvas, y_top: float, rows: List[List[str]]) -> float:
    # sanitize any nan text
    clean_rows = []
    for r in rows or []:
        clean_rows.append([_fmt_nan(x) for x in r])

    data = [["", "Max", "Min", "Range"]] + (clean_rows or [["-", "-", "-", "-"]])
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


def _draw_measurements_page(c: canvas.Canvas, subject: dict, recorded_date: str, analysis_date: str, rec_id: str):
    # Simple text layout, no extra boxes.
    name = _safe_get(subject, "subject_name", "")
    age = _safe_get(subject, "age_years", _safe_get(subject, "age", ""))
    sex = _safe_get(subject, "sex", "")
    height_cm = _safe_get(subject, "height_cm", "")
    weight_kg = _safe_get(subject, "weight_kg", "")
    bmi = _safe_get(subject, "bmi", "")

    try:
        height_m = float(height_cm) / 100.0 if height_cm != "" else ""
    except Exception:
        height_m = ""

    cam_dist = _safe_get(subject, "camera_distance_m", "")
    scale = _safe_get(subject, "scale_m_per_px", "")

    c.setFillColor(C_TEXT)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(M_LEFT, PAGE_H - 2.1 * cm, name)

    c.setFillColor(C_HEADER)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(M_LEFT, PAGE_H - 3.0 * cm, "MEASUREMENTS")

    y = PAGE_H - 3.8 * cm
    line_h = 0.65 * cm

    def row(label, value):
        nonlocal y
        c.setFillColor(C_HEADER)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(M_LEFT, y, label)
        c.setFillColor(C_TEXT)
        c.setFont("Helvetica", 11)
        c.drawString(M_LEFT + 4.2 * cm, y, str(_fmt_nan(value)))
        y -= line_h

    row("Recorded Date", recorded_date)
    row("Analysis Date", analysis_date)
    row("ID", rec_id)
    row("Age (years)", age)
    row("Sex", sex)
    row("Height", (f"{height_m:.2f} m" if isinstance(height_m, float) else _fmt_nan(height_m)))
    row("Weight", (f"{float(weight_kg):.1f} kg" if weight_kg != "" else ""))
    row("BMI", (f"{float(bmi):.1f}" if bmi != "" else ""))
    if cam_dist != "":
        row("Camera Distance", f"{cam_dist} m")
    if scale != "":
        row("Scale (m/px)", scale)


def _draw_image_in_rect(c: canvas.Canvas, img_path: str, x: float, y: float, w: float, h: float):
    c.setStrokeColor(C_RULE)
    c.setLineWidth(1)
    c.rect(x, y, w, h, stroke=1, fill=0)
    if img_path and os.path.exists(img_path):
        c.drawImage(img_path, x, y, width=w, height=h, preserveAspectRatio=True, anchor="c", mask="auto")


def _layout_and_draw_plots(c: canvas.Canvas, graphs_dir: str, plots: List[Tuple[str, str]], y_top: float) -> float:
    """
    Adaptive layout:
    - 1 plot: full width
    - 3 plots: 3 columns
    - 4 plots: 2x2 (bigger plots, no empty boxes)
    """
    # filter out empty filenames
    plots = [(t, f) for (t, f) in plots if f]

    if len(plots) == 1:
        title, fname = plots[0]
        c.setFillColor(C_SECTION)
        c.setFont("Helvetica", 10)
        c.drawString(M_LEFT, y_top, title)
        y_top -= 0.5 * cm
        img_h = 12.5 * cm
        img_y = y_top - img_h
        _draw_image_in_rect(c, os.path.join(graphs_dir, fname), M_LEFT, img_y, CONTENT_W, img_h)
        return img_y - 0.8 * cm

    if len(plots) == 4:
        # 2 columns x 2 rows
        col_w = (CONTENT_W - 0.7 * cm) / 2.0
        row_h = 7.2 * cm
        gap = 0.7 * cm

        start_y = y_top
        for idx, (title, fname) in enumerate(plots):
            r = idx // 2
            col = idx % 2
            x = M_LEFT + col * (col_w + gap)
            top = start_y - r * (row_h + 0.9 * cm)

            c.setFillColor(C_SECTION)
            c.setFont("Helvetica", 9.5)
            c.drawString(x, top, title)

            img_h = row_h - 0.55 * cm
            img_y = top - 0.55 * cm - img_h
            _draw_image_in_rect(c, os.path.join(graphs_dir, fname), x, img_y, col_w, img_h)

        last_row_bottom = start_y - 2 * (row_h + 0.9 * cm) + 0.9 * cm
        return last_row_bottom - 0.3 * cm

    # default: 3 columns row(s)
    col_w = (CONTENT_W - 2 * 0.6 * cm) / 3.0
    row_h = 6.2 * cm
    gap_x = 0.6 * cm
    gap_y = 0.9 * cm

    start_y = y_top
    for idx, (title, fname) in enumerate(plots):
        r = idx // 3
        col = idx % 3
        x = M_LEFT + col * (col_w + gap_x)
        top = start_y - r * (row_h + gap_y)

        c.setFillColor(C_SECTION)
        c.setFont("Helvetica", 9)
        c.drawCentredString(x + col_w / 2, top, title)

        img_h = row_h - 0.55 * cm
        img_y = top - 0.55 * cm - img_h
        _draw_image_in_rect(c, os.path.join(graphs_dir, fname), x, img_y, col_w, img_h)

    nrows = (len(plots) + 2) // 3
    last_bottom = start_y - nrows * (row_h + gap_y) + gap_y
    return last_bottom - 0.2 * cm


def _draw_plots_with_rom(
    c: canvas.Canvas,
    letter: str,
    title: str,
    section_label: str,
    plots: List[Tuple[str, str]],
    graphs_dir: str,
    rom_rows: List[List[str]],
):
    y = PAGE_H - 2.0 * cm
    y = _draw_section_title(c, letter, title, y_top=y)

    if section_label:
        c.setFillColor(C_SECTION)
        c.setFont("Helvetica", 10)
        c.drawString(M_LEFT, y, section_label)
        y -= 0.6 * cm

    y = _layout_and_draw_plots(c, graphs_dir, plots, y_top=y)

    c.setStrokeColor(C_RULE)
    c.setLineWidth(1)
    c.line(M_LEFT, y, PAGE_W - M_RIGHT, y)
    y -= 0.65 * cm

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

    # Page 1: Measurements
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, 1, total_pages)
    _draw_measurements_page(c, subject, rec_date, gen_date, rec_id)
    _draw_footer(c, gen_date)
    c.showPage()

    # Page 2: Lower
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, 2, total_pages)
    _draw_plots_with_rom(
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

    # Page 3: Upper (includes wrist, 2x2 layout)
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, 3, total_pages)
    _draw_plots_with_rom(
        c, "U", "Upper Body Kinematics", "LEFT SIDE",
        [
            ("Trunk Anterior Tilt wrt Pelvis", "trunk_tilt_deg.png"),
            ("Shoulder Flexion", "shoulder_flex_deg.png"),
            ("Elbow Flexion", "elbow_flex_deg.png"),
            ("Wrist Flexion (Proxy)", "wrist_flex_deg.png"),
        ],
        graphs_dir,
        rom_rows=rom.get("upper", []),
    )
    _draw_footer(c, gen_date)
    c.showPage()

    # Page 4: Head (full width)
    _draw_top_meta_bar(c, subject, rec_date, up_date, rec_id, 4, total_pages)
    _draw_plots_with_rom(
        c, "", "Head Kinematics", "HEAD",
        [
            ("Head Flexion (Head-Trunk)", "head_flex_deg.png"),
        ],
        graphs_dir,
        rom_rows=rom.get("head", []),
    )
    _draw_footer(c, gen_date)
    c.save()
