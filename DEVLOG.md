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

NGHIATYPE FONT DEVELOPMENT
DEVLOG — 18/11/2026
Project: NghiaType Tools / Native Kerning V2 GUI
Status: Đóng phiên làm việc — GUI V2 Alpha.1.9

============================================================
1. KẾT QUẢ CHÍNH
============================================================

- Hoàn thành vòng phát triển GUI Native Kerning V2 bằng PythonQt cho FontLab 8/9.
- Giao diện sử dụng hướng thiết kế Material 3 Expressive, bảng màu Tropical;
  bản Alpha.1.8 tham chiếu thiết kế HTML do Nghĩa cung cấp.
- Bản mới nhất: V2 Alpha.1.9 / Refined Layout.
- Giữ nguyên Native Core V2 Alpha.1.4.1 và Core V1 Stable.
- Không tự động Apply hoặc Save. Các thao tác ghi Native Class chỉ
  được cho phép với FontLab 8 theo cơ chế Guarded Apply.
- FontLab 9 vẫn chỉ Scan / Select / Preview / Export JSON; native writer bị khóa.

============================================================
2. CORE NATIVE KERNING V2 — TRẠNG THÁI
============================================================

FontLab 8:
  [PASS] Native Class Reader
  [PASS] Vietnamese Candidate Discovery
  [PASS] Selective Planning / Read-only Preview
  [PASS] Guarded Native Apply trên bản COPY thử nghiệm
  [PASS] Stepwise Readback
  [PASS] Save / Reopen kiểm tra kết quả
  [PASS] Kerning behavior đã được kiểm tra

FontLab 9:
  [PASS] Native Class Reader / Discovery / Selective Preview
  [LOCK] Native Writer — chưa được xác minh
  [NOTE] fgKerningGroups không hỗ trợ __setitem__
  [NOTE] TypeRig không có trong môi trường kiểm thử
  [RULE] FL9 vẫn Preview Only cho đến khi có writer đã kiểm chứng

Dữ liệu kiểm thử — Post Grotesk Light:
  - 878 glyphs
  - 138 native classes
  - 134 Vietnamese candidates
  - Ban đầu có 174 available memberships (21 affected classes)
  - Sau một lần Apply 6 memberships và Save / Reopen: còn 168 available
    memberships; hai class đã được cập nhật không còn xuất hiện trong đề xuất.

Kiểm thử chọn lọc trong GUI:
  - 2 classes / 6 memberships
  - STEPWISE READBACK: PASS
  - Font thay đổi IN MEMORY ONLY ngay sau Apply; người dùng tự Save / Reopen
    trên bản sao thử nghiệm và xác nhận kết quả.

============================================================
3. TIẾN TRÌNH GUI TRONG NGÀY
============================================================

Alpha.1.1
  - Khắc phục lỗi khởi động FL9:
    AttributeError: Slot 'result' can not be overwritten on Window object.
  - Tránh ghi đè tên slot của QDialog.

Alpha.1.2
  - Live Preview tự cập nhật khi thay đổi lựa chọn.

Alpha.1.3
  - Tách workspace thành danh sách Native Classes và Proposed Glyphs.

Alpha.1.4
  - Làm gọn khu Guarded Apply.
  - Plan token được giữ trong logic xác minh, không cần hiển thị cho người dùng.

Alpha.1.5–1.7
  - Tối ưu tỉ lệ hai cột và chiều cao workspace.
  - Xử lý tương thích getter PythonQt (property hoặc callable).
  - Bố trí lại các thẻ số liệu / nút Scan.
  - Cải thiện chiều cao tối thiểu để nút Apply không bị cắt.

Alpha.1.8 — M3 Expressive Redesign
  - Header trắng; Scan xanh đậm.
  - Bốn metric cards: Glyphs / Native Classes / Viet Candidates /
    Available Adds.
  - Workspace hai cột, Preview/Readback và Guarded Apply tách rõ.
  - Giữ nguyên backend và tất cả chốt an toàn.

Alpha.1.9 — Refined Layout (BẢN CHỐT HÔM NAY)
  - Bỏ logo chữ NT.
  - Header hiển thị Python version / FontLab version / Plugin version.
    Chỉ hiển thị số build FontLab đầy đủ nếu API trả về; không tự đoán.
  - Bỏ ký hiệu '>' trong nút Scan.
  - Rút ngắn cảnh báo backup; tăng chiều cao khu Apply để tránh cắt chữ.
  - Ẩn màu thanh splitter ngang để giao diện sạch hơn, vẫn giữ khả năng
    điều chỉnh chiều cao.
  - Kiểm thử offline: 17/17 PASS; Python source compile PASS; ASCII-only PASS.
  - Người dùng đã xem trên FontLab 8 và phản hồi giao diện tốt.

