#!/usr/bin/env python3
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

missing = []
for lib in ("cairosvg", "lxml", "PIL"):
    try:
        __import__("Pillow" if lib == "PIL" else lib)
    except ImportError:
        missing.append("pillow" if lib == "PIL" else lib)

if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

import cairosvg  # noqa: E402
from lxml import etree  # type: ignore # noqa: E402
from PIL import Image  # noqa: E402


def only_svg_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    
    return text


def export_map(
    svg_path: Path,
    json_path: Path,
    out_path: Path,
    width=4096,
    height=2048,
    quality=95,
    keep_alpha=True,
):
    print("start export map")
    svg_text = only_svg_text(svg_path)
    root = etree.fromstring(svg_text.encode("utf-8"))
    print("map loaded")

    colors = json.loads(json_path.read_text(encoding="utf-8"))
    print("colors loaded")
    regions = colors.get("regions", {})

    for el in root.iter():
        el_id = el.get("id")
        if el_id and el_id in regions:
            el.set("fill", regions[el_id])

    svg_bytes = etree.tostring(root, encoding="utf-8")
    print("render to bitmap")
    png_buffer = BytesIO()
    cairosvg.svg2png(
        bytestring=svg_bytes,
        write_to=png_buffer,
        output_width=width,
        output_height=height,
        background_color=None if keep_alpha else "white",
    )

    png_buffer.seek(0)
    if keep_alpha:
        Image.open(png_buffer).save(out_path, format="PNG", optimize=True)
    else:
        img = Image.open(png_buffer).convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        bg.save(out_path, "JPEG", quality=quality, optimize=True)

    print(f"Done: {out_path}")


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: script.py <map.svg> <colors.json> [--out out.png] "
            "[--width 4096] [--height 2048] [--quality 95] [--jpeg]"
        )
        sys.exit(1)

    svg, jsn = Path(sys.argv[1]), Path(sys.argv[2])
    out = Path("world_map.png")
    width, height, quality = 4096, 2048, 95
    keep_alpha = True

    args = sys.argv[3:]
    for i, a in enumerate(args):
        if a == "--out" and i + 1 < len(args):
            out = Path(args[i + 1])
        elif a == "--width" and i + 1 < len(args):
            width = int(args[i + 1])
        elif a == "--height" and i + 1 < len(args):
            height = int(args[i + 1])
        elif a == "--quality" and i + 1 < len(args):
            quality = int(args[i + 1])
        elif a == "--jpeg":
            keep_alpha = False

    export_map(svg, jsn, out, width, height, quality, keep_alpha)


if __name__ == "__main__":
    main()
