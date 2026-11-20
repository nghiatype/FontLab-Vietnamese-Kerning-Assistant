# NghiaType

**Keep your Native and OpenType kerning classes in sync.**  
**Giữ các nhóm kerning Native và OpenType luôn đồng bộ.**

NghiaType is a PythonQt utility for **FontLab 8**. Its Kerning Studio provides a guided workflow for finding missing glyphs in Native kerning groups, comparing them with OpenType `kern` classes, and carefully updating eligible classes.

NghiaType là công cụ PythonQt dành cho **FontLab 8**. Kerning Studio hướng dẫn người dùng tìm glyph còn thiếu trong các nhóm kerning Native, đối chiếu với class OpenType `kern`, sau đó cập nhật những class đủ điều kiện an toàn.

**Current version / Phiên bản:** `1.9.5` · **Released / Phát hành:** 20 November 2026 (20/11/2026)  
**Status / Trạng thái:** Kerning Studio đã hoàn thiện và được thử nghiệm trên FontLab 8; khả năng tương thích với FontLab 9 vẫn đang trong giai đoạn thử nghiệm.

> [!CAUTION]
> Use a **saved test COPY** of your font, and keep a separate backup of the original. The guarded writers are designed for FontLab 8 test copies. They do not automatically save or compile the font. If verification fails, **close the test copy without saving**.
>
> **Lưu ý:** Luôn sử dụng một **bản COPY đã lưu** của font và giữ bản sao lưu riêng của font gốc. Các thao tác ghi có bảo vệ được thiết kế cho bản copy thử nghiệm trong FontLab 8; công cụ **không tự lưu hoặc biên dịch font**. Nếu xác minh thất bại, hãy **đóng bản copy mà không lưu**.

## Kerning Studio / Không gian làm việc

| Step / Bước | Module | What it does / Chức năng |
| --- | --- | --- |
| 01 | **Native classes** | Scan existing Native kerning classes, preview missing glyphs, select them, run safety checks, and add approved members.<br>Quét nhóm kerning Native, xem glyph còn thiếu, chọn glyph cần thêm, kiểm tra an toàn rồi cập nhật. |
| 02 | **Cross-check** | Read-only comparison of Native groups with OpenType `kern` classes: **In sync**, **Differs**, **Needs review**.<br>Đối chiếu Native với OpenType ở chế độ **chỉ đọc**, hiển thị rõ trạng thái đồng bộ, chênh lệch hoặc cần kiểm tra thêm. |
| 03 | **OpenType sync** | Select eligible missing glyphs, run preflight, back up `kern` to `.fea`, add glyphs, and verify.<br>Chọn glyph đủ điều kiện, kiểm tra trước khi ghi, sao lưu `kern` thành `.fea`, cập nhật và xác minh kết quả. |

The interface preserves selections while switching classes. A selection is locked after safety checks; choose **Edit selection** to change it and check again. After a successful round, use **Scan again** to start a fresh scan.

Giao diện giữ nguyên các lựa chọn khi chuyển class. Sau bước kiểm tra an toàn, lựa chọn sẽ được **khóa**; dùng **Edit selection** nếu muốn sửa và kiểm tra lại. Khi hoàn tất một vòng, nhấn **Scan again** để quét mới.

### Safety-first OpenType backup flow / Quy trình sao lưu OpenType

1. Review the glyph count and affected OpenType classes.  
   Kiểm tra số lượng glyph và những class OpenType sắp thay đổi.
2. Read and acknowledge the confirmation dialog.  
   Đọc nội dung hộp thoại và tích xác nhận.
3. Choose **where to save a new `.fea` backup** of the original OpenType `kern` feature.  
   Chọn **vị trí lưu bản backup `.fea` mới** của tính năng `kern` hiện tại.
4. NghiaType repeats its safety checks, creates the backup, applies eligible class additions, and verifies them.  
   NghiaType kiểm tra lại điều kiện an toàn, tạo backup, thêm glyph đủ điều kiện và xác minh kết quả.
5. Save the **test font copy manually** in FontLab only after a successful verified result.  
   Chỉ **lưu bản font COPY bằng tay** trong FontLab sau khi kết quả được xác minh thành công.

The `.fea` file is a backup of the **OpenType `kern` feature text**, **not** a saved copy of the font. Canceling either dialog stops the operation before glyphs are added.

File `.fea` chỉ sao lưu **nội dung tính năng OpenType `kern`**, **không phải file font**. Nếu hủy ở hộp thoại xác nhận hoặc cửa sổ chọn nơi lưu, quá trình sẽ dừng trước khi thêm glyph.

### Shared classes and manual review / Class dùng chung

One OpenType class can be referenced on both kerning sides. If an update could affect multiple Native groups, NghiaType marks the class as requiring review and explains why. Such classes are **not automatically unlocked or force-synced**. Review them in OpenType Studio before changing them manually.

Một class OpenType có thể được sử dụng ở cả hai phía kerning. Khi cập nhật có nguy cơ ảnh hưởng nhiều nhóm Native, NghiaType sẽ đánh dấu **cần kiểm tra** và giải thích lý do. Công cụ **không tự mở khóa hoặc ép đồng bộ** những class này; người dùng nên kiểm tra trong OpenType Studio trước khi sửa thủ công.

## Requirements / Yêu cầu

- FontLab **8** with its bundled Python / PythonQt environment.  
  FontLab **8** với môi trường Python / PythonQt đi kèm.
- A **saved test copy** of the active font; guarded writers require a filename that indicates a copy.  
  **Bản font COPY đã lưu**; tên file phải thể hiện đây là bản sao để các bộ ghi dữ liệu cho phép thao tác.
- A backup of the original font; every writer requires safety checks and confirmation.  
  Có **bản sao lưu font gốc**; mọi thao tác ghi phải vượt qua kiểm tra an toàn và xác nhận của người dùng.
- The companion NghiaType scripts listed below.  
  Có đủ các module hỗ trợ NghiaType liệt kê bên dưới.

### Companion scripts / Các module đi kèm

The main `NghiaType_1.9.5.py` GUI is a **shell**, not a standalone implementation of every scanner and writer. It loads these exact-named modules:

`NghiaType_1.9.5.py` là **giao diện điều phối**, không phải file chứa toàn bộ bộ quét và bộ ghi dữ liệu. Công cụ nạp các module có **đúng tên file** sau:

```text
NghiaType_1.9.5.py
NghiaType_Native_Kerning_V2_GUI_Alpha1.py
FontLab_Vietnamese_Kerning_Assistant_v1.py
NghiaType_Kerning_Crosscheck_V3_Alpha0_11.py
NghiaType_OT_Sync_Preview_V3_Alpha0_12.py
NghiaType_OT_Guarded_Preflight_V3_Alpha0_14.py
NghiaType_OT_Guarded_Writer_V3_Alpha0_16.py
```

Place the available companion scripts beside the main file. If a required module cannot be found there, NghiaType asks you to locate the **exact matching filename**. Keep these engine files at their tested versions; do not substitute a similarly named script.

Đặt các module bên cạnh file chính. Nếu không tìm thấy, NghiaType sẽ yêu cầu chọn đúng file tương ứng. **Không thay thế bằng file gần giống tên** hoặc tự đổi tên engine vì điều đó có thể làm sai lệch các bước kiểm tra an toàn.

## Run in FontLab 8 / Cách sử dụng

1. **Back up your original font**, then open a separately saved **COPY** in FontLab 8.  
   **Sao lưu font gốc**, sau đó mở **bản COPY đã lưu riêng** trong FontLab 8.
2. Open the **Macro** panel and run `NghiaType_1.9.5.py`.  
   Mở bảng **Macro** và chạy file `NghiaType_1.9.5.py`.
3. In **Native classes**, select **Scan Native classes**, review suggestions, then use **Check selection** before confirming.  
   Ở **Native classes**, quét class, xem glyph được đề xuất, dùng **Check selection** rồi mới xác nhận thêm glyph.
4. In **Cross-check**, compare both class systems and review warnings for shared or ambiguous classes.  
   Ở **Cross-check**, đối chiếu hai hệ thống class và đọc cảnh báo dành cho class dùng chung hoặc chưa xác định rõ.
5. In **OpenType sync**, select eligible glyphs, run preflight, confirm, choose a new `.fea` backup location, and wait for verification.  
   Ở **OpenType sync**, chọn glyph đủ điều kiện, kiểm tra an toàn, xác nhận, chọn nơi lưu backup `.fea` mới rồi chờ xác minh.
6. **Save the test font manually** only after the result is verified.  
   **Chỉ lưu bản font thử nghiệm bằng tay** khi công cụ báo xác minh thành công.

You can inspect additional read-only information through the **Report**, **Details**, and **FEA details** controls. Native preview information can also be exported as JSON.

Bạn có thể xem thông tin bổ sung ở các mục **Report**, **Details**, **FEA details** (chỉ đọc) và xuất dữ liệu xem trước Native thành file JSON.

## Important limitations / Giới hạn cần biết

- **FontLab 9:** experimental compatibility only; guarded write support is not established for FL9.  
  **FontLab 9:** vẫn đang thử nghiệm; chưa xác nhận hỗ trợ ghi dữ liệu an toàn trên FL9.
- **OpenType scope:** Cross-check reads text `kern` with limited class and pair-rule parsing; it does **not** cover all syntax or compiled GPOS.  
  **Phạm vi OpenType:** Cross-check chỉ phân tích một phần cú pháp `kern` dạng văn bản; **không** kiểm tra toàn bộ cú pháp OpenType hay GPOS đã biên dịch.
- **No silent writes:** scans, comparisons, old `.fea` previews, and reports never add glyphs by themselves.  
  **Không tự ghi dữ liệu:** quét, đối chiếu, xem trước `.fea` cũ và xuất báo cáo không tự thêm glyph.
- **No automatic Save/Compile:** in-memory changes are not the same as saving the font to disk.  
  **Không tự Save/Compile:** thay đổi trong bộ nhớ FontLab không đồng nghĩa với việc font đã được lưu xuống ổ đĩa.
- **Verification failures:** close the test copy **without saving**, inspect the report, and restart with a clean copy.  
  **Lỗi xác minh:** đóng bản font COPY **mà không lưu**, xem báo cáo lỗi và bắt đầu lại từ một bản copy sạch.

## Release history / Lịch sử phát triển

See [DEVLOG.md](DEVLOG.md) for the 1.9.5 release notes, interface decisions, safety boundaries, and development milestones.

Xem [DEVLOG.md](DEVLOG.md) để đọc ghi chú phát hành 1.9.5, các quyết định UI/UX, giới hạn an toàn và những cột mốc phát triển.

---

*NghiaType · FontLab workflow tools / Công cụ hỗ trợ FontLab · Version / Phiên bản 1.9.5*