Ghi chú thẩm mỹ còn lại (không ảnh hưởng chức năng):
  - Nền hàng tiêu đề QHeaderView trong bảng vẫn vuông ở góc, dù khung ngoài
    đã bo; có thể polish sau.

============================================================
4. SAFETY CONTRACT — PHẢI GIỮ
============================================================

- Core V1 Stable không được sửa.
- Native Core V2 Alpha.1.4.1 không được sửa tùy tiện.
- Scan và Preview luôn read-only.
- Apply chỉ thực hiện sau khi có kế hoạch và người dùng đồng ý rõ ràng.
- Chỉ Apply trên bản COPY thử nghiệm đã lưu và có backup riêng.
- Không auto Save; người dùng tự quyết định sau Readback PASS.
- Trước Apply phải kiểm tra lại trạng thái thực tế, kế hoạch/token và
  các điều kiện an toàn.
- Lỗi readback hoặc ghi một phần => cảnh báo DO NOT SAVE, đóng COPY không lưu.
- Không tự động mở khóa Native Writer trên FontLab 9.
- OpenType Classes/Features và Native Classes phải được quản lý độc lập
  về dữ liệu lẫn đường ghi, tránh ảnh hưởng dữ liệu client.

============================================================
5. ĐỊNH HƯỚNG NGÀY MAI — NGHIATYPE TOOLS MODULAR GUI
============================================================

Mục tiêu mới đã thống nhất:
  Hợp nhất Native và OpenType trong MỘT ứng dụng NghiaType Tools,
  nhưng dùng CÁC TAB RIÊNG theo kiểu điều hướng ứng dụng điện thoại.

Định hướng module:
  [Native Kerning]  |  [OpenType]  |  [Reports]

Native Kerning:
  - Giữ workflow V2 hiện có: Scan, Select, Preview, Guarded Apply, Readback.

OpenType (không chỉ feature kern):
  - OpenType Classes reader / membership inspection.
  - Feature inspection: liga, locl, smcp, c2sc, stylistic sets, v.v.
  - Validation: glyph/class references, thiếu/trùng, dependencies.
  - Phát triển tiếp editor / writer có bảo vệ SAU KHI kiểm chứng API.
  - Có thể chia tab con: Classes / Features / Validation.

Reports:
  - Scan report, conflicts, preview, readback và export JSON.

Shared Shell:
  - Header, font/master context, trạng thái kết nối, điều hướng tab.
  - Tab switch không xóa lựa chọn đang thao tác.
  - Mỗi module có Preview và Apply riêng khi cần.
  - Không gộp Native Core và OpenType Core thành một writer.

Ưu tiên buổi sau:
  1) Khảo sát lại OpenType V1 Stable và API đọc OT Classes/Features
     trên FL8/FL9 (READ ONLY).
  2) Thiết kế shell PythonQt nhiều tab và state riêng mỗi module.
  3) Tích hợp Native GUI V2 như module đầu tiên, không sửa backend.
  4) Xây tab OpenType đọc/preview trước; writer là công việc riêng.
  5) Lưu ý hành vi FontLab 'Update all auto features' có thể tái tạo
     OpenType class/feature content; phải kiểm tra trước khi cho phép ghi.

QUYẾT ĐỊNH KIẾN TRÚC:
  HỢP NHẤT GIAO DIỆN — KHÔNG HỢP NHẤT HAI CORE.

============================================================
6. FILE THAM CHIẾU
============================================================

- NghiaType_Native_Kerning_V2_GUI_Alpha1.py
  (latest: V2 Alpha.1.9 / Refined Layout)
- NghiaType_Native_Core_V2_Alpha1_4_1_SCOPED_GUARDED_FL8(1).py
  (companion Native Core, không chỉnh sửa)
- nghiatype_native_kerning_m3_expressive.html
  (mẫu tham chiếu thiết kế UI)
- test_native_v2_gui_backend.py
  (bộ kiểm thử mô phỏng backend; 17/17 PASS tại thời điểm chốt)

END OF DEVLOG — 18/11/2026

