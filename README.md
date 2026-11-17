# Vietnamese Kerning Assistant — FontLab 8/9 GUI (BETA)

Giao diện chạy **bên trong FontLab 8/9** qua PythonQt, sử dụng bộ xử lý `FontLab_Vietnamese_Kerning_Assistant_v1.py` đi kèm. Công cụ gợi ý bổ sung các glyph tiếng Việt vào kerning class đã tồn tại trong OpenType feature `kern`.

**Trạng thái kiểm thử (người dùng xác nhận):** Đã thử trên **FontLab 8.4.3.8984** và **FontLab 9.0.9809** với font kiểm thử Post Grotesk Light. Quy trình Scan → Apply (readback khớp chính xác) → Compile → Save/Close/Reopen → Scan lại (0 gợi ý) → Export OTF/TTF và kiểm tra kerning đã hoạt động trong những lần thử này. Đây vẫn là bản **BETA**; chưa bảo đảm tương thích với mọi font hoặc phiên bản FontLab.

## Cài và mở giao diện

1. Giữ **hai file `.py` cùng thư mục**:
   - `FontLab_Vietnamese_Kerning_GUI.py` — file mở giao diện
   - `FontLab_Vietnamese_Kerning_Assistant_v1.py` — bộ xử lý đã test
2. Mở FontLab 8 hoặc 9 và một font có OpenType feature `kern` dạng text.
3. Trong **Scripting panel** của FontLab, mở `FontLab_Vietnamese_Kerning_GUI.py`, rồi chạy script.
4. Cửa sổ **Vietnamese Kerning Assistant / BETA** sẽ hiện lên. Nếu có lỗi, kiểm tra **Output panel** hoặc traceback; không cần cài PythonQt/PyQt riêng bằng pip.

## Cách dùng an toàn

1. **Sao lưu toàn bộ file font trước khi thao tác.** Khuyến nghị **Save As** thành một bản Copy để thử nghiệm. Công cụ **không tự sao lưu toàn bộ font**.
2. Nhấn **Scan active font** để xem số glyph, kern classes, các thành viên được gợi ý và cảnh báo.
3. Có thể lọc theo tên class/glyph hoặc bỏ chọn từng glyph; **Select all/none** áp dụng lên toàn bộ danh sách, kể cả dòng đang bị lọc. Với glyph chỉ được nhận diện theo tên (**name-only**), hãy tự kiểm tra trước khi cho phép thêm.
4. Nhấn **Export FEA + Diff** để xuất `kern_BACKUP_original.fea`, `kern_PROPOSED.fea`, `kern_changes.diff`, `report.json` vào thư mục `FontLab_Kerning_Assistant` trong thư mục người dùng Windows. Nút này **không sửa font**.
5. Nếu thấy đúng, đánh dấu **I confirm I have a separate full-font backup**. Nếu chọn glyph name-only, phải duyệt và đánh dấu xác nhận thứ hai.
6. Nhấn **Apply Changes** → đọc xác nhận → chọn **Yes**. GUI chỉ sửa text feature `kern` **trong bộ nhớ**, không tự lưu font. Chỉ khi hiện **APPLY READBACK: EXACT MATCH** mới chuyển sang kiểm tra trong FontLab.
7. **Compile/Play** phần OpenType Features. Nếu có lỗi hoặc kết quả bất thường, **đóng font mà không lưu** và sử dụng bản sao lưu.
8. Nếu compile thành công, lưu font, đóng và mở lại, rồi nhấn **Scan active font**. Kết quả mong đợi là **0 thành viên cần thêm**. Xuất OTF/TTF và kiểm tra kerning trong Metrics/ứng dụng khác.

### Giới hạn bảo vệ ở bản GUI hiện tại

- GUI đang đặt `ALLOW_ORIGINAL_FONT = True`, nên **không bắt buộc tên file chứa chữ `Copy`**. Dù vậy, vẫn phải xác nhận đã có **bản sao lưu font đầy đủ** trước khi Apply.
- Nếu muốn bắt buộc tên file chứa chữ `copy`, đổi thành `ALLOW_ORIGINAL_FONT = False` trong `FontLab_Vietnamese_Kerning_GUI.py`.
- **Script core khi chạy độc lập** có thiết lập Apply riêng và mặc định ở chế độ Preview. Quy tắc tên `copy` trong core không phải quy tắc đang được GUI sử dụng.
- File backup `.fea` và báo cáo **không thể thay thế** bản sao lưu toàn bộ font nguồn.

## Ghi chú kỹ thuật

- Mở/Scan/Preview không thay đổi font; **Export FEA + Diff** chỉ ghi báo cáo ra đĩa.
- Apply **không tự động Save**; nó chỉ sửa text feature `kern` trong font đang mở sau khi có bản backup FEA và xác nhận.
- Chỉ thêm các glyph tiếng Việt nhận dạng được vào **class đã tồn tại**, không tự tạo class mới, không thay đổi POS rules.
- **Native kerning groups trong Classes panel không được cập nhật trực tiếp.** Dữ liệu native và class khai báo trong **OpenType Features > kern** có thể khác nhau.
- Các thao tác như **Update all auto features** có thể tái tạo feature từ dữ liệu native và ghi đè bổ sung trong text `kern`; hãy Scan và kiểm tra lại nếu dùng thao tác này.
- Các file báo cáo tạo khi chạy có thể chứa **đường dẫn font và nội dung FEA của font client**. Không public báo cáo này nếu chưa được phép.
- Nếu không hiện GUI hoặc báo lỗi liên quan PythonQt, gửi nội dung **Output panel** và phiên bản FontLab; đừng tự thay `PyQt5`/`PySide6` vào script này.

**Khuyến nghị:** Luôn thử trên bản sao trước khi dùng với font đang làm việc cho client.
