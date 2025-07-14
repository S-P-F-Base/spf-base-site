import re
import urllib.parse
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markdown import Markdown

router = APIRouter()
templates = Jinja2Templates(directory="templates")

BASE_DIR = Path(__file__).resolve().parents[2]
WIKI_DIR = BASE_DIR / "wiki"


def preprocess_wikilinks(md_text: str) -> str:
    wikilink_pattern = re.compile(r"\[\[([^\|\]]+)\|([^\]]+)\]\]")
    button_pattern = re.compile(r"!btn\[(.*?)\|(.*?)\]")

    def wikilink_replacer(match):
        path = match.group(1).strip()
        text = match.group(2).strip()
        url_path = urllib.parse.quote(path)
        return f"[{text}]({url_path})"

    def button_block_replacer(match):
        url = match.group(1).strip()
        label = match.group(2).strip()
        return f'__BTN__<a href="{url}">{label}</a>__BTN__'

    md_text = button_pattern.sub(button_block_replacer, md_text)

    md_text = re.sub(
        r"(?:__BTN__(<a .*?</a>)__BTN__\s*)+",
        lambda m: f'<nav class="links-list">{"".join(re.findall(r"<a .*?</a>", m.group(0)))}</nav>',
        md_text,
    )

    md_text = wikilink_pattern.sub(wikilink_replacer, md_text)

    return md_text


@router.get("/wiki/{page:path}", response_class=HTMLResponse)
def wiki_page(request: Request, page: Path):
    md_path = WIKI_DIR / page
    if md_path.is_dir() or str(page).endswith("/"):
        md_path = md_path / "index.md"
    else:
        md_path = md_path.with_suffix(".md")

    if not md_path.resolve().is_relative_to(WIKI_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Invalid path")

    try:
        content = md_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Page not found")

    md = Markdown(
        extensions=[
            "fenced_code",  # Блоки кода через тройные кавычки (```), как на GitHub
            "nl2br",  # Превращает одиночные \n в <br />
            "tables",  # Markdown-таблицы
            "meta",  # Заголовки-мета в начале файла (например, автор, дата)
            "wikilinks",  # Поддержка [[WikiLinks]] для вики-стилей
            "toc",  # 	Автоматическое оглавление по заголовкам
        ],
        extension_configs={
            "wikilinks": {
                "base_url": "/wiki/",
                "end_url": "",
                "html_class": "wikilink",
            }
        },
    )
    content = preprocess_wikilinks(content)
    rendered_html = md.convert(content)
    meta = getattr(md, "Meta", {})

    title = meta.get("title", [str(page)])[0] if meta else str(page)

    return templates.TemplateResponse(
        "wiki_template.html",
        {
            "request": request,
            "content": rendered_html,
            "title": title,
            "meta": meta,
        },
    )
