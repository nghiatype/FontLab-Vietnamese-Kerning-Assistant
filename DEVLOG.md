# NghiaType — Development Log

Nhật ký quyết định và kết quả thử nghiệm của NghiaType FontLab Tools. Mục đích là để Nghĩa hoặc một AI/người phát triển khác có thể **tiếp tục dự án mà không phải đoán lại cách FontLab hoạt động**.

> **Quy ước:** Ghi mục mới lên đầu theo ngày. Phân biệt rõ **đã thử trong FontLab**, **đã kiểm tra offline** và **chưa xác minh**. Đừng ghi “ổn định trên mọi font” khi chỉ thử với một font COPY.

## 19/11/2026 — Kerning Studio 1.9.3 Beta

**Trạng thái:** Hoàn thành mốc Beta cho Kerning Studio trên **FontLab 8**; tiếp tục theo dõi qua sử dụng thực tế. FontLab 9 writer vẫn chưa hỗ trợ.

### Đã hoàn thành

- Hợp nhất **Native Classes → Cross-check → OT Sync & Apply** trong một giao diện với sidebar và các bước riêng.
- Giữ **Native Core V2** và **OpenType Core V1** độc lập. Cross-check so sánh dữ liệu; không tự viết từ bên này sang bên kia.
- **Native:** quét class, gợi ý glyph có dấu tiếng Việt, tick từng glyph/class, xem trước, kiểm tra lựa chọn, ghi từng class trên bản COPY và đọc lại kết quả.
- **Cross-check:** đọc class Native và text feature `kern`, liên kết dựa trên glyph đại diện + đúng bên kerning. Một OpenType class có thể dùng cho cả **LEFT và RIGHT**; kiểm tra từng bên riêng. Hiển thị `MATCH`, `DIFFERENT`, `UNMAPPED` và glyph khác biệt.
- **OpenType:** chọn glyph cần thêm vào class đã có, tạo FEA diff, kiểm tra trước khi ghi, yêu cầu backup `.fea` mới, xác nhận ghi và đọc lại feature.
- Cho phép chuyển từ **Native Apply đã xác minh** sang Cross-check và OT Sync **trong cùng phiên FontLab**, không bắt buộc Save/Close/Reopen ở giữa. Các điều kiện an toàn và kiểm tra lại dữ liệu trực tiếp vẫn được giữ.
- Không tự Save, Compile, viết lại kerning pair values hoặc tái tạo toàn bộ feature `kern`.

### Các mốc phát hành nhỏ

| Mốc | Nội dung |
| --- | --- |
| **1.9.1 Beta** | Kết hợp Kerning Studio thành workflow với Native và OT riêng |
| **1.9.2 Beta** | Bỏ giới hạn thử nghiệm 20 class/200 membership ở phần chọn Native tích hợp; vẫn ghi từng class và đọc lại |
| **1.9.3 Beta** | Thiết kế lại Cross-check theo UI mẫu, mô tả trạng thái trực quan, luồng Native → OT trong cùng phiên; sửa tương thích PythonQt và căn chỉnh panel |

### Kết quả thử nghiệm

- **FontLab 8 / font COPY:** đã có các lần ghi Native và OpenType thành công, readback chính xác, lưu/mở lại và Cross-check không còn khác biệt. Đây là các lần thử cụ thể, **không phải bảo đảm cho mọi font**.
- **Kiểm thử Cross-check:** font Post Grotesk Light có 878 glyphs, 138 Native classes; một lần so sánh 137 class khớp và 1 class khác biệt (`Y`), sau đó xem đề xuất bổ sung glyph.
- **OT Guarded Writer:** từng xác minh thêm 4 thành viên vào class `@_Y` với readback chính xác; các `pos` hiện có được giữ nguyên. Có trường hợp glyph có 12 tham chiếu POS riêng — chỉ báo thông tin, không mặc định chặn việc thêm vào class.
- **92/92 offline tests PASS** ở bản 1.9.3 cuối ngày, gồm mô phỏng getter PythonQt dưới dạng property/method. Các kiểm thử offline **không thay thế** việc mở UI và chạy trong FontLab thực tế.
- **Chưa xác minh trên host:** bố cục UI cuối cùng ở mọi DPI/độ phân giải và toàn bộ chuỗi Native → OT không Save trung gian trên nhiều font. Tiếp tục thử trên bản COPY.

### Lỗi đã xử lý trong quá trình tích hợp

