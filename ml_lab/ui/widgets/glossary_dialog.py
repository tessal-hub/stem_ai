"""
ml_lab/ui/widgets/glossary_dialog.py — Sổ Tay Thuật Ngữ & Cẩm Nang Sư Phạm STEM AI (ML Glossary).

Tài liệu tra cứu toàn bộ khái niệm trong ML Lab: đặc trưng, chia dữ liệu,
học vẹt, kiểm tra chéo, 15 thuật toán theo 4 họ, tăng cường dữ liệu, đường cong
dữ liệu, độ chắc chắn, triển khai vi điều khiển và hồ sơ mô hình.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
import ml_lab.ui.lab_style as ls
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


GLOSSARY_TOPICS = [
    ("Tổng quan", "intro", """
<h2>Chào mừng đến với STEM ML Lab</h2>
<p><b>ML Lab</b> là phòng thí nghiệm học máy giúp bạn đi qua toàn bộ quy trình của một kỹ sư AI thực thụ, trên chính dữ liệu vung wand của mình:</p>
<ol>
  <li><b>Xem dữ liệu đã ghi</b> — khám phá đặc trưng, tạo thêm dữ liệu mẫu.</li>
  <li><b>Huấn luyện máy</b> — chọn 1 trong 15 thuật toán, đọc chẩn đoán của AI Coach.</li>
  <li><b>Thử tham số</b> — tìm cài đặt tốt nhất, trả lời "cần bao nhiêu dữ liệu?"</li>
  <li><b>So sánh 15 thuật toán</b> — xếp hạng chính xác, tốc độ, RAM.</li>
  <li><b>Thử nhanh &amp; nạp lên wand</b> — giả lập What-If, xuất mã C++, nạp 1-click.</li>
  <li><b>Kết nối wand</b> — thi triển thật và thử mô hình trực tiếp trên máy.</li>
</ol>
<p><b>Mẹo cho người mới:</b> bật "Chế độ Người mới bắt đầu" ở tab 2, hoặc bấm "Để máy tự chọn giúp bạn" để máy thử 11 mô hình nhẹ và chọn giúp bạn.</p>
"""),

    ("Đặc trưng (Feature Engineering)", "features", """
<h2>Trích Xuất Đặc Trưng (Feature Engineering) là gì?</h2>
<p>Cảm biến wand ghi 50 mẫu mỗi giây, mỗi mẫu 6 trục (a_x, a_y, a_z, g_x, g_y, g_z). Trong ~1.3 giây vung, có tới <b>384 con số thô</b>!</p>
<p>Đưa thẳng 384 số vào máy học cổ điển thì quá nhiều chiều và nhiều nhiễu. Thay vào đó, ta nén thành <b>63 đặc trưng thống kê</b>:</p>
<h3>Các nhóm đặc trưng:</h3>
<ul>
  <li><b>Trung bình (mean)</b> — hướng nghiêng và trọng lực cơ bản.</li>
  <li><b>Độ dao động (std)</b> — vung mạnh hay nhẹ.</li>
  <li><b>Nhỏ nhất / lớn nhất / biên độ quét (min, max, range)</b> — biên độ dao động lớn nhất.</li>
  <li><b>Cường độ (RMS) &amp; năng lượng (energy)</b> — tổng cường độ chuyển động.</li>
  <li><b>Tần suất đổi chiều (ZCR)</b> — nhận biết vung zíc zắc.</li>
  <li><b>Độ lớn tổng hợp (|a|, |g|)</b> — cường độ không phụ thuộc góc cầm wand.</li>
  <li><b>Phối hợp trục &amp; giật (az·gx, jerk)</b> — sự phối hợp giữa động tác và xoay cổ tay.</li>
</ul>
<p><b>Cách nhận biết đặc trưng tốt:</b> mở tab 1, xem phân phối — hai màu lớp tách rời nhau là đặc trưng tốt; trộn vào nhau là đặc trưng vô dụng.</p>
"""),

    ("Tập học & tập kiểm tra", "split", """
