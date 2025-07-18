import xml.etree.ElementTree as etree

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor


class ConstInlineProcessor(InlineProcessor):
    RE = r"!const\[(.*?)\]"

    def __init__(self, pattern, constants, md):
        super().__init__(pattern, md)
        self.constants = constants

    def handleMatch(self, m, data):
        key = m.group(1).strip()
        val = self.constants.get(key, f"<missing const: {key}>")
        el = etree.Element("span")
        el.text = val
        return el, m.start(0), m.end(0)


class ConstExtension(Extension):
    def __init__(self, **kwargs):
        self.config = {
            "constants": [{}, "Dictionary of constants"],
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        constants = self.getConfig("constants")
        pattern = ConstInlineProcessor.RE
        md.inlinePatterns.register(
            ConstInlineProcessor(pattern, constants, md), "const", 0
        )
