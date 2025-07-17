import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from markdown import Markdown

from templates import templates

from .extensions import (
    ButtonExtension,
    ConstExtension,
    FolderTreeExtension,
    ImgBlockExtension,
    SingleImgExtension,
    SmallTextExtension,
    StripCommentsExtension,
    WikiLinkExtension,
)

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
WIKI_DIR = BASE_DIR / "wiki"
CONSTANTS_PATH = WIKI_DIR / "constants.json"


def load_constants() -> dict[str, str]:
    try:
        with open(CONSTANTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    except FileNotFoundError:
        logging.warning(f"Constants file not found: {CONSTANTS_PATH}")
        return {}

    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in constants file: {e}")
        return {}


CONSTANTS = load_constants()


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
            "tables",  # Markdown-таблицы
            "meta",  # Заголовки-мета в начале файла (например, автор, дата)
            "toc",  # Автоматическое оглавление по заголовкам
            "admonition",  # Поддержка блоков с предупреждениями, заметками и пр.
            "footnotes",  # Сноски
            "smarty",  # Типографические ковычки
            "nl2br",  # Превращает одиночные \n в <br />
            WikiLinkExtension(),  # Поддержка [[url|name]] для вики-стилей
            ConstExtension(constants=CONSTANTS),  # Константы для замены
            ImgBlockExtension(),  # Для блоков с картинками и текстом
            SingleImgExtension(),  # Макрос для картинок
            ButtonExtension(),  # Работа с кнопками и их оформлением
            StripCommentsExtension(),  # В пизду комментарии, так же стрипает весь текст
            FolderTreeExtension(),  # Для создания красивых деревьев
            SmallTextExtension(),  # Маленький текст
        ],
    )
    rendered_html = md.convert(content)
    meta = getattr(md, "Meta", {})
    background_url = (
        meta.get("background", [None])[0] or "/static/images/wallpaper.jpeg"
    )
    title = meta.get("title", [str(page)])[0] if meta else str(page)

    return templates.TemplateResponse(
        "wiki_template.html",
        {
            "request": request,
            "content": rendered_html,
            "title": title,
            "meta": meta,
            "background_url": background_url,
        },
    )