- FontLab có **Kerning Both**: Native đôi khi tách trái/phải thành `Y` và `Y2` vì không cho trùng tên. Không được ghép class chỉ vì tên giống nhau; một OT class có thể khớp cả hai phía.
- FontLab có thể **Create [kern] Feature / Update on Compile**, làm thay đổi nội dung FEA. Preflight phải dùng bản text `kern` hiện tại, phát hiện dữ liệu đổi từ lúc preview và yêu cầu quét lại khi cần.
- Một số getter trong PythonQt là **giá trị**, không phải hàm: `currentIndex`, `isVisible`, `topLevelItemCount`. Dùng helper đọc được cả property lẫn callable để tránh `TypeError: 'int' object is not callable`.
- Có lần bấm nhiều checkbox Native khiến FontLab đóng đột ngột trong GUI tích hợp; đã chỉnh cơ chế tương tác, sau đó người dùng test lại nhiều kiểu và xác nhận ổn. Vẫn nên tránh thay đổi widget/table tùy tiện nếu chưa test trong FL8.
- Các phiên bản thử nghiệm trước có yêu cầu Save/Close/Reopen quá sớm; bản 1.9.3 cho phép tiếp tục trong phiên sau Native readback thành công nhưng không bỏ preflight và writer readback.
- UI đã được tinh chỉnh theo bản mẫu: sidebar, phân tách workflow, bảng 2 cột, cột Unicode ở Native, Cross-check `MATCH/DIFFERENT`, panel giải thích tiếng Việt, khoảng cách và badge.

### Quyết định trước khi khép mốc Kerning

- **Chốt phạm vi Beta**, không mở rộng parser hay thêm writer mới trong cùng lần phát hành.
- Mọi tác vụ ghi phải do người dùng chủ động chọn và xác nhận. `DIFFERENT` chỉ là dữ liệu kiểm tra, **không phải quyền ghi**.
- Giữ lại các file cũ trong `Archive/` để tra cứu nhưng chỉ chạy bộ file release cùng thư mục.
- `README.md` phải mô tả **bản 1.9.3**, không còn hướng dẫn khởi chạy GUI V1 như công cụ chính.

---

## 18/11/2026 — Native Kerning V2 / nghiên cứu writer

### Hoàn thành

- Đọc được cấu trúc `fgGroup`: tên, mode (`KernLeft`/`KernRight`) và danh sách thành viên.
- Xây Native scanner, Vietnamese candidate discovery, selective preview và **Guarded Native Apply** cho FontLab 8 trên bản font COPY.
- Ghi theo từng bước, sau mỗi bước đối chiếu thành viên Native và các kerning pair values; **không tự Save**.
- Xây giao diện Native V2 với Material 3 Expressive: metric cards, bảng Native Classes/Proposed Glyphs, Preview và Apply tách riêng.
- Đã thử Save/Reopen và kiểm tra tính năng kerning không bị hỏng trong font COPY.

### Dữ liệu quan sát trong font thử

- 878 glyphs; 138 Native classes; 134 Vietnamese candidates.
- Một thời điểm có 174 đề xuất membership ở 21 class; sau khi thêm 6 thành viên vào 2 class và Save/Reopen, còn 168 đề xuất.
- Bài kiểm thử GUI V2 tại thời điểm chốt: 17/17 offline tests PASS. Những bài kiểm thử sau đó được mở rộng ở V3.

### FontLab 9 — giới hạn chưa giải quyết

- Native reader/discovery/preview đã hoạt động; writer **khóa**.
- `fgKerning.addGroup`/`fgGroup` gặp vấn đề chữ ký/kiểu đối số; `fgKerningGroups` không hỗ trợ `__setitem__` trong thử nghiệm.
- TypeRig không tìm thấy trong môi trường FL9 thử nghiệm. **Không suy diễn** API ghi từ FL8 sang FL9.

### Quyết định kiến trúc

**Hợp nhất giao diện, không hợp nhất Native Core và OT Core.** Mỗi bên có scanner, dữ liệu, safety gate và writer riêng. Đối chiếu phải rõ bên trái/phải và không tự cập nhật class chỉ dựa vào tên.

---

## 17/11/2026 — Khởi đầu Native + OpenType V1

