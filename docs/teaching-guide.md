# Giáo Trình Dạy Học — STEM ML Lab

> Tài liệu dành cho người dạy. Toàn bộ khái niệm đều gắn với một màn hình cụ thể
> trong ML Lab — nguyên tắc giảng: **mỗi khái niệm = 1 hành động tay + 1 con số
> trên màn hình + 1 câu hỏi cho lớp**. Không giảng lý thuyết khô.

---

## Phần A. Bản đồ khái niệm — thứ tự giảng

### 1. Phân lớp (classification)
- **Một câu**: Máy nhận dữ liệu vào và chọn 1 đáp án trong danh sách có sẵn.
- **Ví dụ**: Hộp thư có sẵn các ngăn; lá thư mới bỏ vào đúng một ngăn.
- **Chỉ vào**: Tab 2 — combo thuật toán + nút "Huấn luyện & đánh giá".
  Đầu vào: 63 con số; đầu ra: 1 tên thần chú.

### 2. Đặc trưng (features) — khái niệm quan trọng nhất
- **Một câu**: Thay vì đưa 384 số cảm biến thô vào máy, ta nén thành 63 con số
  thống kê có ý nghĩa (trung bình, dao động, năng lượng...).
- **Ví dụ**: Nhận diện bạn bè không đo từng lỗ chân lông — nhìn "chiều cao,
  giọng nói, kiểu tóc".
- **Chỉ vào**: Tab 1 — chọn "Gia tốc X · trung bình", xem histogram:
  **màu tách nhau = đặc trưng tốt; trộn nhau = đặc trưng vô dụng**.
- **Câu hỏi kiểm tra**: "Tại sao không đưa 384 số thô luôn?" — Vì quá nhiều
  chiều và máy không biết đâu là ý nghĩa; thống kê là bản tóm tắt.

### 3. Tập học / tập kiểm tra (train/validation)
- **Một câu**: Phải giữ một phần dữ liệu mà máy **chưa từng thấy** để chấm bài
  trung thực.
- **Ví dụ**: Luyện với 80% đề, thi bằng 20% đề chưa thấy. Lấy chính đề luyện ra
  thi = điểm ảo.
- **Chỉ vào**: Tab 2 — nhãn "ĐOÁN ĐÚNG TRÊN DỮ LIỆU MỚI".
- **Điểm dạy hay**: App chia theo **FILE** (toàn bộ cửa sổ trượt từ 1 lần ghi
  thuộc cùng 1 tập) — vì các cửa sổ từ cùng file gần giống nhau, chia lẫn = rò
  rỉ dữ liệu. Mở tab 1, chỉ cột "Số mẫu đã ghi" đếm theo file.

### 4. Học vẹt (overfitting) & học thiếu (underfitting)
- **Một câu**: Học vẹt = thuộc bài cũ, làm bài mới kém; học thiếu = đến bài cũ
  còn làm sai.
- **Chỉ vào**: Tab 2 — "MỨC ĐỘ HỌC VỆT" (chênh lệch train − validation).
- **Demo sống**: Decision Tree depth 8 (train ~99%, val tụt) rồi depth 3 (hai
  điểm gần nhau). Học sinh tự nhìn thấy.
- **Cách nhớ**: Gap lớn = vẹt. Train thấp = lười học.

### 5. Kiểm tra chéo (cross-validation)
- **Một câu**: Chia dữ liệu học thành 5 phần, luân phiên để 1 phần làm đề kiểm
  tra — đo xem điểm có ổn định không.
- **Ví dụ**: Thi 5 lần liên tiếp; điểm dao động mạnh = chưa tin được.
- **Chỉ vào**: "KIỂM TRA CHÉO (5 LẦN)" — dạng `85% ± 3%`. ± nhỏ = tin được;
  ± lớn = dữ liệu ít hoặc lệch lớp.
- **Trả lời câu hỏi kinh điển** "sao 2 lần train ra 2 kết quả?": chia dữ liệu
  ngẫu nhiên — CV chính là cách đo mức dao động đó.