<h2>Tập Học (Train) &amp; Tập Kiểm Tra (Validation)</h2>
<p>Phải giữ một phần dữ liệu mà máy <b>chưa từng thấy</b> khi học, để chấm bài trung thực. App chia theo tỷ lệ 80% học — 20% kiểm tra.</p>
<h3>Vì sao chia theo FILE chứ không chia theo cửa sổ?</h3>
<ul>
  <li>Dữ liệu vung được cắt thành các cửa sổ trượt có gối đầu lên nhau.</li>
  <li>Nếu chia ngẫu nhiên từng cửa sổ, các mảnh của <b>cùng một lần vung</b> sẽ rơi vào cả tập học lẫn tập kiểm tra → đề thi bị lộ → điểm cao giả tạo.</li>
  <li><b>Nguyên tắc của ML Lab</b>: toàn bộ cửa sổ từ một file CSV chỉ nằm trọn ở tập học HOẶC tập kiểm tra (Zero Data Leakage).</li>
</ul>
<p>Đây là lý do tab 1 đếm "Số mẫu" theo file ghi, và mọi điểm số trong app đều tính trên dữ liệu chưa từng thấy.</p>
"""),

    ("Học vẹt & học thiếu", "bias_variance", """
<h2>Học Vẹt (Overfitting) &amp; Học Thiếu (Underfitting)</h2>
<p>Nguyên lý quan trọng nhất giải thích vì sao mô hình dự đoán sai:</p>
<h3>1. Học thiếu (Underfitting)</h3>
<ul>
  <li>Mô hình <b>quá đơn giản</b> (cây depth 1, C quá nhỏ).</li>
  <li><b>Dấu hiệu</b>: cả điểm train lẫn điểm mới đều thấp (&lt;70%).</li>
  <li><b>Thuốc</b>: tăng độ phức tạp, đổi thuật toán mạnh hơn.</li>
</ul>
<h3>2. Học vẹt (Overfitting)</h3>
<ul>
  <li>Mô hình <b>quá phức tạp</b> (cây quá sâu, K=1).</li>
  <li>Máy nhớ cả nhiễu rung tay vô ý của người ghi.</li>
  <li><b>Dấu hiệu</b>: điểm train ~100% nhưng điểm mới tụt dốc.</li>
  <li><b>Thuốc</b>: giảm depth/K, bật nhân bản dữ liệu ×3, ghi thêm mẫu đa dạng.</li>
</ul>
<h3>3. Điểm cân bằng (Sweet Spot)</h3>
<p>Đỉnh của đường điểm-mới trên biểu đồ tab 3 — nơi mô hình tổng quát hóa tốt nhất.</p>
"""),

    ("Kiểm tra chéo (Cross-Validation)", "cv", """
<h2>Kiểm Tra Chéo 5 Lần (5-Fold Cross-Validation)</h2>
<p>Chia dữ liệu học thành 5 phần bằng nhau. Huấn luyện 5 lần: mỗi lần dùng 4 phần để học, 1 phần còn lại làm đề kiểm tra. Điểm cuối là trung bình 5 lần.</p>
<h3>Vì sao cần?</h3>
<ul>
  <li>Một lần chia dữ liệu ngẫu nhiên có thể may rủi: dễ quá hoặc khó quá.</li>
  <li>Kiểm tra chéo cho biết mô hình <b>ổn định</b> hay chỉ <b>may mắn</b> với một kiểu chia cụ thể.</li>
</ul>
<h3>Đọc kết quả "95.1% ± 1.5%":</h3>
<ul>
  <li><b>± nhỏ</b> (dưới ~3%): mô hình ổn định, tin được.</li>
  <li><b>± lớn</b> (trên ~12%): dữ liệu ít hoặc lệch lớp — hãy ghi thêm mẫu đều cho từng thần chú.</li>
</ul>
"""),

    ("Ma trận nhầm lẫn", "confusion_matrix", """
