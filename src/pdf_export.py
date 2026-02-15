from pathlib import Path
from datetime import datetime
from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black


def generate_pdf(image_paths: list[str], output_path: str | Path) -> Path:
    output_path = Path(output_path)

    # First pass: find maximum width
    max_width = 0
    sizes = []

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

    c.save()
    return output_path


def auto_filename() -> str:
    return f"AshAlbum_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"