- Vietnamese Kerning Assistant V1 đọc text `kern` và bổ sung glyph vào các **OpenType class đã tồn tại**; đã từng test 154 membership ở 17 class trên font COPY, sau readback và Save/Reopen không còn gợi ý trong lần thử đó.
- GUI V1 dùng PythonQt, tạo FEA backup/diff và báo cáo JSON. V1 **không** ghi trực tiếp Native classes.
- Native reader ban đầu chỉ đọc được 50 class (24 trái, 26 phải) trên trạng thái font lúc đó; số liệu về sau tăng lên 138 class ở font khác/trạng thái khác.
- Các probe đầu tiên với `fgKerning.addGroup` và `fgGroup` gặp lỗi kiểu dữ liệu; thử nghiệm writer khi đó chỉ dùng font tạm trong bộ nhớ.
- Nhận ra `Create [kern] Feature` hoặc `Update all auto features` có thể tái tạo OT từ Native, làm những chỉnh sửa OT cũ biến mất. Đây là hành vi FontLab phải tính đến trong workflow.

---

## Hợp đồng an toàn — Không bỏ khi phát triển tiếp

1. **Read-only là read-only:** Scan, Preview và Cross-check không được thay đổi font.
2. **Ghi chỉ trên COPY:** font đã lưu, có bản backup độc lập. Không dùng font client gốc để thử API.
3. **Kiểm tra lại trước khi ghi:** font/master, số master, glyph, nhóm Native, pair values, text `kern`, lựa chọn, trạng thái feature; nếu khác với lúc duyệt thì chặn và yêu cầu kiểm tra lại.
4. **Tác vụ ghi có xác nhận:** kế hoạch xem trước → kiểm tra an toàn → xác nhận người dùng → ghi → đọc lại. Writer OT còn yêu cầu backup `.fea` mới.
5. **Không tự Save/Compile:** chỉ thay đổi trong bộ nhớ; người dùng Save bản COPY sau khi kết quả được xác minh.
6. **Readback lỗi hoặc ghi một phần:** cảnh báo **DO NOT SAVE**, đóng bản COPY không lưu, điều tra nguyên nhân. Không giả định có rollback tự động.
7. **Không gộp writer:** Native và OpenType có đường ghi riêng; thay đổi class không được tự sửa POS/pair values.
8. **FontLab 9 writer vẫn khóa** cho đến khi có test API thực tế và readback đủ tin cậy.
9. **Giới hạn parser:** Cross-check hiện chỉ hiểu các khai báo class và `pos` đơn giản trong text `kern`, chưa bao phủ GPOS biên dịch và cú pháp FEA đầy đủ.
10. **Bảo mật:** báo cáo, file `.fea` và ảnh lỗi có thể chứa glyph names, class lists, đường dẫn và dữ liệu font client; kiểm tra trước khi đưa lên GitHub công khai.

## Backlog — Sau Kerning Studio

| Hướng | Phạm vi dự kiến | Trạng thái |
| --- | --- | --- |
| **OpenType Studio** | Duyệt classes, features, lookup GSUB/GPOS; kiểm tra thiếu/trùng và tham chiếu | Chưa xây hoàn chỉnh |
| **Accented Alternates** | Từ `A.ss01` có anchor, đề xuất composite `Aacute.ss01`, `Abreveacute.ss01`… với công thức để FontLab tự ghép | Ý tưởng đã thống nhất, chưa triển khai |
| **Ligatures** | Hỗ trợ xây các biến thể có dấu cho ligature khi thật sự hợp lý | Cần thiết kế quy tắc |
| **Glyph Matrix** | Kiểm tra encoding, Unicode, glyph thiếu và hỗ trợ tự tổ chức bộ ký tự | Đang lên kế hoạch |
| **Language Coverage** | Quét hỗ trợ ngôn ngữ, chỉ ra glyph thiếu và liên kết tiêu chuẩn Unicode | Đang lên kế hoạch |
| **FontLab 9** | Khảo sát và xác minh writer riêng | Khóa ghi, ưu tiên sau |

**Nguyên tắc sản phẩm:** Hybrid — tận dụng khả năng sẵn có của FontLab, chỉ đơn giản hóa thao tác phức tạp/lặp lại và cung cấp hướng dẫn dễ hiểu; không xây lại FontLab.

## Mẫu cho lần ghi tiếp theo

```markdown
## DD/MM/YYYY — Tên công việc

### Đã hoàn thành
- ...

### Đã test (nêu rõ FontLab thực tế hay offline)
- ...

### Lỗi / giới hạn
- ...

### Bước tiếp theo
- ...
```
