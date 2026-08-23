"""
ml_lab/ui/widgets/glossary_dialog.py — Sổ Tay Thuật Ngữ & Cẩm Nang Sư Phạm STEM AI (ML Glossary).

Cung cấp tài liệu tra cứu trực quan, dễ hiểu về các khái niệm cốt lõi trong Học Máy:
Feature Engineering, Bias-Variance Trade-off, Confusion Matrix, 5 thuật toán Classic ML,
Zero Data Leakage và tối ưu hóa phần cứng nhúng MCU.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


GLOSSARY_TOPICS = [
    ("🌟 Tổng Quan", "intro", r"""
<h2>🔮 Chào mừng đến với STEM ML Lab</h2>
<p><b>ML Lab</b> là phòng thí nghiệm học máy chuyên sâu, giúp bạn khám phá <b>bản chất khoa học</b> của Trí tuệ nhân tạo thay vì chỉ coi AI là một "hộp đen".</p>
<p>Tại đây, bạn sẽ tự tay đi qua toàn bộ quy trình của một kỹ sư AI thực thụ:</p>
<ol>
  <li><b>Thu thập & Khám phá dữ liệu</b>: Phân tích tín hiệu cảm biến IMU 6 trục.</li>
  <li><b>Trích xuất đặc trưng (Feature Engineering)</b>: Biến dữ liệu chuỗi thời gian thành các chỉ số thống kê toán học.</li>
  <li><b>Huấn luyện & Mổ xẻ 5 thuật toán</b>: KNN, Decision Tree, Random Forest, SVM, Logistic Regression.</li>
  <li><b>Tối ưu Siêu tham số & Bias-Variance</b>: Khắc phục hiện tượng Quá khớp (Overfitting).</li>
  <li><b>Triển khai Phần cứng Nhúng</b>: Tự động sinh mã nguồn C99 chạy trực tiếp trên vi điều khiển ESP32 với tốc độ siêu thanh (&lt;0.05ms).</li>
</ol>
"""),

    ("📊 Đặc trưng (Feature Engineering)", "features", r"""
<h2>📊 Trích Xuất Đặc Trưng (Feature Engineering) là gì?</h2>
<p>Cảm biến MPU6050 ghi lại 50 mẫu mỗi giây, mỗi mẫu gồm 6 trục (a_x, a_y, a_z, g_x, g_y, g_z). Trong 1.28 giây, có tới <b>384 con số thô</b>!</p>
<p>Nếu đưa trực tiếp 384 con số này vào máy học cổ điển, dữ liệu sẽ quá nhiều chiều và chứa nhiều nhiễu rung lắc. Do đó, ta tính toán <b>48 đặc trưng cô đọng</b>:</p>

<h3>Các nhóm đặc trưng chính:</h3>
<ul>
  <li><b>Giá trị Trung bình (Mean)</b>: Xác định hướng nghiêng và trọng lực cơ bản của chiếc gậy phép.</li>
  <li><b>Độ lệch chuẩn (Standard Deviation)</b>: Đo mức độ biến động, vung vẩy mạnh hay nhẹ.</li>
  <li><b>Phạm vi (Range = Max - Min)</b>: Biên độ dao động lớn nhất trong suốt cú vung.</li>
  <li><b>Năng lượng (Energy / RMS)</b>: Tổng cường độ chuyển động của cử chỉ.</li>
  <li><b>Tần số đổi dấu (Zero-Crossing Rate)</b>: Đếm số lần tín hiệu đổi chiều (nhận biết cử chỉ zíc zắc, lắc gậy liên tục).</li>
  <li><b>Gia tốc tổng hợp (|a|) & Góc tổng hợp (|g|)</b>: Cường độ không phụ thuộc góc cầm gậy.</li>
  <li><b>Vi phân chéo (a_z * g_x, Jerk)</b>: Đo sự phối hợp giữa động tác chém xuống và xoay cổ tay.</li>
</ul>
"""),

    ("⚖️ Độ Lệch & Phương Sai (Bias-Variance)", "bias_variance", r"""
<h2>⚖️ Định Luật Đánh Đổi Độ Lệch - Phương Sai (Bias-Variance Trade-off)</h2>
<p>Đây là nguyên lý quan trọng nhất trong học máy giải thích vì sao mô hình có thể dự đoán sai:</p>

