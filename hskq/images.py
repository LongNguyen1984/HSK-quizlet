"""Tạo thư mục hình minh họa cho từng thẻ.

Thứ tự lấy hình cho mỗi từ (cấu hình bằng "image_sources" trong config.json):
  custom    – hình bạn tự bỏ vào images_custom/<Bai_xx>/  (tên file: 05.jpg, 05_片.png hoặc 片.jpg)
  pixabay   – tìm ảnh trên Pixabay (cần API key miễn phí), dùng từ khóa tiếng Việt / tiếng Anh
  openverse – tìm ảnh giấy phép mở trên Openverse (không cần key, chỉ dùng từ khóa tiếng Anh)
  generated – tự vẽ thẻ hình: chữ Hán lớn + pinyin + nghĩa (luôn thành công, dùng cho từ trừu tượng)

Từ khóa nằm trong keywords/<Bai_xx>.csv (tự tạo lần đầu, bạn sửa được):
  keyword_vi = '-'  -> không tìm ảnh online (từ trừu tượng), dùng thẻ tự vẽ
  skip = x          -> thẻ này không có hình
"""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
import sys
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from .parser import Card, Lesson, guess_keyword

UA = {"User-Agent": "hsk-quizlet/1.0 (personal study tool)"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
MAX_SIDE = 1000

CJK_FONTS = [
    "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]
LATIN_FONTS = [
    "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

PALETTE = ["#FDECEC", "#FFF4E0", "#EAF6EC", "#E8F1FB", "#F1ECFB", "#FFF0F6"]
INK = "#1F2A44"
ACCENT = "#C0392B"


def safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s（）()]+', "", s)[:20] or "card"


# ---------------- từ khóa ----------------
def load_keywords(lesson: Lesson, kw_dir: Path) -> Path:
    """Đọc / tạo keywords/<slug>.csv rồi gán lại keyword cho từng thẻ."""
    kw_dir.mkdir(parents=True, exist_ok=True)
    path = kw_dir / f"{lesson.slug}.csv"
    rows = {}
    if path.exists():
        with path.open(encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                rows[r.get("hanzi", "").strip()] = r
    for c in lesson.cards:
        r = rows.get(c.hanzi)
        if r:
            c.keyword = (r.get("keyword_vi") or c.keyword).strip()
            c._kw_en = (r.get("keyword_en") or "").strip()          # type: ignore[attr-defined]
            c._skip = (r.get("skip") or "").strip().lower() in {"1", "x", "yes", "y"}  # type: ignore
        else:
            c._kw_en, c._skip = "", False                           # type: ignore[attr-defined]
    # ghi lại (thêm dòng cho từ mới, giữ nguyên chỉnh sửa cũ)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["index", "hanzi", "keyword_vi", "keyword_en", "skip"])
        for c in lesson.cards:
            w.writerow([c.index, c.hanzi, c.keyword, c._kw_en, "x" if c._skip else ""])  # type: ignore
    return path


# ---------------- nguồn hình ----------------
def _from_custom(c: Card, custom_dir: Path) -> Path | None:
    if not custom_dir.is_dir():
        return None
    for f in sorted(custom_dir.iterdir()):
        if f.suffix.lower() not in IMG_EXT:
            continue
        stem = f.stem
        m = re.match(r"^0*(\d+)(?:[_\-\s].*)?$", stem)
        if (m and int(m.group(1)) == c.index) or stem == c.hanzi or stem == safe_name(c.hanzi):
            return f
    return None


def _download(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=UA, timeout=20)
        if r.ok and r.headers.get("content-type", "").startswith("image"):
            return r.content
    except requests.RequestException:
        pass
    return None


def _from_pixabay(c: Card, key: str) -> tuple[bytes, str] | None:
    if not key:
        return None
    queries = []
    if getattr(c, "_kw_en", ""):
        queries.append((c._kw_en, "en"))                       # type: ignore[attr-defined]
    if c.keyword and c.keyword != "-":
        queries.append((c.keyword, "vi"))
    for q, lang in queries:
        try:
            r = requests.get("https://pixabay.com/api/", params={
                "key": key, "q": q[:100], "lang": lang, "safesearch": "true",
                "per_page": 5, "orientation": "horizontal"}, headers=UA, timeout=20)
            hits = r.json().get("hits", []) if r.ok else []
        except (requests.RequestException, ValueError):
            hits = []
        for h in hits:
            data = _download(h.get("webformatURL", ""))
            if data:
                return data, f"Pixabay: {h.get('pageURL', '')}"
    return None


def _from_openverse(c: Card) -> tuple[bytes, str] | None:
    q = getattr(c, "_kw_en", "")
    if not q:
        return None
    try:
        r = requests.get("https://api.openverse.org/v1/images/", params={
            "q": q, "page_size": 5, "mature": "false",
            "license_type": "all-cc"}, headers=UA, timeout=20)
        results = r.json().get("results", []) if r.ok else []
    except (requests.RequestException, ValueError):
        results = []
    for it in results:
        data = _download(it.get("url", ""))
        if data:
            credit = f"Openverse: {it.get('title','')} – {it.get('creator','')} ({it.get('license','')}) {it.get('foreign_landing_url','')}"
            return data, credit
    return None


def _font(cands: list[str], size: int, override: str = ""):
    for p in ([override] if override else []) + cands:
        if p and Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _display_meaning(c: Card) -> str:
    """Dòng nghĩa đầu tiên (sau dấu →), giữ nguyên phần trong ngoặc."""
    for line in c.meaning.splitlines():
        if "→" in line:
            return line.split("→", 1)[1].strip()
    return guess_keyword(c.meaning)


def _generated(c: Card, font_override: str = "") -> bytes:
    """Thẻ hình tự vẽ: chữ Hán lớn + pinyin + nghĩa, căn giữa theo kích thước thực."""
    W, H, PAD = 900, 600, 70
    img = Image.new("RGB", (W, H), PALETTE[c.index % len(PALETTE)])
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([24, 24, W - 24, H - 24], radius=36, outline=INK, width=4)

    # cỡ chữ Hán: lớn nhất mà vẫn vừa chiều ngang
    size = 230
    while size > 60:
        f_han = _font(CJK_FONTS, size, font_override)
        if d.textlength(c.hanzi, font=f_han) <= W - 2 * PAD:
            break
        size -= 10
    f_pin = _font(LATIN_FONTS, 52)
    f_mean = _font(LATIN_FONTS, 38)

    blocks = [(c.hanzi, f_han, INK, 28)]
    if c.pinyin:
        blocks.append((c.pinyin, f_pin, ACCENT, 18))
    for line in textwrap.wrap(_display_meaning(c), 36)[:2]:
        blocks.append((line, f_mean, INK, 8))

    def bbox(text, font):
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
        return x0, y0, x1 - x0, y1 - y0

    total = sum(bbox(t, f)[3] + gap for t, f, _, gap in blocks) - blocks[-1][3]
    y = (H - total) / 2
    for text, font, fill, gap in blocks:
        x0, y0, w, h = bbox(text, font)
        d.text(((W - w) / 2 - x0, y - y0), text, font=font, fill=fill)
        y += h + gap
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def _to_jpeg(data: bytes) -> bytes:
    im = Image.open(io.BytesIO(data))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return buf.getvalue()


# ---------------- chính ----------------
def build_images(lesson: Lesson, lesson_dir: Path, cfg: dict, repo_dir: Path,
                 refresh: bool = False) -> Path:
    img_dir = lesson_dir / "images"
    if refresh and img_dir.exists():
        shutil.rmtree(img_dir)
    img_dir.mkdir(parents=True, exist_ok=True)

    kw_path = load_keywords(lesson, repo_dir / "keywords")
    custom_dir = repo_dir / "images_custom" / lesson.slug
    sources = cfg.get("image_sources", ["custom", "pixabay", "openverse", "generated"])
    key = cfg.get("pixabay_api_key", "")
    font = cfg.get("font_path", "")

    credits = []
    for c in lesson.cards:
        target = img_dir / f"{c.index:02d}_{safe_name(c.hanzi)}.jpg"
        c.image = str(target.relative_to(lesson_dir)).replace("\\", "/")
        if getattr(c, "_skip", False):
            c.image = ""
            target.unlink(missing_ok=True)
            continue
        if target.exists() and not refresh:
            continue
        data, src = None, ""
        for s in sources:
            if s == "custom":
                f = _from_custom(c, custom_dir)
                if f:
                    data, src = f.read_bytes(), f"custom: {f.name}"
            elif s == "pixabay":
                res = _from_pixabay(c, key)
                if res:
                    data, src = res
            elif s == "openverse":
                res = _from_openverse(c)
                if res:
                    data, src = res
            elif s == "generated":
                data, src = _generated(c, font), "generated"
            if data:
                break
        if not data:
            c.image = ""
            continue
        try:
            target.write_bytes(_to_jpeg(data))
        except Exception as e:  # ảnh hỏng -> dùng thẻ tự vẽ
            print(f"   [!] {c.hanzi}: ảnh lỗi ({e}), dùng thẻ tự vẽ", file=sys.stderr)
            target.write_bytes(_generated(c, font))
            src = "generated"
        credits.append({"index": c.index, "hanzi": c.hanzi, "file": target.name, "source": src})
        print(f"   [img] {c.index:02d} {c.hanzi:<6} <- {src.split(':')[0]}")

    if credits:
        cpath = lesson_dir / "image_credits.json"
        old = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() and not refresh else []
        merged = {x["index"]: x for x in old + credits}
        cpath.write_text(json.dumps(sorted(merged.values(), key=lambda x: x["index"]),
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   Từ khóa hình: {kw_path}")
    return img_dir
