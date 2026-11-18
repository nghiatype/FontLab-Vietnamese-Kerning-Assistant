# NghiaType Tools — Development Log

Ghi lại tiến độ phát triển, các vấn đề gặp phải và bước tiếp theo.

> Cách dùng: Mỗi buổi làm việc, thêm một mục ngày mới **ở trên cùng** theo mẫu cuối file. Không cần ghi quá dài.

## 2026-11-17 — Native Kerning Research

### ✅ Done

- Vietnamese Kerning Assistant V1 đã kiểm thử trên FontLab 8/9; thử nghiệm thành công 154 glyph memberships trong 17 classes.
- GUI Material 3 Expressive (Tropical) đã chạy; sửa lỗi tiếng Việt và bổ sung lựa chọn nơi lưu báo cáo.
- Đã phát hành bản beta `v1.0.0-beta.1` trên GitHub.
- Native Class Reader đọc được 50 native kerning classes (24 trái, 26 phải).
- Native Class Preview đề xuất 7 memberships vào 3 classes trên font thử nghiệm; **chưa Apply**.

### 🔬 Issues / Findings

- V1 chỉnh sửa text OpenType `kern`, chưa cập nhật Native Kerning Classes.
- `fgKerning.addGroup` chưa xác định được cách gọi hợp lệ (`Unexpected SeqBase<T> length`).
- Constructor `fgGroup` chưa nhận kiểu tham số đã thử (`Incorrect args type`).
- Các thử nghiệm Native Writer chỉ thực hiện trên font tạm trong bộ nhớ; không sửa font đang mở.
- Cần lưu ý FontLab 8 đôi khi phải vào **Font Info → Apply** sau khi mở font OTF/TTF để khởi tạo đầy đủ.

### 📌 Next

- Kiểm tra cấu trúc `fgGroup` thực tế từ một native class có sẵn (**read-only**).
- Xác định phương thức ghi Native Kerning Classes an toàn.
- Khi đã xác minh: thử trên font **Copy**, bảo toàn pairs/exceptions và kiểm tra sau Save/Reopen.
- Chỉ tích hợp vào GUI khi tính năng Native Apply hoạt động ổn định.

---

## Mẫu ghi cho lần tiếp theo

Sao chép phần dưới, thay ngày và đặt **lên trên mục cũ**:

```markdown
## YYYY-MM-DD — Tên công việc

### ✅ Done
- ...

### 🔬 Issues / Findings
- ...

### 📌 Next
- ...
```

## Backlog — Ý tưởng tương lai

- Tự động thêm/xóa anchor cho glyph mở rộng.
- Hỗ trợ tạo và cập nhật OpenType Features (FEA).
- Thống kê ngôn ngữ mà font hỗ trợ.
- Tích hợp các tính năng trong một plugin NghiaType Tools.

**Nguyên tắc:** Giữ V1 ổn định, backup trước khi ghi, không thử API chưa xác minh trên font client.

## 18-11-2026
### ✅ Done
- Xác nhận truy cập được fgGroup thực tế
- Đọc được group ID, mode và memberships
- Xác định kiểu dữ liệu trả về
- Không chỉnh sửa font
### 🔍 Next
- Nghiên cứu cách cập nhật memberships
- Kiểm thử trên font tạm trong bộ nhớ
- Xác minh kết quả trước khi thử Apply
