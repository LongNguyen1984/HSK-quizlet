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

## 1. Cài đặt (một lần)

### Windows
1. Cài **Python 3.10 trở lên** từ https://www.python.org/downloads/. Khi cài, nhớ tick ô **"Add python.exe to PATH"**.
2. Cài **Google Chrome**, nếu máy chưa có.
3. Giải nén repo, ví dụ vào `C:\hsk-quizlet`, rồi nhấp đúp **`setup_windows.bat`**.
4. Một cửa sổ trình duyệt sẽ mở. **Đăng nhập Quizlet** trong cửa sổ đó, xong quay lại màn hình đen và nhấn **Enter**.
   Phiên đăng nhập được lưu trong `browser_profile/`, các lần sau không phải đăng nhập lại.

### macOS / Linux
```bash
./setup.sh
```

## 2. Sử dụng

| Cách | Làm gì |
|---|---|
| **Kéo thả** | Kéo một hoặc nhiều file `.docx` thả vào `upload.bat` |
| **Theo dõi thư mục** | Chạy `start_watch.bat`, sau đó cứ chép `.docx` vào `inbox/` là xong |
| **Tự chạy khi bật máy** | Chạy `install_autostart.bat` một lần |
| Dòng lệnh | `python run.py upload Bai_27.docx` |
| Chỉ tạo file và hình, không đụng Quizlet | `python run.py convert Bai_27.docx` |

Các tùy chọn thêm:

- `--no-images`: không tạo hình.
- `--refresh-images`: tạo lại toàn bộ hình.
- `--force`: tạo lại học phần dù trước đó đã tạo.
- `--assist`: khi gặp lỗi, giữ trình duyệt mở để bạn làm nốt bằng tay.
- `--headless`: chạy ẩn trình duyệt.

Bài nào đã tạo xong được ghi vào `output/history.json`, nên thả lại cùng một file sẽ không tạo trùng.

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

Sửa xong thì chạy `python run.py convert Bai_27.docx --refresh-images` để tạo lại hình.

> ⚠️ Tải hình **của riêng bạn** lên thẻ Quizlet thường cần tài khoản **Quizlet Plus**. Nếu tài khoản miễn phí bị chặn upload, học phần vẫn được tạo, chỉ thiếu hình. Muốn tắt hẳn bước gắn hình, đặt `"upload_images": false` trong `config.json`. Thư mục `images/` vẫn được tạo để bạn dùng nơi khác.

## 4. Cấu hình `config.json`

| Khóa | Mặc định | Ý nghĩa |
|---|---|---|
| `title_template` | `Lesson {num} - Bài {num} {title} - HSK 2 Classical` | Mẫu tên học phần |
| `include_related` | `true` | Đưa phần bộ thủ và từ liên quan vào mặt sau |
| `browser_channel` | `chrome` | Đổi thành `msedge` nếu máy dùng Edge; để `""` thì dùng Chromium của Playwright |
| `headless` | `false` | `true` để chạy ẩn. Nên để `false` ở lần chạy đầu để quan sát |
| `timeout_ms`, `image_wait_ms` | 15000, 2500 | Tăng lên nếu mạng chậm |

## 5. Khi Quizlet đổi giao diện

Phần tự động bấm nút dựa vào các bộ chọn (selector) trong **`quizlet_selectors.json`**, không viết cứng trong code.

Nếu báo lỗi `Không tìm thấy phần tử 'xxx'`:
1. Xem ảnh chụp màn hình lúc lỗi trong `output/Bai_xx/debug/`.
2. Chạy `python run.py inspect`. Trong Playwright Inspector, bấm **Pick locator** rồi nhấp vào nút cần tìm trên trang Quizlet.
3. Chép selector vừa lấy vào **đầu** danh sách của mục `xxx` trong `quizlet_selectors.json`.

Trong lúc chưa sửa, chạy với `--assist` để làm nốt bằng tay. Hoặc dán `quizlet_import.txt` vào Quizlet theo cách: **Tạo → Học phần → + Nhập**, chọn **Tab** giữa thuật ngữ và định nghĩa, **Tùy chỉnh `###`** giữa các thẻ.

## 6. Cấu trúc repo

```
run.py                   CLI: login / convert / upload / watch / inspect
hskq/parser.py           đọc .docx → thẻ
hskq/export.py           xuất quizlet_import.txt, cards.csv, cards.json
hskq/images.py           tạo thư mục hình (custom / Pixabay / Openverse / tự vẽ)
hskq/quizlet.py          tự động hóa quizlet.com bằng Playwright
quizlet_selectors.json   selector giao diện Quizlet (sửa khi Quizlet đổi giao diện)
keywords/                từ khóa tìm hình cho từng bài
images_custom/           hình riêng của bạn, mỗi bài một thư mục
setup_windows.bat, setup.sh, start_watch.bat, upload.bat, install_autostart.bat
```

**Lưu ý:** Quizlet không có API công khai để tạo học phần, nên chương trình điều khiển trình duyệt giống như người dùng thao tác. Hãy dùng cho học phần của chính bạn với tốc độ vừa phải. Điều khoản của Quizlet không khuyến khích tự động hóa ở quy mô lớn.
