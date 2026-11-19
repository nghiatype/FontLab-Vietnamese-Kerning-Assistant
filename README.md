# NghiaType — FontLab Tools

**Phiên bản hiện tại:** `1.9.3 Beta` · **Cập nhật:** 19/11/2026  
**Nền tảng chính:** FontLab 8 (PythonQt) · **FontLab 9:** hỗ trợ đọc và xem trước, chức năng ghi chưa được xác nhận

NghiaType là bộ công cụ hỗ trợ thiết kế typeface trong FontLab. Mục tiêu là tận dụng những tính năng FontLab đã có, đồng thời giúp người dùng kiểm tra dữ liệu và thực hiện các thao tác lặp lại dễ dàng hơn.

Phiên bản này tập trung vào **Kerning Studio**: bổ sung glyph vào các nhóm kerning Native, đối chiếu với OpenType `kern`, rồi chọn những glyph cần đồng bộ. Plugin không tự động quyết định thay người dùng.

> **Beta:** Hãy dùng một bản font **COPY đã lưu và có bản sao lưu độc lập** để kiểm thử. Plugin không tự Save hoặc Compile. Nếu thao tác ghi hoặc đọc lại dữ liệu bị lỗi, **đóng bản COPY mà không lưu**.

## Kerning Studio làm được gì?

| Bước | Chức năng | Có sửa font không? |
| --- | --- | --- |
| **01 · Native Classes** | Quét class Native, gợi ý glyph tiếng Việt còn thiếu; chọn từng class/glyph, xem trước, kiểm tra và thêm vào Native | Chỉ khi chọn **Add to Native**, xác nhận và vượt qua kiểm tra |
| **02 · Cross-check** | So sánh thành viên class Native với OpenType `kern`; hiển thị `MATCH`, `DIFFERENT`, glyph chỉ có ở mỗi bên | **Không** — chỉ đọc |
| **03 · OT Sync & Apply** | Chọn những glyph Native có nhưng class OpenType chưa có, xem diff FEA, kiểm tra trước khi ghi, backup và ghi class có xác nhận | Chỉ khi chọn **Add to test font**, xác nhận và vượt qua kiểm tra |

Hai bên dùng **core và cơ chế ghi riêng**. Cross-check là cầu nối để người dùng xem sự khác biệt, không phải lệnh đồng bộ tự động. Plugin chỉ bổ sung thành viên vào **class đã tồn tại**; không tự thay giá trị kerning pair hoặc viết lại các quy tắc `pos`.

### Luồng sử dụng đề xuất (FontLab 8)

1. **Save As** font thành một bản `.vfc` COPY để thử; chuẩn bị thêm một bản backup độc lập.
2. Mở `NghiaType_1.9.3_Beta.py` trong **Scripting/Macro panel** của FontLab và chạy.
3. Trong **Native Classes**, nhấn **Scan Native Classes**, chọn các gợi ý, **Check selection**, rồi xác nhận **Add to Native**. Đợi kết quả đọc lại dữ liệu thành công.
4. Sang **Cross-check** để xem Native và OpenType đang khớp hay khác nhau ở glyph nào. `DIFFERENT` không có nghĩa là plugin đã sửa font.
5. Sang **OT Sync & Apply**, chỉ chọn glyph muốn bổ sung, xem FEA diff và nhấn **Check changes**. Nếu đạt kiểm tra, xác nhận ghi và chọn **file backup `.fea` mới** khi được yêu cầu.
6. Sau khi đọc lại dữ liệu thành công, **tự Save bản COPY**. Nếu có lỗi ghi/đọc lại, **không Save**.

Sau Native Apply thành công, phiên bản 1.9.3 cho phép tiếp tục sang Cross-check và OT Sync **ngay trong cùng phiên FontLab**, không bắt buộc Save/đóng/mở lại ở giữa. Các bước kiểm tra dữ liệu trực tiếp trước khi ghi vẫn được giữ. Luồng liền mạch này cần thêm thử nghiệm thực tế trên nhiều font.

## Cài đặt

Giải nén trọn bộ release vào **một thư mục riêng**, tránh trộn với các script Alpha cũ. Các file Python cần nằm **cùng thư mục**:

