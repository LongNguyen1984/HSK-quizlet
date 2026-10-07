"""Xuất thẻ ra file Import của Quizlet, CSV và JSON."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .parser import Lesson

TERM_SEP = "\t"     # Quizlet: "Giữa thuật ngữ và định nghĩa" = Tab
CARD_SEP = "###"    # Quizlet: "Giữa các thẻ" = Tùy chỉnh "###"


def import_text(lesson: Lesson) -> str:
    return f"\n{CARD_SEP}\n".join(f"{c.term}{TERM_SEP}{c.definition}" for c in lesson.cards)


def write_outputs(lesson: Lesson, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "txt": out_dir / "quizlet_import.txt",
        "csv": out_dir / "cards.csv",
        "json": out_dir / "cards.json",
    }
    paths["txt"].write_text(import_text(lesson), encoding="utf-8")
    with paths["csv"].open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["index", "term", "definition", "image"])
        for c in lesson.cards:
            w.writerow([c.index, c.term, c.definition, c.image])
    paths["json"].write_text(json.dumps({
        "source": lesson.source, "number": lesson.number, "title": lesson.title,
        "cards": [c.to_dict() for c in lesson.cards],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths
