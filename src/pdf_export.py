"""
Ash Album — PDF generation using ReportLab.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_pdf(image_paths: list[str], output_path: str | Path) -> Path:
    """
    Create a PDF where each image occupies a separate A4 page,
    centred with its aspect ratio preserved.
    """
    output_path = Path(output_path)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    page_w, page_h = A4
    margin = 36  # 0.5 inch

    usable_w = page_w - 2 * margin
    usable_h = page_h - 2 * margin

    for idx, img_path in enumerate(image_paths):
        try:
            with PILImage.open(img_path) as img:
                img_w, img_h = img.size
        except Exception:
            continue

        scale = min(usable_w / img_w, usable_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        x = margin + (usable_w - draw_w) / 2
        y = margin + (usable_h - draw_h) / 2

        c.drawImage(
            img_path, x, y, draw_w, draw_h,
            preserveAspectRatio=True, mask="auto",
        )

        if idx < len(image_paths) - 1:
            c.showPage()

    c.save()
    return output_path


def auto_filename() -> str:
    """Generate timestamped default filename."""
    return f"AshAlbum_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"