```text
NghiaType_1.9.3_Beta.py                  # Chạy file này
NghiaType_Native_Kerning_V2_GUI_Alpha1.py
NghiaType_Native_Core_V2_Alpha1_4_1_SCOPED_GUARDED_FL8(1).py
FontLab_Vietnamese_Kerning_Assistant_v1.py
NghiaType_Kerning_Crosscheck_V3_Alpha0_11.py
NghiaType_OT_Sync_Preview_V3_Alpha0_12.py
NghiaType_OT_Guarded_Preflight_V3_Alpha0_14.py
NghiaType_OT_Guarded_Writer_V3_Alpha0_16.py
```

**Lưu ý:** Giữ **nguyên tên file**, kể cả `(1)` ở Native Core: bản hiện tại tìm các thành phần theo tên cụ thể. Thư mục `Archive/` là lịch sử thử nghiệm, không phải nơi chạy bản phát hành.

## Trạng thái kiểm thử và giới hạn

- **FontLab 8:** Người phát triển đã thử nghiệm thực tế các luồng Native Apply, OpenType class Apply, đọc lại kết quả, lưu và mở lại trên bản font COPY. Những thử nghiệm đó không chứng minh mọi font đều tương thích.
- **FontLab 9:** Đọc Native/Preview đã được thử, nhưng **Native/OT writer vẫn khóa** do API ghi chưa được xác minh đủ.
- **Offline:** 92 bài regression test đã đạt ở bản 1.9.3, gồm lỗi PythonQt `int object is not callable` và một số kiểm tra cấu trúc UI. Đây không phải bài kiểm tra giao diện trực tiếp trong FontLab.
- Cross-check chỉ đọc **class declarations** và các lệnh `pos` đơn giản bên trong text feature `kern`; **không** kiểm tra toàn bộ GPOS đã biên dịch, tên class đơn lẻ, hay mọi dạng cú pháp FEA.
- `Create [kern] Feature`, `Update Auto Features` và tùy chọn **Update on Compile** của FontLab có thể tái tạo nội dung `kern` từ Native. Sau các thao tác này, hãy Cross-check lại trước khi đồng bộ.
- Writer chỉ thay đổi dữ liệu **trong bộ nhớ** sau khi xác nhận và kiểm tra; backup `.fea` **không thay thế** bản backup `.vfc` đầy đủ.

### Khi gặp lỗi

1. **Đừng Save bản font thử** nếu lỗi xảy ra trong quá trình ghi hoặc xác minh kết quả.
2. Ghi lại thao tác vừa thực hiện, phiên bản FontLab và traceback trong **Output panel**.
3. Kiểm tra bộ file có đầy đủ và đúng tên, đặc biệt các module Native/OT bên trên.
4. Gửi báo cáo lỗi kèm ảnh giao diện **đã ẩn tên font/đường dẫn nhạy cảm nếu cần**.

## Cấu trúc dự án và định hướng

- **`README.md`:** cách dùng hiện tại.
- **`DEVLOG.md`:** quyết định kỹ thuật, kết quả thử nghiệm và các giới hạn cần giữ.
- **`Archive/`:** script thử nghiệm/Alpha cũ, giữ lại để tra cứu; không chạy lẫn với release.

Sau Kerning Studio, các hướng phát triển dự kiến là:

1. **OpenType Studio:** xem class, feature, lookup và kiểm tra tham chiếu GSUB/GPOS ngoài `kern`.
2. **Accented Alternates:** từ glyph như `A.ss01` đã có anchor, đề xuất tạo các biến thể có dấu cùng công thức composite để FontLab tự dựng và căn dấu.
3. **Glyph Matrix / Language Coverage:** kiểm tra ngôn ngữ, liệt kê glyph còn thiếu, gợi ý thứ tự bổ sung và liên kết tham khảo Unicode.

Các ý tưởng trên **chưa phải tính năng đã hoàn thành**.

## Dành cho người tiếp tục phát triển

Đọc **[DEVLOG.md](DEVLOG.md)** trước khi sửa writer. Nguyên tắc chính: **giữ Native và OpenType độc lập, chỉ ghi trên COPY thử nghiệm, xác nhận rõ ràng, đọc lại chính xác, không tự Compile/Save**. Không mở khóa FontLab 9 writer chỉ vì các kiểm thử read-only thành công.

---

**NghiaType · 19.11.2026 · Kerning Studio 1.9.3 Beta**
