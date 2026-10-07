"""Tự động tạo học phần trên quizlet.com bằng Playwright (trình duyệt thật, phiên đăng nhập được lưu)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import (BrowserContext, Error as PWError, Locator, Page,
                                 TimeoutError as PWTimeout, sync_playwright)

from .export import CARD_SEP, import_text
from .parser import Lesson


class QuizletError(RuntimeError):
    pass


# Giảm dấu hiệu "trình duyệt bị điều khiển" mà hệ thống chống bot hay kiểm tra
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = window.chrome || {runtime: {}};
Object.defineProperty(navigator, 'languages', {get: () => ['vi-VN', 'vi', 'en-US', 'en']});
"""

CHALLENGE_TITLES = re.compile(r"just a moment|attention required|verify|xác minh|access denied|captcha", re.I)


def _need_display():
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise QuizletError("Không có màn hình đồ họa (DISPLAY). Trên WSL cần Windows 11 / WSLg "
                           "(chạy 'wsl --update' trong PowerShell).")


def _browser_executable(cfg: dict) -> str:
    """Đường dẫn trình duyệt để mở THƯỜNG (không qua Playwright) khi đăng nhập."""
    ch = cfg.get("browser_channel", "")
    names = {"chrome": ["google-chrome", "google-chrome-stable", "chrome"],
             "msedge": ["microsoft-edge", "microsoft-edge-stable", "msedge"]}.get(ch, [])
    for n in names:
        if shutil.which(n):
            return shutil.which(n)
    with sync_playwright() as pw:                       # Chromium do Playwright cài
        return pw.chromium.executable_path


