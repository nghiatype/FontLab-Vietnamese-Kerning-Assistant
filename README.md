# Vietnamese Kerning Assistant — FontLab 8 GUI (BETA)

Giao diện chạy **bên trong FontLab 8** qua PythonQt. Nó dùng lại **nguyên vẹn** bộ xử lý đã kiểm chứng `FontLab_Vietnamese_Kerning_Assistant_v1.py`.

**Trạng thái kiểm thử:** thuật toán nền v1.0 đã kiểm chứng trên FontLab **8.4.3.8984** và Post Grotesk Light. **Giao diện PythonQt mới chưa được thử trực tiếp trong FontLab của bạn.** FontLab 9 chưa được kiểm chứng.

## Cài và mở giao diện

1. Giải nén ZIP vào một thư mục, giữ **hai file `.py` cùng thư mục**:
   - `FontLab_Vietnamese_Kerning_GUI.py` — file mở giao diện
   - `FontLab_Vietnamese_Kerning_Assistant_v1.py` — bộ xử lý đã test
2. Mở FontLab 8.4.3.8984 và mở một font có feature `kern` dạng text.
3. Chọn `Window > Panels > Scripting` (tên menu có thể hơi khác theo giao diện). Trong Scripting panel, chọn **Open Script**, mở `FontLab_Vietnamese_Kerning_GUI.py`, rồi bấm **Run**.
4. Cửa sổ **Vietnamese Kerning Assistant / BETA** sẽ hiện lên. Nếu có lỗi, chụp **Output panel** hoặc gửi traceback; không cần cài thêm Python 3.13 hay pip package.

## Cách dùng an toàn

1. **Save As** font thành một bản thử riêng, và đặt chữ `Copy` trong **tên file** (ví dụ `My Font - Copy.vfc`). Giữ font gốc ở nơi khác.
2. Nhấn **Scan active font**. Xem tổng số glyph, kern classes và các thành viên gợi ý.
3. Có thể gõ tên class/glyph để lọc, bỏ chọn những glyph không muốn thêm; **Select all/none** thay đổi toàn bộ danh sách, kể cả dòng đang bị lọc.
4. Nhấn **Export FEA + Diff** để xuất backup `kern_BACKUP_original.fea`, `kern_PROPOSED.fea`, `kern_changes.diff`, `report.json` vào thư mục `FontLab_Kerning_Assistant` trong thư mục người dùng Windows. Nút này **không sửa font**.
5. Nếu thấy đúng, đánh dấu **I confirm the active font is an expendable COPY**. Nếu có glyph chỉ được nhận dạng qua tên (name-only), phải duyệt và đánh dấu xác nhận thứ hai.
6. Nhấn **Apply to COPY** → đọc xác nhận → chọn **Yes**. Chỉ khi hoàn tất và hiện **APPLY READBACK: EXACT MATCH** mới chuyển sang kiểm tra trong FontLab.
7. Compile/Play phần OpenType Features. Nếu có lỗi: **đóng bản thử mà không lưu**.
8. Nếu compile thành công: lưu bản Copy, đóng, mở lại, nhấn **Scan active font**. Kết quả mong đợi là **0 thành viên cần thêm**. Xuất OTF/TTF và kiểm tra kerning trong Metrics/ứng dụng khác.

## Ghi chú kỹ thuật

- Mở/Scan/Preview không thay đổi font.
- Apply **không tự động Save**; nó chỉ sửa text feature `kern` trong font đang mở, sau khi có backup và xác nhận.
- Chỉ thêm các glyph tiếng Việt nhận dạng được vào **class đã tồn tại**, không tự tạo class mới, không thay đổi POS rules.
- Nếu cần so sánh kết quả với các AI khác, gửi `report.json`, `kern_changes.diff`, và các file `.py` đã được chạy — có đủ dấu vết để tái hiện.
- Kết quả trong **Classes panel** của source có thể khác class được khai báo trong **OpenType Features > kern**. Khi xuất font nhị phân và mở lại, FontLab có thể dựng class từ OpenType tables; cần tự kiểm chứng ở font đầu ra.
- Nếu không hiện GUI hoặc báo lỗi liên quan PythonQt, gửi nội dung **Output panel** và phiên bản FontLab; đừng tự thay `PyQt5`/`PySide6` vào script này.

**Không dùng trên font gốc khi GUI chưa được bạn kiểm thử.**
