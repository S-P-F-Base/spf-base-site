import re

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


class TableImgPreprocessor(Preprocessor):
    RE = re.compile(
        r"!tblimg\[\s*(?P<url>[^\|\]]+)\s*(?:\|\s*(?P<width>\d{1,3}))?\s*\]",
        re.IGNORECASE,
    )

    def run(self, lines):
        new_lines = []
        for line in lines:
            if "|" in line:

                def repl(m):
                    url = m.group("url").strip()
                    width = int(m.group("width") or 100)
                    width = max(10, min(width, 100))

                    return f'<img src="{url}" alt="" style="max-width:{width}%">'

                line = self.RE.sub(repl, line)
            new_lines.append(line)
        return new_lines


class TableImgExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(TableImgPreprocessor(), "tableimg", 20)