def login_plain(repo_dir: Path, cfg: dict):
    """Mở trình duyệt bình thường (không bị điều khiển) để bạn đăng nhập + giải xác minh 'tôi là người'.
    Cookie được lưu vào browser_profile/ và các lần chạy tự động sau dùng lại."""
    _need_display()
    base = cfg.get("quizlet_base_url", "https://quizlet.com").rstrip("/")
    profile = repo_dir / "browser_profile"
    profile.mkdir(exist_ok=True)
    for lock in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        (profile / lock).unlink(missing_ok=True)
    exe = _browser_executable(cfg)
    print(f"[i] Mở trình duyệt: {exe}")
    proc = subprocess.Popen([exe, f"--user-data-dir={profile}", "--no-first-run",
                             "--no-default-browser-check", "--password-store=basic",
                             f"{base}/login"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("\n>>> 1. Đăng nhập Quizlet trong cửa sổ vừa mở (giải ô xác minh nếu có).")
    print(">>> 2. Mở thử https://quizlet.com/create-set để chắc chắn đã vào được.")
    print(">>> 3. ĐÓNG HẲN cửa sổ trình duyệt — chương trình sẽ tự kiểm tra.\n")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
    time.sleep(1)
    with QuizletBot(repo_dir, cfg).open(headless=False) as bot:
        if bot.is_logged_in():
            print("[ok] Đã đăng nhập. Phiên được lưu trong browser_profile/.")
        else:
            print("[!] Chưa thấy đăng nhập. Chạy lại: ./hsk login")


class QuizletBot:
    def __init__(self, repo_dir: Path, cfg: dict):
        self.repo_dir = repo_dir
        self.cfg = cfg
        self.base = cfg.get("quizlet_base_url", "https://quizlet.com").rstrip("/")
        self.sel = json.loads((repo_dir / "quizlet_selectors.json").read_text(encoding="utf-8"))
        self.profile = repo_dir / "browser_profile"
        self._pw = None
        self.ctx: BrowserContext | None = None
        self.page: Page | None = None
        self.debug_dir: Path | None = None
        self._headless = False

    # ---------- trình duyệt ----------
    def open(self, headless: bool | None = None):
        if headless is None:
            headless = bool(self.cfg.get("headless", False))
        self._headless = headless
        if not headless:
            _need_display()
        self._pw = sync_playwright().start()
        kw = dict(user_data_dir=str(self.profile), headless=headless,
                  viewport={"width": 1366, "height": 900}, locale="vi-VN",
                  args=["--disable-blink-features=AutomationControlled", "--password-store=basic"],
                  ignore_default_args=["--enable-automation"])
        channel = self.cfg.get("browser_channel", "")
        if channel:
            kw["channel"] = channel          # "chrome" hoặc "msedge": dùng trình duyệt đã cài trên máy
        try:
            self.ctx = self._pw.chromium.launch_persistent_context(**kw)
        except PWError as e:
            if not channel:
                raise
            print(f"[i] Không mở được '{channel}' ({str(e).splitlines()[0]}). Dùng Chromium của Playwright.")
            kw.pop("channel")
            self.ctx = self._pw.chromium.launch_persistent_context(**kw)
        self.ctx.add_init_script(STEALTH_JS)
        self.ctx.set_default_timeout(int(self.cfg.get("timeout_ms", 15000)))
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        return self

    def close(self):
        try:
            if self.ctx:
                self.ctx.close()
        finally:
            if self._pw:
                self._pw.stop()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # ---------- tiện ích ----------
    def find(self, key: str, scope: Page | Locator | None = None, timeout: int = 8000,
             required: bool = True) -> Locator | None:
        scope = scope or self.page
        deadline = time.time() + timeout / 1000
        while time.time() < deadline:
            for s in self.sel.get(key, []):
                loc = scope.locator(s).first
                try:
                    if loc.count() and loc.is_visible():
                        return loc
                except PWError:
                    continue
            time.sleep(0.3)
        if required:
            raise QuizletError(f"Không tìm thấy phần tử '{key}' trên trang. "
                               f"Sửa quizlet_selectors.json (xem: ./hsk inspect).")
        return None

    def snap(self, name: str):
        if not (self.debug_dir and self.page):
            return
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%H%M%S")
        try:
            self.page.screenshot(path=str(self.debug_dir / f"{stamp}_{name}.png"), full_page=True)
            (self.debug_dir / f"{stamp}_{name}.html").write_text(self.page.content(), encoding="utf-8")
        except PWError:
            pass

    def dismiss_cookies(self):
        loc = self.find("cookie_accept", timeout=2500, required=False)
        if loc:
            try:
                loc.click()
            except PWError:
                pass

    def challenge_present(self) -> bool:
        try:
            if CHALLENGE_TITLES.search(self.page.title() or ""):
                return True
        except PWError:
            return False
        for s in self.sel.get("human_check", []):
            try:
                loc = self.page.locator(s).first
                if loc.count() and loc.is_visible():
                    return True
            except PWError:
                continue
        return False

    def wait_for_human(self, max_wait: int = 300):
        """Nếu trang hiện ô 'xác minh bạn là người', chờ bạn giải trong cửa sổ trình duyệt."""
        if not self.challenge_present():
            return
        self.snap("human_check")
        if self.cfg.get("headless", False) or self._headless:
            raise QuizletError("Quizlet yêu cầu xác minh 'tôi là người'. Chạy lại không có --headless "
                               "để giải, hoặc chạy ./hsk login.")
        print("[!] Quizlet đang yêu cầu xác minh 'tôi là người' — hãy giải trong cửa sổ trình duyệt...")
        deadline = time.time() + max_wait
        while time.time() < deadline:
            time.sleep(2)
            if not self.challenge_present():
                print("    [ok] Đã qua bước xác minh.")
                self.page.wait_for_timeout(1500)
                return
        raise QuizletError("Hết thời gian chờ xác minh 'tôi là người'.")

    def is_logged_in(self) -> bool:
        self.page.goto(f"{self.base}/create-set", wait_until="domcontentloaded")
        self.page.wait_for_timeout(2500)
        self.wait_for_human()
        url = self.page.url
        return not re.search(r"/(login|sign-?up|goodbye)", url)

    # ---------- tạo học phần ----------
    def create_set(self, lesson: Lesson, title: str, lesson_dir: Path,
                   with_images: bool = True, assist: bool = False) -> str:
        self.debug_dir = lesson_dir / "debug"
        p = self.page
        try:
            if not self.is_logged_in():
                raise QuizletError("Chưa đăng nhập Quizlet. Chạy một lần: ./hsk login")
            self.dismiss_cookies()

            # 1) tiêu đề
            t = self.find("title")
            t.click()
            t.fill(title)

            # 2) nhập toàn bộ thẻ bằng hộp "Nhập"
            self.find("import_button").click()
            box = self.find("import_textarea")
            box.fill(import_text(lesson))
            self._try_click("sep_term_tab")
            if self._try_click("sep_card_custom"):
                inp = self.find("sep_card_custom_input", required=False, timeout=3000)
                if inp:
                    inp.fill(CARD_SEP)
            p.wait_for_timeout(800)
            self.snap("import_preview")
            self.find("import_confirm").click()
            p.wait_for_timeout(2500)

            rows = self._rows()
            n = rows.count() if rows else 0
            print(f"   Quizlet hiển thị {n} thẻ (cần {len(lesson.cards)})")
            if n < len(lesson.cards):
                self.snap("card_count_mismatch")
                raise QuizletError(f"Chỉ thấy {n}/{len(lesson.cards)} thẻ sau khi Nhập. "
                                   f"Kiểm tra ảnh trong {self.debug_dir}")

            # 3) hình minh họa
            if with_images:
                self._upload_images(lesson, lesson_dir, rows)

            # 4) lưu
            self.snap("before_create")
            self.find("create_button").click()
            p.wait_for_timeout(1500)
            self.wait_for_human()
            p.wait_for_url(re.compile(r"/\d{5,}/"), timeout=60000)
            url = p.url.split("?")[0]
            print(f"   [ok] Đã tạo: {url}")
            return url

        except (QuizletError, PWError, PWTimeout) as e:
            self.snap("error")
            if assist and not self.cfg.get("headless", False):
                print(f"\n[!] Gặp lỗi: {e}\n    Hãy hoàn tất thủ công trong cửa sổ trình duyệt "
                      f"(file nhập: {lesson_dir / 'quizlet_import.txt'}, hình: {lesson_dir / 'images'}).")
                input("    Lưu học phần xong thì nhấn Enter... ")
                return p.url.split("?")[0]
            raise

    def _try_click(self, key: str) -> bool:
        loc = self.find(key, required=False, timeout=2500)
        if loc:
            try:
                loc.click()
                return True
            except PWError:
                pass
        return False

    def _rows(self) -> Locator | None:
        for s in self.sel["card_rows"]:
            loc = self.page.locator(s)
            try:
                if loc.count():
                    return loc
            except PWError:
                continue
        return None

    def _upload_images(self, lesson: Lesson, lesson_dir: Path, rows: Locator):
        ok = fail = 0
        for i, c in enumerate(lesson.cards):
            if not c.image:
                continue
            img = (lesson_dir / c.image).resolve()
            if not img.exists():
                continue
            row = rows.nth(i)
            try:
                row.scroll_into_view_if_needed()
                self.find("image_button", scope=row, timeout=4000).click()
                self.page.wait_for_timeout(600)
                self._set_file(row, img)
                self.page.wait_for_timeout(int(self.cfg.get("image_wait_ms", 2500)))
                ok += 1
                print(f"   [up] {c.index:02d} {c.hanzi}")
            except (QuizletError, PWError, PWTimeout) as e:
                fail += 1
                print(f"   [!] Không gắn được hình cho {c.hanzi}: {str(e).splitlines()[0]}")
                self.snap(f"img_fail_{c.index:02d}")
                self.page.keyboard.press("Escape")
        print(f"   Hình: {ok} thành công, {fail} lỗi")
        if fail and ok == 0:
            print("   (Lưu ý: tải hình riêng lên Quizlet có thể cần tài khoản Quizlet Plus.)")

    def _set_file(self, row: Locator, img: Path):
        # Cách 1: input[type=file] trong thẻ hoặc trong hộp thoại đang mở
        for scope in (row, self.page.locator("[role='dialog']").last, self.page):
            try:
                inp = scope.locator("input[type='file']")
                if inp.count():
                    inp.last.set_input_files(str(img))
                    return
            except PWError:
                continue
        # Cách 2: bấm nút "Tải lên" và bắt hộp chọn file
        up = self.find("upload_button", timeout=4000)
        with self.page.expect_file_chooser(timeout=6000) as fc:
            up.click()
        fc.value.set_files(str(img))

    # ---------- hỗ trợ sửa selector ----------
    def inspect(self):
        self.page.goto(f"{self.base}/create-set")
        print(">>> Playwright Inspector đã mở. Dùng nút 'Pick locator' để lấy selector, "
              "rồi chép vào quizlet_selectors.json. Đóng Inspector để thoát.")
        self.page.pause()