<h3>1. Hiện tượng Thiếu Khớp (Underfitting / High Bias):</h3>
<ul>
  <li>Xảy ra khi mô hình <b>quá đơn giản</b> (vd: Cây quyết định chỉ có độ sâu 1, hoặc hệ số phạt C quá nhỏ).</li>
  <li>Mô hình không học đủ quy luật cử chỉ.</li>
  <li><b>Dấu hiệu</b>: Cả <i>Train Accuracy</i> và <i>Validation Accuracy</i> đều thấp (&lt;70%).</li>
</ul>

<h3>2. Hiện tượng Quá Khớp / Học Vẹt (Overfitting / High Variance):</h3>
<ul>
  <li>Xảy ra khi mô hình <b>quá phức tạp</b> (vd: Cây quyết định quá sâu, hoặc KNN với K=1).</li>
  <li>Mô hình nhớ từng chi tiết nhỏ và học cả những rung lắc vô tình của người thu mẫu.</li>
  <li><b>Dấu hiệu</b>: <i>Train Accuracy</i> đạt gần 100% nhưng <i>Validation Accuracy</i> bị tụt dốc mạnh.</li>
</ul>

<h3>3. Điểm Cân Bằng Lý Tưởng (Sweet Spot):</h3>
<p>Là đỉnh cao nhất của đường Validation Score trên biểu đồ quét tham số. Tại đây, mô hình có khả năng <b>tổng quát hóa (Generalization)</b> tốt nhất trên những cử chỉ mới chưa từng gặp.</p>
"""),

    ("🎯 Ma Trận Nhầm Lẫn (Confusion Matrix)", "confusion_matrix", r"""
<h2>🎯 Ma Trận Nhầm Lẫn (Confusion Matrix)</h2>
<p>Ma trận nhầm lẫn là bảng thống kê chi tiết các trường hợp đoán đúng và đoán sai của mô hình trên tập kiểm thử (Validation Set):</p>

<ul>
  <li><b>Hàng ngang (Actual Class)</b>: Phép thuật thực tế người dùng đã thực hiện.</li>
  <li><b>Cột dọc (Predicted Class)</b>: Phép thuật mà mô hình AI dự đoán.</li>
  <li><b>Đường chéo chính (Màu Xanh lá)</b>: Các dự đoán <b>chính xác</b> (True Positives). Con số càng lớn thì mô hình càng giỏi!</li>
  <li><b>Các ô ngoài đường chéo (Màu Đỏ/Cam)</b>: Các trường hợp <b>nhầm lẫn</b>. Ví dụ: Người dùng vung thần chú <i>Lumos</i> nhưng AI lại nhận nhầm thành <i>Nox</i>.</li>
</ul>
<p>💡 <i>Mẹo sư phạm: Nếu thấy 2 phép thuật thường xuyên nhầm lẫn với nhau, hãy mở Tab 1 để kiểm tra Histogram xem đặc trưng của chúng có bị đè lên nhau không!</i></p>
"""),

    ("🌳 Cây Quyết Định (Decision Tree)", "tree", r"""
<h2>🌳 Cây Quyết Định (Decision Tree)</h2>
<p>Cây quyết định mô phỏng quá trình tư duy logic của con người thông qua một chuỗi các câu hỏi điều kiện (if-else):</p>
<p><i>Ví dụ: "Gia tốc a_z &le; 1.45 m/s²?" &rarr; Nếu Đúng: rẽ nhánh Trái, Nếu Sai: rẽ nhánh Phải.</i></p>

<h3>Chỉ số Tạp chất Gini (Gini Impurity):</h3>
<p>Gini đo lường độ "hỗn loạn" của tập mẫu tại một node (từ 0.0 đến 0.5):</p>
<ul>
  <li><b>Gini = 0.0</b>: Node hoàn toàn tinh khiết (100% mẫu trong node đều thuộc về cùng 1 phép thuật). Node này trở thành Node Lá (Leaf Node).</li>
  <li><b>Gini = 0.5</b>: Node bị trộn lẫn 50-50 giữa các phép thuật. Cần tiếp tục đặt câu hỏi để phân tách.</li>
</ul>

<h3>Ưu điểm trên ESP32:</h3>
<p>Tốc độ suy luận chỉ <b>0.04 ms</b> (cực nhanh), mã nguồn C sinh ra chỉ là các câu lệnh if-else lồng nhau, không tốn RAM heap!</p>
"""),

    ("🌲 Rừng Ngẫu Nhiên (Random Forest)", "forest", r"""
<h2>🌲 Rừng Ngẫu Nhiên (Random Forest)</h2>
<p>Thay vì chỉ dựa vào 1 Cây quyết định duy nhất, Random Forest xây dựng một <b>tập hợp nhiều cây độc lập</b> (Ensemble of Trees).</p>

<h3>Nguyên lý Hoạt động (Biểu Quyết Đa Số):</h3>
<ol>
  <li>Mỗi cây được huấn luyện trên một tập mẫu con ngẫu nhiên (Bootstrap Sampling) và một nhóm đặc trưng ngẫu nhiên.</li>
  <li>Khi có một cử chỉ mới, tất cả các cây cùng đưa ra dự đoán.</li>
  <li>Lớp nào nhận được <b>nhiều phiếu bầu nhất (Majority Voting)</b> sẽ là kết quả cuối cùng.</li>
</ol>
<p>💡 <i>Ưu điểm: Khắc phục nhược điểm học vẹt của cây đơn, độ chính xác cao và ổn định hơn rất nhiều.</i></p>
"""),

    ("📈 Hồi Quy Logistic (Logistic Regression)", "logistic", r"""
<h2>📈 Hồi Quy Logistic & Hàm Softmax</h2>
<p>Hồi quy Logistic là mô hình phân loại tuyến tính dựa trên xác suất toán học:</p>

<h3>1. Tính điểm số thô (Logits):</h3>
<p><b>z_k = W_k &middot; x + b_k</b></p>
<p>Trong đó W_k là vector trọng số của phép thuật thứ k, x là 48 đặc trưng, b_k là độ lệch (bias).</p>

<h3>2. Chuyển đổi thành xác suất qua hàm Softmax:</h3>
<p><b>P(k) = exp(z_k) / &Sigma; exp(z_m)</b></p>
<p>Softmax biến các điểm số z_k thành xác suất từ 0.0% đến 100.0% với tổng các xác suất bằng 100%.</p>
<p>💡 <i>Ý nghĩa trọng số W: Trọng số dương lớn nghĩa là đặc trưng đó càng mạnh thì khả năng là phép thuật đó càng cao!</i></p>
"""),

    ("🎯 Support Vector Machine (SVM)", "svm", r"""
<h2>🎯 Support Vector Machine (SVM)</h2>
<p>SVM tìm kiếm một <b>Siêu phẳng phân tách (Hyperplane)</b> có khoảng cách (Margin) xa nhất tới các điểm dữ liệu của các lớp.</p>

<h3>Véc-tơ Hỗ Trợ (Support Vectors):</h3>
<p>Là những điểm dữ liệu nằm sát ranh giới phân cách nhất. Toàn bộ vị trí của siêu phẳng chỉ phụ thuộc vào các Support Vectors này, những điểm khác ở xa không ảnh hưởng đến ranh giới!</p>

<h3>Bí quyết Hàm Nhân (RBF Kernel Trick):</h3>
<p>Khi dữ liệu cử chỉ không thể phân tách bằng một đường thẳng phẳng, hàm nhân RBF (Gaussian) sẽ chiếu dữ liệu lên không gian toán học nhiều chiều hơn để tìm siêu phẳng phân tách phi tuyến.</p>
"""),

    ("📍 K-Nearest Neighbors (KNN)", "knn", r"""
<h2>📍 K-Láng Giềng Gần Nhất (K-Nearest Neighbors)</h2>
<p>KNN là thuật toán đơn giản nhất và không cần quá trình huấn luyện tham số (Lazy Learning / Non-parametric):</p>
<ol>
  <li>Lưu toàn bộ các mẫu cử chỉ vào bộ nhớ Flash.</li>
  <li>Khi có một cử chỉ mới, tính khoảng cách hình học (Euclidean Distance) từ cử chỉ mới tới tất cả các mẫu trong kho.</li>
  <li>Chọn ra <b>K mẫu gần nhất</b>.</li>
  <li>Bỏ phiếu: Phép thuật nào chiếm đa số trong K láng giềng sẽ là kết quả dự đoán.</li>
