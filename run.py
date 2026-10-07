#!/usr/bin/env python3
"""HSK Docx -> Quizlet: tự động hoàn toàn.

  ./hsk login                         # 1 lần: mở trình duyệt thường để đăng nhập + giải xác minh
  ./hsk convert Bai_27.docx   # chỉ tạo file nhập + thư mục hình (không đụng Quizlet)
  ./hsk upload  Bai_27.docx   # chuyển đổi + tạo hình + tạo học phần trên Quizlet
  ./hsk watch                 # chạy nền: thả .docx vào inbox/ là tự lên Quizlet
  ./hsk inspect               # mở Playwright Inspector để sửa selector khi Quizlet đổi giao diện
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):           # tránh lỗi in tiếng Việt / chữ Hán trên Windows console
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent

# Gọi bằng "python3 run.py" (Python hệ thống) -> tự chuyển sang .venv nếu đã cài
_venv_py = REPO / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if _venv_py.exists() and Path(sys.prefix).resolve() != (REPO / ".venv").resolve() \
        and not os.environ.get("HSK_NO_VENV_SWITCH"):
    os.environ["HSK_NO_VENV_SWITCH"] = "1"
    os.execv(str(_venv_py), [str(_venv_py), __file__, *sys.argv[1:]])
sys.path.insert(0, str(REPO))

from hskq.export import write_outputs          # noqa: E402
from hskq.images import build_images           # noqa: E402
from hskq.parser import parse_docx             # noqa: E402

OUT = REPO / "output"
INBOX = REPO / "inbox"
HISTORY = OUT / "history.json"


def set_dirs(cfg: dict):
    """Cho phép đặt inbox/output ở nơi khác, vd. thư mục Windows khi chạy trong WSL: /mnt/c/Users/ban/HSK/inbox"""
    global OUT, INBOX, HISTORY
    if cfg.get("inbox_dir"):
        INBOX = Path(cfg["inbox_dir"]).expanduser()
    if cfg.get("output_dir"):
        OUT = Path(cfg["output_dir"]).expanduser()
    HISTORY = OUT / "history.json"


def to_local_path(f: str) -> Path:
    """Trong WSL/Linux: đổi 'C:\\Users\\ban\\Bai_27.docx' (chép từ Explorer) thành /mnt/c/Users/ban/Bai_27.docx."""
    f = f.strip().strip('"')
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", f)
    if m and os.name != "nt":
        f = f"/mnt/{m.group(1).lower()}/" + m.group(2).replace("\\", "/")
    return Path(f).expanduser().resolve()


def load_config() -> dict:
    cfg_path = REPO / "config.json"
    if not cfg_path.exists():
        shutil.copy(REPO / "config.example.json", cfg_path)
        print("[i] Đã tạo config.json từ config.example.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    return {k: v for k, v in cfg.items() if not k.startswith("_")}


def load_history() -> dict:
    return json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {}


def save_history(h: dict):
    OUT.mkdir(exist_ok=True)
    HISTORY.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")


def make_title(lesson, cfg) -> str:
    tpl = cfg.get("title_template", "Lesson {num} - Bài {num} {title} - HSK 2 Classical")
    return " ".join(tpl.format(num=lesson.number, title=lesson.title).split())


def convert(path: Path, cfg: dict, images: bool = True, refresh: bool = False):
    lesson = parse_docx(path, include_related=cfg.get("include_related", True))
    if not lesson.cards:
        raise RuntimeError(f"{path.name}: không tìm thấy bảng từ vựng")
    lesson_dir = OUT / lesson.slug
    print(f"[*] {path.name}: {len(lesson.cards)} thẻ  ->  {lesson_dir}")
    if images and cfg.get("images_enabled", True):
        build_images(lesson, lesson_dir, cfg, REPO, refresh=refresh)
    write_outputs(lesson, lesson_dir)
    return lesson, lesson_dir


def upload(paths: list[Path], cfg: dict, args) -> list[tuple[Path, bool]]:
    from hskq.quizlet import QuizletBot
    hist = load_history()
    results = []
    with QuizletBot(REPO, cfg).open(headless=args.headless or None) as bot:
        for path in paths:
            try:
                lesson, lesson_dir = convert(path, cfg, images=not args.no_images,
                                             refresh=args.refresh_images)
                if lesson.slug in hist and not args.force:
                    print(f"   [=] {lesson.slug} đã có trên Quizlet: {hist[lesson.slug]['url']} "
                          f"(thêm --force để tạo lại)")
                    results.append((path, True))
                    continue
                title = make_title(lesson, cfg)
                print(f"   Tiêu đề: {title}")
                url = bot.create_set(lesson, title, lesson_dir,
                                     with_images=not args.no_images and cfg.get("upload_images", True),
                                     assist=args.assist)
                (lesson_dir / "quizlet_url.txt").write_text(url + "\n", encoding="utf-8")
                hist[lesson.slug] = {"url": url, "title": title, "cards": len(lesson.cards),
                                     "source": path.name, "time": datetime.now().isoformat(timespec="seconds")}
                save_history(hist)
                results.append((path, True))
            except Exception as e:
                print(f"[x] {path.name}: {e}")
                traceback.print_exc(limit=2)
                results.append((path, False))
    return results


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
            st.flush()

    def flush(self):
        for st in self.streams:
            st.flush()


def watch(cfg: dict, args):
    INBOX.mkdir(exist_ok=True)
    (INBOX / "done").mkdir(exist_ok=True)
    (INBOX / "failed").mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    log = open(OUT / "run.log", "a", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log)
    sys.stderr = Tee(sys.__stderr__, log)
    interval = int(cfg.get("watch_interval_sec", 10))
    print(f"[watch] {datetime.now():%Y-%m-%d %H:%M} – theo dõi {INBOX} (mỗi {interval}s). Ctrl+C để dừng.")
    while True:
        files = sorted(f for f in INBOX.glob("*.docx") if not f.name.startswith("~$"))
        if files:
            time.sleep(2)  # chờ file chép xong
            for path, ok in upload(files, cfg, args):
                dest = INBOX / ("done" if ok else "failed") / path.name
                if dest.exists():
                    dest = dest.with_name(f"{path.stem}_{datetime.now():%H%M%S}{path.suffix}")
                shutil.move(str(path), dest)
                print(f"[watch] {path.name} -> {dest.parent.name}/")
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["login", "convert", "upload", "watch", "inspect"])
    ap.add_argument("files", nargs="*", help="file .docx")
    ap.add_argument("--no-images", action="store_true", help="không tạo / không tải hình")
    ap.add_argument("--refresh-images", action="store_true", help="tạo lại toàn bộ hình")
    ap.add_argument("--force", action="store_true", help="tạo lại học phần dù đã tạo trước đó")
    ap.add_argument("--assist", action="store_true", help="khi lỗi, dừng để bạn làm tiếp bằng tay")
    ap.add_argument("--headless", action="store_true", help="chạy ẩn trình duyệt")
    args = ap.parse_args()
    cfg = load_config()
    set_dirs(cfg)

    if args.command in ("convert", "upload") and not args.files:
        ap.error("cần ít nhất một file .docx")
    paths = [to_local_path(f) for f in args.files]

    if args.command == "convert":
        for p in paths:
            convert(p, cfg, images=not args.no_images, refresh=args.refresh_images)
    elif args.command == "upload":
        res = upload(paths, cfg, args)
        sys.exit(0 if all(ok for _, ok in res) else 1)
    elif args.command == "watch":
        watch(cfg, args)
    else:
        from hskq.quizlet import QuizletBot, login_plain
        if args.command == "login":
            login_plain(REPO, cfg)
        else:
            with QuizletBot(REPO, cfg).open(headless=False) as bot:
                bot.inspect()


if __name__ == "__main__":
    main()