### 6. Ma trận nhầm lẫn
- **Một câu**: Bảng cho biết máy nhầm **ai với ai** nhiều nhất — không chỉ sai
  bao nhiêu.
- **Đọc**: đường chéo = đúng; ô ngoài chéo: hàng = thật, cột = máy đoán.
- **Chỉ vào**: Tab 2 → "Kết quả & AI Coach". AI Coach tự gọi tên cặp nhầm
  ("B hay nhầm thành P") — hành động theo nó: ghi thêm 2 cử chỉ đó **khác biệt
  hơn**.

### 7. 15 thuật toán — dạy theo 4 "tính cách", không dạy công thức

| Họ | Thành viên | Trực giác | Điểm mạnh/yếu |
|---|---|---|---|
| So khoảng cách | KNN, Nearest Centroid | "Cử chỉ mới giống những cử chỉ đã học nhất" | Đơn giản; KNN chậm nếu nhiều mẫu |
| Họ câu hỏi if-else | Tree, Forest, Extra Trees, GBDT, AdaBoost | "Chuỗi câu hỏi có/không dẫn đến phán quyết" | Nhanh trên chip, dễ giải thích; cây đơn dễ vẹt |
| Họ ranh giới phẳng | Logistic, Ridge, SGD, SVM-tuyến tính, LDA | "Vẽ một mặt phẳng chia hai bên" | Nhẹ nhất, nhanh nhất; chỉ tách được dữ liệu tuyến tính |
| Họ phân phối | GNB, QDA | "Học hình dạng phân phối từng lớp" | Học nhanh từ ít mẫu; QDA cho ranh giới cong |
| Nơ-ron | MLP | "Nhiều ô tính nhỏ ghép lại" | Mạnh nhất nhưng nặng, dễ vẹt, hộp đen |

- **Cách dạy**: Tab 4 (So sánh 15 thuật toán) → bấm chạy ~18 giây → đọc bảng
  xếp hạng cùng nhau.
- **Câu thần chú**: "Không có mô hình tốt nhất — chỉ có mô hình phù hợp nhất
  với dữ liệu và con chip của bạn."

### 8. Siêu tham số — cài đặt chọn trước khi học
- **Một câu**: Siêu tham số là "cài đặt khó độ" chọn trước khi học; tham số
  (trọng số) là máy tự học trong lúc học.
- **Ví dụ**: K = số người bỏ phiếu; Depth = số câu hỏi tối đa; C = độ nghiêm
  khắc.
- **Quy luật chung dạy**: **càng phức tạp càng dễ học vẹt**.

### 9. Bias-Variance / Sweet Spot
- **Một câu**: Quét một cài đặt từ thấp đến cao, tìm điểm dữ liệu mới đạt đỉnh —
  cân bằng giữa học thiếu và học vẹt.
- **Chỉ vào**: Tab 3 — đường xám (bài cũ, luôn tăng) vs đường xanh dương (bài
  mới, hình vòm); **cột xanh lá = chọn**.
- **Bài tập lớp**: quét Tree depth 1→8, giải thích hình vòm.

### 10. Đường cong dữ liệu — "ghi thêm có đáng không?"
- **Một câu**: Train cùng mô hình với 25% → 100% dữ liệu; đường xanh còn tăng
  thì ghi thêm có lợi, đã phẳng thì dừng.
- **Chỉ vào**: Tab 3 — nút "Chạy thử: 25% → 100% dữ liệu".
- **Kết quả tham chiếu** (dataset 8 thần chú, 184 file): 77.9% → 77.9% → 77.9%
  → 85.2% — còn tăng ở 100% = nên ghi thêm.

### 11. Tăng cường dữ liệu (augmentation)
- **Một câu**: Nhân bản mẫu + thêm nhiễu nhẹ = giả lập nhiều lần vung khác
  nhau; **chỉ làm trên tập học**.
- **Cảnh báo bắt buộc**: tuyệt đối KHÔNG nhân bản tập kiểm tra — đó là gian lận
  điểm. Tool đã cài đúng (validation giữ nguyên).