</ol>
<p>💡 <i>Lưu ý: Nếu chọn K=1, mô hình rất dễ bị quá khớp bởi 1 điểm nhiễu; nếu chọn K quá lớn, biên phân lớp sẽ bị mờ.</i></p>
"""),

    ("🛡️ Zero Data Leakage (Không Rò Rỉ)", "zero_leakage", r"""
<h2>🛡️ Nguyên Tắc Không Rò Rỉ Dữ Liệu (Zero Data Leakage)</h2>
<p>Trong nhận diện cử chỉ chuỗi thời gian (Time-Series IMU), dữ liệu được cắt thành các cửa sổ trượt (Sliding Windows) có độ gối đầu lên nhau (Overlapping).</p>

<h3>Vì sao phải chia tập theo Cấp Độ File (File-Level Split)?</h3>
<ul>
  <li>Nếu chia ngẫu nhiên từng window (Random Window Split), các window kề nhau trong cùng 1 lần vung gậy sẽ rơi vào cả tập Train và tập Validation.</li>
  <li>Khi đó, bài thi (Validation) đã bị lộ đề vì máy đã học các mảnh vụn của chính lần vung gậy đó trong tập Train! Điểm số sẽ cao giả tạo (99-100%).</li>
  <li><b>Nguyên tắc Zero Data Leakage của ML Lab</b>: Toàn bộ các window của một file CSV chỉ được nằm trọn vẹn ở tập Train HOẶC tập Validation. Điều này đảm bảo điểm số phản ánh chính xác 100% năng lực thật của mô hình.</li>
</ul>
"""),
]


class GlossaryDialog(QDialog):
    """
    Hộp thoại Cẩm Nang Sư Phạm & Sổ Tay Thuật Ngữ AI.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("📖 Cẩm Nang Sư Phạm & Sổ Tay Thuật Ngữ STEM AI")
        self.resize(920, 640)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        head_box = QFrame()
        head_box.setStyleSheet("background: rgba(0, 122, 255, 0.07); border-radius: 8px; padding: 6px 12px;")
        h_layout = QHBoxLayout(head_box)
        
        lbl_h = QLabel("📖 CẨM NANG HỌC MÁY BẢN CHẤT (STEM ML HANDBOOK)")
        lbl_h.setStyleSheet("font-weight: 800; font-size: 14px; color: #007aff;")
        h_layout.addWidget(lbl_h)
        h_layout.addStretch()
        main_layout.addWidget(head_box)

        # Splitter Body
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left list topics
        self.topic_list = QListWidget()
        self.topic_list.setStyleSheet(
            "QListWidget { border: 1px solid #e5e7eb; border-radius: 6px; font-weight: 600; font-size: 12px; } "
            "QListWidget::item { padding: 10px; border-bottom: 1px solid #f3f4f6; } "
            "QListWidget::item:selected { background: #007aff; color: white; border-radius: 4px; }"
        )
        for title, key, _ in GLOSSARY_TOPICS:
            self.topic_list.addItem(title)
        self.topic_list.currentRowChanged.connect(self._on_topic_selected)
        splitter.addWidget(self.topic_list)

        # Right Content Browser
        self.content_browser = QTextBrowser()
        self.content_browser.setStyleSheet(
            "QTextBrowser { border: 1px solid #e5e7eb; border-radius: 6px; padding: 16px; background: white; font-size: 13px; line-height: 1.6; }"
        )
        splitter.addWidget(self.content_browser)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        main_layout.addWidget(splitter, stretch=1)

        # Bottom Button
        btn_close = QPushButton("Đóng Sổ Tay")
        btn_close.setStyleSheet("padding: 8px 18px; font-weight: 600; border-radius: 6px; background: #f3f4f6; border: 1px solid #d1d5db;")
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        # Default select first
        self.topic_list.setCurrentRow(0)

    def _on_topic_selected(self, row: int) -> None:
        if 0 <= row < len(GLOSSARY_TOPICS):
            _, _, html_content = GLOSSARY_TOPICS[row]
            self.content_browser.setHtml(html_content)
