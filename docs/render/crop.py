"""Crop the raw renders to the object (plus a margin) and write the README images."""
import os
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "images")
BG = (243, 241, 236)
for view, width in (("open", 1600), ("closed", 1200), ("back", 1200)):
    raw = Image.open(os.path.join(IMG, f"render_{view}_raw.png")).convert("RGB")
    diff = ImageChops.difference(raw, Image.new("RGB", raw.size, BG)).convert("L").point(lambda v: 255 if v > 6 else 0)
    x0, y0, x1, y1 = diff.getbbox()
    m = int(0.06 * max(x1 - x0, y1 - y0))
    box = (max(0, x0 - m), max(0, y0 - m), min(raw.width, x1 + m), min(raw.height, y1 + m))
    out = raw.crop(box)
    out = out.resize((width, round(out.height * width / out.width)), Image.LANCZOS)
    out.save(os.path.join(IMG, f"render_{view}.png"), optimize=True)
    os.remove(os.path.join(IMG, f"render_{view}_raw.png"))
    print(view, out.size)