- **Demo**: Tab 1 → "Tạo thêm dữ liệu mẫu" → thí nghiệm A/B gốc vs nhân bản →
  đọc kết luận (thắng/thua/hòa đều là kết luận khoa học hợp lệ).

### 12. Triển khai lên vi điều khiển
- **Một câu**: Mô hình học xong được "dịch" sang mã C thuần, không cần bộ nhớ
  động, nạp thẳng vào chip — mỗi lần đoán dưới 0.05ms.
- **Ràng buộc dạy**: chip chỉ có vài trăm KB — nên bảng so sánh có cột RAM/Flash.
  Chính xác 99% mà nặng 500KB = vô dụng trên wand.
- **Chỉ vào**: Tab 5 — "Nạp lên wand"; Tab 7 — thi triển thật.

### 13. Độ chắc chắn (confidence)
- **Một câu**: Mô hình luôn kèm % chắc chắn — chắc cao không có nghĩa là đúng,
  nhưng chắc thấp là tín hiệu đừng tin.
- **Quy tắc dạy**: dưới ~60% coi như đoán mò.
- **Chỉ vào**: Tab 7 — "Chắc chắn 97%".

---

## Phần B. Kịch bản giảng 90 phút

| Phút | Hoạt động | Màn hình | Khái niệm |
|---|---|---|---|
| 0–10 | Mở app, vung wand xem stream | Tab 7 | Cảm biến → số liệu thô |
| 10–25 | Xem phân phối đặc trưng; hỏi "đặc trưng nào tách tốt nhất?" | Tab 1 | Đặc trưng |
| 25–40 | Train model đầu (chế độ Người mới) + đọc AI Coach | Tab 2 | Train/val, học vẹt |
| 40–55 | Demo học vẹt: depth 8 vs depth 3 | Tab 2 | Overfitting bằng mắt |
| 55–70 | Quét sweet spot + thử 25→100% dữ liệu | Tab 3 | Bias-variance, data efficiency |
| 70–80 | Arena 15 model + What-If slider | Tab 4, 5 | Đánh đổi, minh bạch mô hình |
| 80–90 | Nạp wand + thi triển thật | Tab 5, 7 | Triển khai + phần thưởng |

---

## Phần C. Câu hỏi học sinh hay gặp + câu trả lời mẫu

1. **"Train 100% mà validation 60% — máy dở à?"**
   → Không, máy đang học vẹt: thuộc đề cũ không bằng biết quy luật. Chỉ vào
   "MỨC ĐỘ HỌC VỆT".
2. **"Cần ghi bao nhiêu mẫu là đủ?"**
   → Đừng đoán — chạy tab 3 thử 25→100%. Đường còn tăng: ghi tiếp; phẳng: đủ.
3. **"Mô hình nào tốt nhất?"**
   → Tùy ràng buộc: nhanh + nhỏ (Tree, GNB) hay chính xác (Forest, MLP). Chạy
   tab 4 trên chính dữ liệu của em.
4. **"Máy có hiểu mình đang vung không?"**
   → Không. Nó thấy 63 con số thống kê và tìm quy luật số — như phân loại thư
   theo từ khóa mà không cần "hiểu" lá thư.
5. **"Sao lần sau train lại ra khác?"**
   → Chia dữ liệu + khởi tạo ngẫu nhiên. Vì thế có "Kiểm tra chéo" đo độ tin.
6. **"Sao tăng cường dữ liệu đôi khi làm tệ hơn?"**
   → Nhiễu quá mạnh làm loãng dữ liệu sạch. Mọi can thiệp đều phải thí nghiệm
   (thí nghiệm A/B tab 1).
7. **"Em ghi 1 lớp được không?"**
   → Không. Phân lớp cần ≥2 lớp để có "ranh giới".

---

## Phần D. Cạm bẫy khi đứng lớp

- **Chuẩn bị dataset mẫu trước** (2 lớp × 5 file): lớp chưa ghi gì thì mọi tab
  đều chặn đúng — nhưng đừng dạy tiết đầu trên màn hình trống.
- **Cử chỉ demo phải khác biệt rõ** (vung lên vs quét ngang). Hai cử chỉ giống
  nhau → confusion matrix chính là bài học, nhưng để dành tiết 2.