<h2>Ma Trận Nhầm Lẫn (Confusion Matrix)</h2>
<p>Bảng thống kê chi tiết các trường hợp đoán đúng và đoán sai trên tập kiểm tra:</p>
<ul>
  <li><b>Hàng ngang</b>: thần chú thực tế đã vung.</li>
  <li><b>Cột dọc</b>: thần chú máy dự đoán.</li>
  <li><b>Đường chéo</b>: đoán đúng — càng đậm càng tốt.</li>
  <li><b>Ô ngoài chéo</b>: nhầm lẫn. Ví dụ: vung Lumos nhưng máy đoán Nox.</li>
</ul>
<p><b>Mẹo:</b> nếu 2 thần chú hay nhầm nhau, hãy xem tab "Lớp nào yếu?" và thí nghiệm A/B, hoặc ghi thêm 2 cử chỉ đó khác biệt hơn (to hơn, chậm hơn).</p>
"""),

    ("KNN & Nearest Centroid", "knn", """
<h2>K-Láng Giềng Gần Nhất (KNN) &amp; Nearest Centroid</h2>
<h3>KNN — so với những ví dụ đã học</h3>
<ol>
  <li>Lưu toàn bộ mẫu cử chỉ vào bộ nhớ.</li>
  <li>Cử chỉ mới đến: tính khoảng cách tới tất cả mẫu đã học.</li>
  <li>Chọn K mẫu gần nhất, bỏ phiếu theo đa số.</li>
</ol>
<p><b>K nhỏ</b> (1-2): nhạy, dễ bị điểm nhiễu dẫn dắt. <b>K lớn</b> (7-15): ổn định nhưng ranh giới mờ.</p>
<h3>Nearest Centroid — so với "khuôn mẫu"</h3>
<p>Mỗi lớp chỉ giữ một <b>điểm đại diện trung bình</b> (centroid). Cử chỉ mới thuộc lớp có tâm gần nhất. Cực nhẹ và nhanh, hợp vi điều khiển.</p>
"""),

    ("Họ cây: Tree, Forest, Extra Trees", "tree_family", """
<h2>Họ Cây Quyết Định: Tree, Forest, Extra Trees</h2>
<h3>Cây Quyết Định (Decision Tree)</h3>
<p>Chuỗi câu hỏi if-else: <i>"Gia tốc Z ≤ 1.45?" → Đúng rẽ trái, Sai rẽ phải.</i> Dễ giải thích nhất, suy luận ~0.04ms trên ESP32.</p>
<p><b>Gini</b> đo độ hỗn loạn của nhóm (0 = tinh khiết, 0.5 = trộn 50-50). Máy chọn câu hỏi giúp giảm Gini nhiều nhất.</p>
<h3>Random Forest — bỏ phiếu đa số</h3>
<p>Nhiều cây độc lập, mỗi cây học trên tập mẫu con ngẫu nhiên. Cử chỉ mới: tất cả cây bỏ phiếu, lớp nhiều phiếu thắng. Ổn định hơn cây đơn rất nhiều.</p>
<h3>Extra Trees — ngẫu nhiên hơn nữa</h3>
<p>Giống Forest nhưng điểm chia cũng ngẫu nhiên hóa — thường ít học vẹt hơn, nhanh hơn.</p>
<h3>GBDT &amp; AdaBoost — sửa sai tuần tự</h3>
<p>Khác Forest (cây song song bỏ phiếu): GBDT/AdaBoost xây cây <b>tuần tự</b>, cây sau tập trung sửa lỗi của cây trước. Chính xác cao với ít cây, nhưng dễ học vẹt nếu quá nhiều vòng.</p>
"""),

    ("Họ tuyến tính: Logistic, Ridge, SGD, LDA, SVM", "linear_family", """
