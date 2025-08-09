#!/usr/bin/env python3
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from zoneinfo import ZoneInfo

META_LINE = re.compile(r"^[A-Za-z][A-Za-z \-]*:\s?.*$")
HEADING_LINE = re.compile(r"^(#{1,6})\s*(.+?)\s*$")

META_ORDER = ["Title", "Author", "Date", "Background"]

MONTHS = {
    1: "Января",
    2: "Февраля",
    3: "Марта",
    4: "Апреля",
    5: "Мая",
    6: "Июня",
    7: "Июля",
    8: "Августа",
    9: "Сентября",
    10: "Октября",
    11: "Ноября",
    12: "Декабря",
}


def today_ru(tz: str = "Europe/Amsterdam") -> str:
    now = datetime.now(ZoneInfo(tz))
    return f"{now.day} {MONTHS[now.month]} {now.year} г."


# region meta helpers


def find_meta_block(lines: List[str]) -> int:
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1
            break

        if not META_LINE.match(line):
            break

        i += 1

    return i


def parse_meta(meta_lines: List[str]) -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    for ln in meta_lines:
        s = ln.strip()
        if not s or not META_LINE.match(ln):
            continue

        k, _, v = ln.partition(":")
        items.append((k.strip(), v.lstrip()))

    return items


def normalize_keys_capitalization(key: str) -> str:
    lower = key.lower()
    for wanted in META_ORDER:
        if wanted.lower() == lower:
            return wanted

    return key[:1].upper() + key[1:]


def replace_symbols_simple(s: str) -> str:
    # «» -> ", — -> --
    return s.replace("«", '"').replace("»", '"').replace("—", "--")


def normalize_meta_values(items: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for k, v in items:
        if k.strip().lower() != "background":
            v = replace_symbols_simple(v)

        out.append((k, v))

    return out


def rebuild_meta(items: List[Tuple[str, str]]) -> str:
    last_map: dict[str, Tuple[str, str]] = {}
    for k, v in items:
        last_map[k.lower()] = (k, v)

    out: List[Tuple[str, str]] = []
    for wanted in META_ORDER:
        pair = last_map.pop(wanted.lower(), None)
        if pair:
            out.append((wanted, pair[1]))

    for _, (k, v) in sorted(last_map.items(), key=lambda kv: kv[0]):
        out.append((normalize_keys_capitalization(k), v))

    if not out:
        return ""

    return "\n".join(f"{k}: {v}".rstrip() for k, v in out) + "\n\n"


def update_date_in_items(
    items: List[Tuple[str, str]], new_date: str
) -> List[Tuple[str, str]]:
    if not any(k.strip().lower() == "date" for k, _ in items):
        return items

    updated: List[Tuple[str, str]] = []
    for k, v in items:
        if k.strip().lower() == "date":
            updated.append((normalize_keys_capitalization(k), new_date))

        else:
            updated.append((k, v))

    return updated


# endregion

# region body normalization


def fix_headings(text: str) -> str:
    fixed = []
    prev_blank = True
    for raw in text.splitlines():
        m = HEADING_LINE.match(raw)
        line = raw
        if m:
            hashes, title = m.groups()
            line = f"{hashes} {title.strip()}"
            if not prev_blank:
                fixed.append("")
                prev_blank = True

        fixed.append(line.rstrip())
        prev_blank = line.strip() == ""

    out = "\n".join(fixed)
    if text.endswith("\n") and not out.endswith("\n"):
        out += "\n"

    return out


def collapse_blank_lines(text: str) -> str:
    out = []
    blank = 0
    for ln in text.splitlines():
        if ln.strip() == "":
            blank += 1
            if blank > 1:
                continue

            out.append("")

        else:
            blank = 0
            out.append(ln.rstrip())

    res = "\n".join(out)
    if not res.endswith("\n"):
        res += "\n"

    return res


def replace_symbols_in_body(text: str) -> str:
    out_lines = []
    in_code = False
    for ln in text.splitlines():
        if ln.strip().startswith("```"):
            in_code = not in_code
            out_lines.append(ln)
            continue

        if not in_code:
            ln = replace_symbols_simple(ln)

        out_lines.append(ln)

    res = "\n".join(out_lines)
    if text.endswith("\n") and not res.endswith("\n"):
        res += "\n"

    return res


# endregion

# region orchestrator per-file


def process_markdown(text: str, new_date: str) -> str:
    lines = text.splitlines()
    meta_end = find_meta_block(lines)
    meta_lines = lines[:meta_end]
    body_lines = lines[meta_end:]

    items = parse_meta(meta_lines)

    if items:
        items = normalize_meta_values(items)
        items = update_date_in_items(items, new_date)
        new_meta = rebuild_meta(items)

        body_text = "\n".join(body_lines).lstrip("\n")
        body_text = replace_symbols_in_body(body_text)
        body_text = collapse_blank_lines(fix_headings(body_text))

        result = new_meta + body_text
    else:
        body_text = replace_symbols_in_body(text)
        result = collapse_blank_lines(fix_headings(body_text))

    return result


# endregion


def main():
    changed_list = Path("changed_files.txt")
    if not changed_list.exists():
        print("No changed_files.txt; nothing to do.")
        return

    files = [
        Path(p.strip()) for p in changed_list.read_text().splitlines() if p.strip()
    ]
    if not files:
        print("No markdown files to update.")
        return

    new_date = today_ru()
    touched = 0
    for p in files:
        if not p.is_file() or p.suffix.lower() != ".md":
            continue
        
        orig = p.read_text(encoding="utf-8")
        updated = process_markdown(orig, new_date)
        if updated != orig:
            p.write_text(updated, encoding="utf-8")
            print(f"Updated: {p}")
            touched += 1
    
    print(f"Done. Files changed: {touched}")


if __name__ == "__main__":
    main()