- **Đừng nạp QDA/MLP lớn lên chip khi demo** — dùng Tree/NB (nhỏ, nhanh).
- **Máy chiếu**: app thiết kế cho laptop 1-1; khi chiếu, phóng cửa sổ và dùng
  HUD tab 7 (chữ to).
- **Editor (VS Code/Cursor) mở cùng repo**: reload file trước khi sửa — buffer
  cũ có thể ghi đè thay đổi.

---

## Phần E. Bảng tra nhanh số liệu

| Thấy trên màn hình | Nghĩa là | Hành động |
|---|---|---|
| Val ≥ 85%, gap ≤ 5% | Sẵn sàng | Nạp lên wand |
| Gap > 15% | Học vẹt nặng | Giảm depth/K, bật nhân bản ×3 |
| Train < 65% | Học thiếu | Tăng độ phức tạp, đổi thuật toán |
| CV ± > 12% | Dữ liệu ít/lệch | Ghi thêm, đều mỗi lớp |
| Đường xanh còn tăng (tab 3) | Thiếu dữ liệu | Ghi thêm mẫu |
| Đường xanh phẳng | Đủ dữ liệu | Dừng ghi, tối ưu thứ khác |
| Chắc chắn < 60% | Đoán mò | Đừng tin kết quả đó |

---

## Phần F. Bài tập về nhà (kèm đáp án)

### Bài 1 — Tìm đặc trưng tách tốt (tab 1)
**Đề**: Ghi 2 thần chú, mỗi lớp ít nhất 5 mẫu. Tìm 3 đặc trưng có phân bố tách
rời nhất giữa 2 lớp. Chụp màn hình histogram + giải thích tại sao tách tốt.

**Đáp án hướng dẫn chấm**:
- Đặc trưng tốt = hai màu histogram **ít chồng nhau** (ví dụ thường gặp:
  `Xoay Y · lớn nhất`, `Gia tốc Z · biên độ quét` cho cử chỉ nhanh/chậm).
- Điểm cao: giải thích được *vì sao* (cử chỉ nhanh → vận tốc góc đỉnh cao hơn).
- Điểm thấp: chọn đặc trưng trộn nhau mà không nhận xét.

### Bài 2 — Săn học vẹt (tab 2)
**Đề**: Train Decision Tree với "Số câu hỏi tối đa" = 2, 4, 8. Lập bảng:
Train / Validation / Gap cho từng mức. Mức nào học thiếu, mức nào học vẹt, mức
nào cân bằng? Nêu mức em chọn và lý do.

**Đáp án hướng dẫn chấm**:
- depth 2: Train và Validation đều thấp → **học thiếu**.
- depth 8: Train rất cao, Validation tụt, Gap lớn → **học vẹt**.
- Mức cân bằng thường 3–5 (số chính xác phụ thuộc dataset — chấm theo cách đọc
  gap, không chấm theo con số cứng).
- Điểm cao: nêu được hành động tiếp theo (chọn mức vừa tìm để nạp).

### Bài 3 — Hai thí nghiệm, ba câu kết luận (tab 1 + tab 3)
**Đề**: (a) Chạy thử 25% → 100% dữ liệu. (b) Chạy thí nghiệm dữ liệu gốc vs dữ
liệu nhân bản ×3. Viết 3 câu kết luận có số liệu.

**Đáp án hướng dẫn chấm** (mọi kết luận đều chấp nhận được nếu có số):
- (a) Đường xanh còn tăng ở 100% → "ghi thêm mẫu có lợi"; đã phẳng → "dữ liệu
  đủ, nên cải thiện chất lượng thay vì số lượng".
- (b) Nhân bản thắng → "nhiều biến thể giúp tổng quát hóa"; thua → "nhiễu làm
  loãng dữ liệu sạch, nên giảm mức nhiễu"; hòa → "dữ liệu gốc đã đủ phong phú".
- Trừ điểm nếu kết luận không trích số liệu từ biểu đồ.

---

*Liên kết: xem `ml_lab/README.md` để biết cấu trúc kỹ thuật và cách chạy app.*
