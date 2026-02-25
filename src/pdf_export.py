from pathlib import Path
from datetime import datetime
from typing import Callable
from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4


def generate_pdf(
    image_paths: list[str],
    output_path: str | Path,
    page_mode: str = "default",
    progress_callback: Callable[[int, int], bool] | None = None,
) -> Path:
    """
    Generate a PDF from a list of image paths.

    page_mode:
        "default" — each page size matches the image (original behaviour).
        "a4"      — each page is A4; images are scaled to fit.

    progress_callback:
        Optional callable(current_index, total) -> bool.
        Return False to cancel.
    """
    output_path = Path(output_path)
    if page_mode == "a4":
        return _generate_pdf_a4(image_paths, output_path, progress_callback)
    return _generate_pdf_default(image_paths, output_path, progress_callback)


def _generate_pdf_default(image_paths: list[str], output_path: Path,
                          progress_callback: Callable[[int, int], bool] | None = None) -> Path:
    """Original behaviour: page size = widest image \u00d7 current image height."""
    # First pass: find maximum width
    max_width = 0
    sizes = []
    total = len(image_paths)

    for p in image_paths:
        try:
            with PILImage.open(p) as img:
                w, h = img.size
                sizes.append((p, w, h))
                max_width = max(max_width, w)
        except Exception:
            continue

    c = canvas.Canvas(str(output_path))

    for idx, (img_path, w, h) in enumerate(sizes):
        if progress_callback and not progress_callback(idx, len(sizes)):
            c.save()
            return output_path

        # Page size = widest image x current image height
        c.setPageSize((max_width, h))

        # Paint black background
        c.setFillColor(black)
        c.rect(0, 0, max_width, h, stroke=0, fill=1)

        # Center image horizontally
        x = (max_width - w) / 2

        # Draw image (no scaling)
        c.drawImage(img_path, x, 0, width=w, height=h, mask="auto")

        if idx < len(sizes) - 1:
            c.showPage()

    if progress_callback:
        progress_callback(len(sizes), len(sizes))
    c.save()
    return output_path


def _generate_pdf_a4(image_paths: list[str], output_path: Path,
                     progress_callback: Callable[[int, int], bool] | None = None) -> Path:
    """A4 mode: each page is A4, image scaled to fit, centred on black."""
    a4_w, a4_h = A4  # 595.28 \u00d7 841.89 points
    total = len(image_paths)

    c = canvas.Canvas(str(output_path), pagesize=A4)

    drawn = 0
    for idx, img_path in enumerate(image_paths):
        if progress_callback and not progress_callback(idx, total):
            c.save()
            return output_path

        try:
            with PILImage.open(img_path) as img:
                w, h = img.size
        except Exception:
            continue

        # Black background
        c.setFillColor(black)
        c.rect(0, 0, a4_w, a4_h, stroke=0, fill=1)

        # Scale image to fit within A4 while keeping aspect ratio
        scale = min(a4_w / w, a4_h / h)
        draw_w = w * scale
        draw_h = h * scale

        # Centre on page
        x = (a4_w - draw_w) / 2
        y = (a4_h - draw_h) / 2

        c.drawImage(img_path, x, y, width=draw_w, height=draw_h, mask="auto")
        drawn += 1

        if idx < len(image_paths) - 1:
            c.showPage()

    if progress_callback:
        progress_callback(total, total)
    c.save()
    return output_path


def auto_filename() -> str:
    return f"AshAlbum_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"
