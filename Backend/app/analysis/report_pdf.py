from __future__ import annotations

import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle, Image
from reportlab.lib import colors


def _draw_header(c: canvas.Canvas, subject: dict, analysis_date: str) -> None:
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, 28.5 * cm, "Car Seating Comfort Motion Analysis Report")

    c.setFont("Helvetica", 10)
    line1 = f"Subject: {subject['subject_name']}  |  Age: {subject['age_years']} years  |  Sex: {subject['sex']}"
    c.drawString(2 * cm, 27.7 * cm, line1)

    line2 = (
        f"Height: {subject['height_cm'] / 100:.2f} m  |  Weight: {subject['weight_kg']:.1f} kg  |  "
        f"BMI: {subject['bmi']:.1f}"
    )
    c.drawString(2 * cm, 27.1 * cm, line2)

    line3 = (
        f"Recording Date: {subject['recording_date']}  |  Camera Distance: {subject['camera_distance_m']:.2f} m  |  "
        f"Analysis Date: {analysis_date}"
    )
    c.drawString(2 * cm, 26.5 * cm, line3)


def _rom_table(rows, col_widths=None) -> Table:
    """
    rows format:
      [[Parameter, "Max ± std", "Min ± std", "Range ± std"], ...]
    """
    data = [["Parameter", "Max ± std", "Min ± std", "Range ± std"]] + rows
    if col_widths is None:
        col_widths = [7.0 * cm, 4.0 * cm, 4.0 * cm, 4.0 * cm]

    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
            ]
        )
    )
    return tbl


def ensure_space(c: canvas.Canvas, y: float, needed_height: float, page_height: float,
                 top_margin: float, bottom_margin: float) -> float:
    """
    Prevents graphs/tables from being cut off:
    If there isn't enough vertical space left for an item of `needed_height`,
    create a new page and reset y to the top drawing position.
    """
    if y - needed_height < bottom_margin:
        c.showPage()
        y = page_height - top_margin
    return y


def build_pdf(
    out_pdf: str,
    subject: dict,
    analysis_date: str,
    sections: list[dict],
) -> None:
    """
    Qualisys-style PDF builder with automatic pagination guard so graphs never get clipped.

    sections: list of dicts:
      {
        "title": str,
        "graphs": [png_paths...],
        "rom_rows": [[Parameter, Max±std, Min±std, Range±std], ...]
      }
    """
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    c = canvas.Canvas(out_pdf, pagesize=A4)
    page_w, page_h = A4

    # Margins
    left_margin = 2 * cm
    right_margin = 2 * cm
    top_margin = 2 * cm
    bottom_margin = 2 * cm

    # Header on first page
    _draw_header(c, subject, analysis_date)

    # Start below header
    y = 25.5 * cm

    # Fixed image size (matches your earlier styling)
    img_w = page_w - left_margin - right_margin
    img_h = 4.2 * cm
    gap = 0.4 * cm

    for sec in sections:
        # Ensure space for section title
        y = ensure_space(
            c,
            y,
            needed_height=1.2 * cm,
            page_height=page_h,
            top_margin=top_margin,
            bottom_margin=bottom_margin,
        )

        c.setFont("Helvetica-Bold", 12)
        c.drawString(left_margin, y, sec["title"])
        y -= 0.6 * cm

        # Graphs
        for g in sec.get("graphs", []):
            if os.path.exists(g):
                # Ensure space for the full graph BEFORE drawing
                y = ensure_space(
                    c,
                    y,
                    needed_height=img_h + gap,
                    page_height=page_h,
                    top_margin=top_margin,
                    bottom_margin=bottom_margin,
                )

                img = Image(g)
                img.drawHeight = img_h
                img.drawWidth = img_w
                img.drawOn(c, left_margin, y - img_h)
                y -= (img_h + gap)

        # ROM table
        rows = sec.get("rom_rows", [])
        if rows:
            tbl = _rom_table(rows)
            tw, th = tbl.wrap(page_w - left_margin - right_margin, page_h)

            # Ensure space for the full table BEFORE drawing
            y = ensure_space(
                c,
                y,
                needed_height=th + gap,
                page_height=page_h,
                top_margin=top_margin,
                bottom_margin=bottom_margin,
            )

            tbl.drawOn(c, left_margin, y - th)
            y -= (th + gap)

    c.save()
