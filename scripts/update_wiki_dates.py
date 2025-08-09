#!/usr/bin/env python3
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

META_LINE = re.compile(r"^[A-Za-z][A-Za-z \-]*:\s?.*$")

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


def update_meta_date(text: str, new_date: str) -> str:
    lines = text.splitlines()
    n = len(lines)

    meta_end = 0
    while meta_end < n:
        line = lines[meta_end]
        if line.strip() == "":
            meta_end += 1
            break
        if not META_LINE.match(line):
            break
        meta_end += 1

    date_idx = None
    for i in range(meta_end):
        if lines[i].strip().lower().startswith("date:"):
            date_idx = i
            break

    if date_idx is None:
        return text

    new_date_line = f"Date: {new_date}"
    if lines[date_idx].strip() != new_date_line:
        prefix = lines[date_idx][: len(lines[date_idx]) - len(lines[date_idx].lstrip())]
        lines[date_idx] = prefix + new_date_line

    out = "\n".join(lines)
    if text.endswith("\n") and not out.endswith("\n"):
        out += "\n"

    return out


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
    for p in files:
        if not p.is_file():
            continue
        orig = p.read_text(encoding="utf-8")
        updated = update_meta_date(orig, new_date)
        if updated != orig:
            p.write_text(updated, encoding="utf-8")
            print(f"Updated: {p}")


if __name__ == "__main__":
    main()
