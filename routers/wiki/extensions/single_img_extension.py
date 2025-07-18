import re
from xml.etree import ElementTree as etree

from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension


class SingleImgBlockProcessor(BlockProcessor):
    RE = re.compile(
        r"^!img\[\s*(?P<url>[^\|\]]+)\s*(?:\|\s*(?P<pos>left|right|middle)?\s*)?(?:\|\s*(?P<width>\d{1,3}))?\s*\]$",
        re.IGNORECASE,
    )

    def test(self, parent, block):
        return bool(self.RE.match(block.strip()))

    def run(self, parent, blocks):
        block = blocks.pop(0).strip()
        match = self.RE.match(block)
        if not match:
            return

        url = match.group("url").strip()
        pos = (match.group("pos") or "middle").lower()
        width = int(match.group("width") or 100)
        width = max(10, min(width, 100))

        wrapper = etree.SubElement(parent, "div")
        wrapper.set("class", f"img-side {pos}")

        img = etree.SubElement(wrapper, "img")
        img.set("src", url)
        img.set("alt", "")
        img.set("style", f"max-width: {width}%;")


class SingleImgExtension(Extension):
    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            SingleImgBlockProcessor(md.parser), "imgsingle", 100
        )