<h2>Họ Ranh Giới Phẳng: Logistic, Ridge, SGD, LDA, SVM</h2>
<h3>Hồi quy Logistic &amp; Softmax</h3>
<p>Tính điểm mỗi lớp: <b>z = W·x + b</b>, rồi biến thành xác suất qua Softmax. Trọng số W dương lớn = đặc trưng đó ủng hộ lớp đó — có thể xem trực tiếp ở tab "Bên trong mô hình".</p>
<h3>Ridge Classifier</h3>
<p>Giống logistic nhưng thêm phạt giữ trọng số nhỏ — rất ổn định với dữ liệu ít.</p>
<h3>SGD Classifier</h3>
<p>Cùng ý tưởng logistic nhưng học theo từng bước nhỏ — nhanh với dữ liệu lớn.</p>
<h3>LDA (Linear Discriminant Analysis)</h3>
<p>Tìm phép chiếu sao cho các tâm lớp cách nhau xa nhất. Co nhỏ thống kê (shrinkage) giúp chịu được dữ liệu ít.</p>
<h3>SVM — Max Margin</h3>
<p>Tìm siêu phẳng có khoảng cách xa nhất tới các điểm sát ranh giới (Support Vectors). Với dữ liệu không tách được bằng phẳng, kernel RBF "uốn cong" không gian. C lớn = nghiêm khắc (dễ vẹt); gamma nhỏ = ranh giới mượt.</p>
"""),

    ("Họ thống kê: GNB & QDA", "stat_family", """
<h2>Họ Thống Kê: Gaussian NB &amp; QDA</h2>
<h3>Gaussian Naive Bayes (GNB)</h3>
<p>Với mỗi lớp, học phân phối hình chuông (trung bình + phương sai) của từng đặc trưng, giả định các trục độc lập. Học gần như tức thì, suy luận dưới 0.01ms — hợp dữ liệu ít.</p>
<h3>QDA (Quadratic Discriminant Analysis)</h3>
<p>Giống GNB nhưng học cả <b>hình dạng trải</b> (ma trận hiệp phương sai) của từng lớp → ranh giới cong tự nhiên. Cần nhiều dữ liệu hơn GNB; tham số reg_param làm mịn khi dữ liệu ít.</p>
"""),

    ("Mạng nơ-ron (MLP)", "mlp", """
<h2>Mạng Nơ-ron Tầng Nông (Shallow MLP)</h2>
<p>Cầu nối sang Deep Learning: 63 đặc trưng → tầng ẩn (16 ô tính, kích hoạt ReLU) → tầng ra (Softmax theo số lớp).</p>
<h3>Các cài đặt chính:</h3>
<ul>
  <li><b>Số ô tính trung gian</b>: nhiều = học được quy luật phức tạp hơn nhưng dễ học vẹt và chậm hơn.</li>
  <li><b>Tốc độ học</b>: bước đi khi sửa trọng số. Lớn quá = nhảy loạn; nhỏ quá = học mãi không xong.</li>
  <li><b>Alpha</b>: phạt trọng số lớn — chống học vẹt.</li>
</ul>
<p>Trên ESP32, MLP chạy bằng thuần C++ (nhân ma trận + ReLU) — không cần TensorFlow.</p>
"""),

    ("Siêu tham số", "hyperparams", """
<h2>Siêu Tham Số (Hyperparameters)</h2>
<p>Phân biệt hai loại:</p>
<ul>
  <li><b>Tham số</b>: máy tự học trong lúc huấn luyện (trọng số W, ngưỡng if-else).</li>
  <li><b>Siêu tham số</b>: cài đặt bạn chọn <b>trước khi</b> huấn luyện — "độ khó" của bài học.</li>
</ul>
<h3>Vài siêu tham số hay gặp:</h3>
<ul>
  <li><b>K</b> (KNN): số láng giềng bỏ phiếu.</li>
  <li><b>Độ sâu (depth)</b> (cây): số câu hỏi tối đa.</li>
  <li><b>C</b> (SVM/Logistic): độ nghiêm khắc — lớn = bám sát dữ liệu (dễ vẹt), nhỏ = mượt.</li>
  <li><b>Learning rate</b> (GBDT/MLP/AdaBoost): bước đi mỗi lần sửa sai.</li>
  <li><b>Alpha</b> (Ridge/MLP/SGD): mức phạt mô hình phức tạp.</li>
</ul>
<p><b>Mẹo:</b> đừng đoán — dùng tab 3 để quét thử từng giá trị, hoặc bấm "Để máy tự chọn giúp bạn" ở tab 2.</p>
"""),

    ("Tăng cường dữ liệu", "augmentation", """
