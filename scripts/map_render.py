#!/usr/bin/env python3
"""
convert_map.py - конвертирует world.svg + world.custom.json в JPEG
Пример запуска:
    python3 convert_map.py world.svg world.custom.json --width 8192 --height 4096
"""

import sys
import subprocess
from pathlib import Path
import json

missing = []
for lib in ("cairosvg", "PIL"):
    try:
        __import__(lib if lib != "PIL" else "Pillow")
    except ImportError:
        missing.append("pillow" if lib == "PIL" else lib)
if missing:
    print("download missing dependency:", ", ".join(missing))
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

import cairosvg
from PIL import Image


def export_map(svg_path: Path, json_path: Path, out_path: Path,
               width: int = 4096, height: int = 2048,
               quality: int = 95,) -> None:
    svg_text = svg_path.read_text(encoding="utf-8")
    colors = json.loads(json_path.read_text(encoding="utf-8"))

    for region, color in colors.get("regions", {}).items():
        svg_text = svg_text.replace(f'id="{region}"', f'id="{region}" fill="{color}"')

    tmp_png = out_path.with_suffix(".tmp.png")
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        write_to=tmp_png,
        output_width=width,
        output_height=height
    )

    img = Image.open(tmp_png)
    img.convert("RGB").save(out_path, format="JPEG", quality=quality, optimize=True)
    tmp_png.unlink()


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    svg = Path(sys.argv[1])
    jsn = Path(sys.argv[2])
    out = "world_map.jpeg"
    width = 4096
    height = 2048
    quality = 95

    args = sys.argv[3:]
    for i, a in enumerate(args):
        if a == "--width" and i + 1 < len(args):
            width = int(args[i + 1])
        if a == "--height" and i + 1 < len(args):
            height = int(args[i + 1])
        if a == "--quality" and i + 1 < len(args):
            quality = int(args[i + 1])

    export_map(svg, jsn, out, width=width, height=height, quality=quality)
    print(f"Done: {out}")


if __name__ == "__main__":
    main()