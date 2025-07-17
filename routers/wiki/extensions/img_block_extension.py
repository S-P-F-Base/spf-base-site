import re
from xml.etree import ElementTree as etree

from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension


class ImgBlockProcessor(BlockProcessor):
    RE = re.compile(
        r"^!imgblock\[(.+?)\|(\s*left\s*|\s*right\s*|\s*middle\s*)(?:\|(\d{1,3}))?\]\s*$",
        re.IGNORECASE,
    )

    def test(self, parent, block):
        return bool(self.RE.match(block.split("\n", 1)[0]))

    def run(self, parent, blocks):
        raw = blocks.pop(0)
        lines = raw.splitlines()

        match = self.RE.match(lines[0])
        if not match:
            return

        url = match.group(1).strip()
        pos = match.group(2).strip().lower()
        max_width = match.group(3)
        if max_width is None:
            w = 40
        else:
            w = max(10, min(int(max_width), 100))

        content_lines = []
        for line in lines[1:]:
            if line.strip().lower() == "!endimgblock":
                break
            content_lines.append(line)

        content = "\n".join(content_lines).strip()

        wrapper = etree.SubElement(parent, "div")
        wrapper.set("class", f"img-side {pos}")

        img = etree.SubElement(wrapper, "img")
        img.set("src", url)
        img.set("alt", "")
        img.set("style", f"max-width: {w}%;")

        content_div = etree.SubElement(wrapper, "div")
        content_div.set("class", "content")
        content_div.text = content


class ImgBlockExtension(Extension):
    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            ImgBlockProcessor(md.parser), "imgblock", 100
        )