<h2>Tăng Cường Dữ Liệu (Data Augmentation)</h2>
<p>Nhân bản mẫu đã ghi kèm biến đổi nhẹ để giả lập nhiều lần vung khác nhau:</p>
<ul>
  <li><b>Nhiễu rung tay</b>: thêm nhiễu nhỏ theo độ dao động của từng kênh.</li>
  <li><b>Co giãn biên độ</b>: mô phỏng vung mạnh/yếu hơn.</li>
  <li><b>Biến dạng nhịp (time-warp)</b>: mô phỏng vung nhanh/chậm hơn.</li>
</ul>
<h3>Quy tắc vàng:</h3>
<p>Chỉ nhân bản <b>tập học</b>. Tập kiểm tra luôn giữ nguyên — nếu nhân bản cả tập kiểm tra thì đó là gian lận điểm.</p>
<p><b>Kiểm chứng bằng thí nghiệm A/B</b> (tab 1): huấn luyện 2 mô hình giống hệt nhau — một học dữ liệu gốc, một học dữ liệu nhân bản ×3 — cùng làm một bài kiểm tra. Kết quả thắng/thua/hòa đều là kết luận khoa học có số liệu.</p>
"""),

    ("Cần bao nhiêu dữ liệu?", "data_curve", """
<h2>Cần Bao Nhiêu Dữ Liệu? (Learning Curve)</h2>
<p>Câu hỏi hay gặp nhất: "Em nên ghi thêm mẫu nữa không?" — đừng đoán, hãy thí nghiệm.</p>
<p><b>Cách làm</b> (tab 3): huấn luyện cùng một mô hình với 25% → 50% → 75% → 100% dữ liệu học, đánh giá trên cùng một tập kiểm tra.</p>
<h3>Đọc biểu đồ:</h3>
<ul>
  <li>Đường điểm-mới <b>còn tăng</b> ở 100% → ghi thêm mẫu sẽ có lợi.</li>
  <li>Đường <b>đã phẳng</b> → dữ liệu đủ; hãy cải thiện chất lượng (đa dạng cách vung) thay vì số lượng.</li>
  <li>Đường train và mới cách xa nhau → vấn đề là học vẹt, không phải thiếu dữ liệu.</li>
</ul>
"""),

    ("Độ chắc chắn", "confidence", """
<h2>Độ Chắc Chắn (Confidence)</h2>
<p>Mô hình luôn kèm phần trăm chắc chắn (qua hàm Softmax). Nguyên tắc đọc:</p>
<ul>
  <li><b>Trên 90%</b>: mô hình rất tự tin — thường đáng tin nếu mô hình tốt.</li>
  <li><b>60–90%</b>: vùng mơ hồ — nên vung lại lần nữa để xác nhận.</li>
  <li><b>Dưới 60%</b>: coi như đoán mò — đừng tin.</li>
</ul>
<p><b>Quan trọng:</b> chắc cao KHÔNG có nghĩa là đúng. Một mô hình học vẹt có thể "chắc" 99% mà vẫn sai. Độ chắc chắn chỉ có ý nghĩa khi mô hình đã được kiểm chứng trên dữ liệu mới.</p>
"""),

    ("Triển khai lên vi điều khiển", "mcu", """
<h2>Triển Khai Lên Vi Điều Khiển (ESP32)</h2>
<p>Mô hình học xong được tự động "dịch" sang mã C thuần (model_classic.h + .cc):</p>
<ul>
  <li><b>Zero malloc</b> — không cấp phát bộ nhớ động, an toàn trên chip.</li>
  <li><b>Header-only, C99</b> — biên dịch được bằng ESP-IDF lẫn Arduino.</li>
  <li><b>Suy luận &lt;0.05ms</b> với hầu hết mô hình — nhanh hơn một cái chớp mắt 5000 lần.</li>
