# HSK Docx → Quizlet (tự động 100%)

Thả file bảng từ vựng `.docx` vào thư mục `inbox/`. Chương trình tự động:

1. Đọc bảng từ vựng (cột Chữ Hán, Pinyin, Giải nghĩa, Ví dụ, Từ liên quan).
2. Tạo thẻ. **Mặt trước:** chữ Hán. **Mặt sau:** pinyin, từ loại, nghĩa, ví dụ, bộ thủ và từ liên quan.
3. Tạo **thư mục hình minh họa**, mỗi từ một hình: `output/Bai_27/images/01_了.jpg`, …
4. Mở Quizlet, tạo học phần, dán thẻ, gắn hình vào từng thẻ rồi bấm **Tạo**.
5. Lưu link học phần vào `output/Bai_27/quizlet_url.txt` và chuyển file `.docx` vào `inbox/done/`.

```
inbox/Bai_27.docx  ──►  output/Bai_27/
                          ├── quizlet_import.txt   (để dán tay nếu cần)
                          ├── cards.csv / cards.json
                          ├── images/01_了.jpg … 44_愉快.jpg
                          ├── image_credits.json   (nguồn từng hình)
                          └── quizlet_url.txt      (link học phần đã tạo)
```

---

## 1. Cài đặt trên WSL (một lần)

**Cần có:** Windows 11, hoặc Windows 10 bản 21H2 trở lên, có **WSLg** để cửa sổ trình duyệt hiện lên được. Kiểm tra bằng cách mở PowerShell và chạy `wsl --update`. Nếu lệnh cập nhật gì đó, chạy tiếp `wsl --shutdown` rồi mở lại Ubuntu.

Trong cửa sổ Ubuntu (WSL):
```bash
cd ~
git clone https://github.com/LongNguyen1984/HSK-quizlet.git
cd HSK-quizlet
./setup.sh
```

`setup.sh` tự làm các việc sau:
- Cài Python venv và font tiếng Trung (`fonts-noto-cjk`). Bước này hỏi mật khẩu sudo.
- Cài thư viện Python, Chromium cho Playwright và các thư viện hệ thống nó cần.
- Tạo `config.json`.
- Mở trình duyệt để bạn **đăng nhập Quizlet một lần**. Đăng nhập xong, quay lại terminal và nhấn **Enter**.

> Mẹo: trong Chromium của Playwright, nên đăng nhập Quizlet bằng **email và mật khẩu**. Google đôi khi chặn đăng nhập trong trình duyệt tự động. Nếu tài khoản Quizlet của bạn chỉ dùng "Đăng nhập bằng Google", hãy đặt thêm mật khẩu trong phần cài đặt tài khoản Quizlet.

macOS và Linux thường cũng chạy `./setup.sh`. Trên Windows thuần (không dùng WSL), dùng `setup_windows.bat`.

## 2. Sử dụng

```bash
./hsk upload ~/Bai_27.docx                                  # một file
./hsk upload "C:\Users\Long\Documents\HSK\Bai_28.docx"    # dán thẳng đường dẫn Windows cũng được
./hsk upload /mnt/c/Users/Long/Documents/HSK/*.docx         # nhiều file
./hsk convert Bai_27.docx                                   # chỉ tạo file nhập và hình, không đụng Quizlet
./start_watch.sh                                            # chạy nền: thả .docx vào inbox là tự xử lý
```

Các tùy chọn thêm:

- `--no-images`: không tạo hình.
- `--refresh-images`: tạo lại toàn bộ hình.
- `--force`: tạo lại học phần dù trước đó đã tạo.
- `--assist`: khi gặp lỗi, giữ trình duyệt mở để bạn làm nốt bằng tay.
- `--headless`: chạy ẩn trình duyệt.

Bài nào đã tạo xong được ghi vào `output/history.json`, nên thả lại cùng một file sẽ không tạo trùng.

### Thả file từ Windows Explorer

Bạn có hai cách:

- **Dùng thư mục bên Windows.** Đây là cách tiện nhất. Trong `config.json`, đặt:
  ```json
  "inbox_dir":  "/mnt/c/Users/<tên>/Documents/HSK-inbox",
  "output_dir": "/mnt/c/Users/<tên>/Documents/HSK-output"
  ```
  Sau đó cứ kéo file `.docx` vào `Documents\HSK-inbox` trong Explorer. Thư mục hình và link Quizlet sẽ nằm ở `Documents\HSK-output`.
- **Dùng thư mục `inbox` mặc định trong WSL.** Trên thanh địa chỉ Explorer, gõ `\\wsl$\Ubuntu\home\<user>\HSK-quizlet\inbox`.

### Tự chạy khi bật máy

```bash
./install_autostart_wsl.sh            # cài
./install_autostart_wsl.sh --remove   # gỡ
```

Script tạo một lối tắt trong thư mục Startup của Windows. Mỗi lần bạn đăng nhập Windows, nó mở một cửa sổ WSL thu nhỏ chạy `./start_watch.sh`. Nhật ký chạy nằm ở `output/run.log`.

## 3. Hình minh họa

Với mỗi từ, chương trình thử lần lượt các nguồn hình theo thứ tự `image_sources` trong `config.json`:

