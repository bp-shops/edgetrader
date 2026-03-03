"""Erstellt das EdgeTrader App-Icon (assets/icon.ico)"""
from PIL import Image, ImageDraw, ImageFont
import os

SIZES = [16, 32, 48, 64, 128, 256]

def create_icon():
    imgs = []
    for size in SIZES:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Hintergrund: Abgerundetes Quadrat (dunkel)
        margin = max(1, size // 16)
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=size // 5,
            fill="#0d0f14",
            outline="#f0b429",
            width=max(1, size // 32)
        )

        # Blitz-Symbol (gelb)
        cx, cy = size / 2, size / 2
        s = size * 0.3  # Skalierung

        bolt = [
            (cx - s * 0.1, cy - s * 0.9),
            (cx + s * 0.4, cy - s * 0.9),
            (cx + s * 0.05, cy - s * 0.1),
            (cx + s * 0.5, cy - s * 0.1),
            (cx - s * 0.15, cy + s * 0.9),
            (cx + s * 0.05, cy + s * 0.1),
            (cx - s * 0.4, cy + s * 0.1),
        ]
        draw.polygon(bolt, fill="#f0b429")

        imgs.append(img)

    out = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
    imgs[0].save(out, format="ICO", sizes=[(s, s) for s in SIZES], append_images=imgs[1:])
    print(f"Icon erstellt: {out}")

if __name__ == "__main__":
    create_icon()