</ul>
<h3>Ràng buộc phần cứng:</h3>
<p>Chip chỉ có vài trăm KB RAM/Flash — nên bảng so sánh có cột RAM và Flash. Mô hình chính xác 99% nhưng nặng 500KB là vô dụng trên wand. Đây là lý do "mô hình nhỏ mà chuẩn" đáng giá hơn "lớn mà chính xác".</p>
"""),

    ("Hồ sơ mô hình (Model Card)", "model_card", """
<h2>Hồ Sơ Mô Hình (Model Card) — AI Có Trách Nhiệm</h2>
<p>Mỗi mô hình sau khi huấn luyện có thể tự sinh một trang tài liệu (nút "Xem hồ sơ mô hình" ở tab 2) mô tả:</p>
<ul>
  <li>Mô hình làm gì, huấn luyện lúc nào, trên dữ liệu nào.</li>
  <li>Độ chính xác tổng thể và <b>từng lớp</b>.</li>
  <li><b>Khi nào KHÔNG nên tin</b>: lớp yếu dưới 75%, dấu hiệu học vẹt, điểm kiểm tra chéo dao động, chắc chắn dưới 60%, người vung khác người ghi.</li>
  <li>Gợi ý cải thiện cụ thể cho từng lớp.</li>
</ul>
<p>Đây là thói quen của kỹ sư AI chuyên nghiệp: mọi mô hình triển khai thật đều cần "giấy khai sinh" ghi rõ điểm mạnh, điểm yếu và giới hạn. Xuất PDF để nộp bài hoặc lưu portfolio.</p>
"""),
]


class GlossaryDialog(QDialog):
    """Hộp thoại Sổ Tay Thuật Ngữ — tra cứu toàn bộ khái niệm trong ML Lab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sổ tay thuật ngữ — STEM ML Lab")
        self.resize(920, 640)
        self.setStyleSheet(f"GlossaryDialog {{ background: {ls.BG_APP}; }}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        head_box = QFrame()
        head_box.setStyleSheet(
            f".QFrame {{ background: {ls.ACCENT_TINT}; border: none; border-radius: {ls.RADIUS_MD}px; padding: 6px 12px; }}"
        )
        h_layout = QHBoxLayout(head_box)
        lbl_h = QLabel("SỔ TAY THUẬT NGỮ & CẨM NANG HỌC MÁY")
        lbl_h.setStyleSheet(f"{ls.font(14, 800)} color: {ls.ACCENT}; border: none; background: transparent;")
        h_layout.addWidget(lbl_h)
        h_layout.addStretch()
        main_layout.addWidget(head_box)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.topic_list = QListWidget()
        self.topic_list.setStyleSheet(
            f"QListWidget {{ border: 1px solid {ls.BORDER}; border-radius: {ls.RADIUS_MD}px; font-weight: 600; font-size: 12px; }} "
            f"QListWidget::item {{ padding: 10px; border-bottom: 1px solid {ls.BORDER}; }} "
            f"QListWidget::item:selected {{ background: {ls.ACCENT}; color: white; border-radius: 4px; }}"
        )
        for title, key, _ in GLOSSARY_TOPICS:
            self.topic_list.addItem(title)
        self.topic_list.currentRowChanged.connect(self._on_topic_selected)
        splitter.addWidget(self.topic_list)

        self.content_browser = QTextBrowser()
        self.content_browser.setStyleSheet(
            f"QTextBrowser {{ border: 1px solid {ls.BORDER}; border-radius: {ls.RADIUS_MD}px; padding: 16px; "
            f"background: white; color: {ls.INK}; font-size: 13px; line-height: 1.6; }}"
        )
        splitter.addWidget(self.content_browser)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        main_layout.addWidget(splitter, stretch=1)

        btn_close = QPushButton("Đóng sổ tay")
        btn_close.setStyleSheet(ls.BTN_SECONDARY)
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        self.topic_list.setCurrentRow(0)

    def _on_topic_selected(self, row: int) -> None:
        if 0 <= row < len(GLOSSARY_TOPICS):
            _, _, html_content = GLOSSARY_TOPICS[row]
            self.content_browser.setHtml(
                f"<html><body style='color: {ls.INK};'>{html_content}</body></html>"
            )