| Nguồn | Cần gì | Ghi chú |
|---|---|---|
| `custom` | Bỏ hình vào `images_custom/Bai_27/` | Đặt tên theo số thứ tự (`05.jpg`, `05_片.png`) hoặc theo chữ Hán (`片.jpg`). **Luôn được ưu tiên.** |
| `pixabay` | API key miễn phí: đăng ký tại https://pixabay.com/api/docs/ rồi dán vào `pixabay_api_key` | Ảnh minh họa đẹp, dùng tự do |
| `openverse` | Không cần key | Chỉ tìm khi có `keyword_en`. Ảnh giấy phép Creative Commons, nguồn ghi trong `image_credits.json` |
| `generated` | Không cần gì | Thẻ hình tự vẽ (chữ Hán, pinyin, nghĩa). Dùng cho từ trừu tượng như 了, 得, 所以 |

**Từ khóa tìm hình** nằm trong `keywords/Bai_xx.csv`. File này tự tạo ở lần chạy đầu, bạn sửa trực tiếp được:

| Cột | Ý nghĩa |
|---|---|
| `keyword_vi` | Từ khóa tiếng Việt, lấy tự động từ nghĩa. Ghi `-` nếu không muốn tìm ảnh online cho từ đó. |
| `keyword_en` | Từ khóa tiếng Anh, cho kết quả tốt hơn. `keywords/Bai_27.csv` đã điền sẵn. |
| `skip` | Ghi `x` để thẻ đó không có hình. |

Sửa xong thì chạy `./hsk convert Bai_27.docx --refresh-images` để tạo lại hình.

> ⚠️ Tải hình **của riêng bạn** lên thẻ Quizlet thường cần tài khoản **Quizlet Plus**. Nếu tài khoản miễn phí bị chặn upload, học phần vẫn được tạo, chỉ thiếu hình. Muốn tắt hẳn bước gắn hình, đặt `"upload_images": false` trong `config.json`. Thư mục `images/` vẫn được tạo để bạn dùng nơi khác.

## 4. Cấu hình `config.json`

| Khóa | Mặc định | Ý nghĩa |
|---|---|---|
| `title_template` | `Lesson {num} - Bài {num} {title} - HSK 2 Classical` | Mẫu tên học phần |
| `include_related` | `true` | Đưa phần bộ thủ và từ liên quan vào mặt sau |
| `browser_channel` | `""` | Để trống thì dùng Chromium của Playwright (nên dùng trên WSL). Trên Windows thuần hoặc macOS có thể đặt `chrome` hoặc `msedge` |
| `inbox_dir`, `output_dir` | `""` | Thư mục nhận `.docx` và thư mục kết quả. Để trống thì dùng `./inbox` và `./output` |
| `headless` | `false` | `true` để chạy ẩn. Nên để `false` ở lần chạy đầu để quan sát |
| `timeout_ms`, `image_wait_ms` | 15000, 2500 | Tăng lên nếu mạng chậm |

## 5. Khi Quizlet đổi giao diện

Phần tự động bấm nút dựa vào các bộ chọn (selector) trong **`quizlet_selectors.json`**, không viết cứng trong code.

Nếu báo lỗi `Không tìm thấy phần tử 'xxx'`:
1. Xem ảnh chụp màn hình lúc lỗi trong `output/Bai_xx/debug/`.
2. Chạy `./hsk inspect`. Trong Playwright Inspector, bấm **Pick locator** rồi nhấp vào nút cần tìm trên trang Quizlet.
3. Chép selector vừa lấy vào **đầu** danh sách của mục `xxx` trong `quizlet_selectors.json`.

Trong lúc chưa sửa, chạy với `--assist` để làm nốt bằng tay. Hoặc dán `quizlet_import.txt` vào Quizlet theo cách: **Tạo → Học phần → + Nhập**, chọn **Tab** giữa thuật ngữ và định nghĩa, **Tùy chỉnh `###`** giữa các thẻ.

## 6. Cấu trúc repo

```
hsk                      lệnh tắt (WSL/Linux): ./hsk login | convert | upload | watch | inspect
run.py                   CLI chính
hskq/parser.py           đọc .docx → thẻ
hskq/export.py           xuất quizlet_import.txt, cards.csv, cards.json
hskq/images.py           tạo thư mục hình (custom / Pixabay / Openverse / tự vẽ)
hskq/quizlet.py          tự động hóa quizlet.com bằng Playwright
quizlet_selectors.json   selector giao diện Quizlet (sửa khi Quizlet đổi giao diện)
keywords/                từ khóa tìm hình cho từng bài
images_custom/           hình riêng của bạn, mỗi bài một thư mục
setup.sh, start_watch.sh, install_autostart_wsl.sh      WSL / Linux / macOS
setup_windows.bat, start_watch.bat, upload.bat, install_autostart.bat   Windows thuần (không WSL)
```

**Lưu ý:** Quizlet không có API công khai để tạo học phần, nên chương trình điều khiển trình duyệt giống như người dùng thao tác. Hãy dùng cho học phần của chính bạn với tốc độ vừa phải. Điều khoản của Quizlet không khuyến khích tự động hóa ở quy mô lớn.
