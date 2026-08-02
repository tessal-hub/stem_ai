"""Rotating educational tips for the Home dashboard.

Purely static content — no runtime state, no signals, no DataStore/Handler
dependency. Mirrors the structure of primitive_i18n.py.
"""
from __future__ import annotations

from typing import Literal

Lang = Literal["en", "vi"]

_TIPS_EN: list[str] = [
    "“Practice makes perfect! Record 5 or more crisp samples to build a robust dataset for your spell.”",
    "“Every gesture is compressed into a 16-dimensional embedding vector — true TinyML magic.”",
    "“Few-shot learning allows your wand to learn entirely new spells from just 3 to 5 examples.”",
    "“Varying your casting speed and tilt angles helps the neural network generalize to different situations.”",
    "“Don't cast the exact same way every time! Slight variations prevent the model from overfitting to a single perfect motion.”",
    "“Cast with confidence! A crisp, decisive gesture has a high signal-to-noise ratio, beating a shaky wand every time.”",
    "“The wand tracks time-series data—acceleration and angular velocity over time—not spatial drawing paths.”",
    "“Consistency scores low? Check your sample alignment in the Laboratory. Bad data in, bad magic out!”",
    "“STAND BY teaches the model what quiet stillness feels like. Never skip training your negative class!”",
    "“Prototypes act as the mathematical center (centroid) of a spell — compact enough for any micro-chip.”",
    "“Swift wrist flicks generate distinct high-frequency IMU spikes — excellent features for offensive spells.”",
    "“Magic meets machine learning: motion sensors transform raw physical momentum into structured data.”",
    "“Smooth arcs reduce motion noise. Master fluid wrist control for clearer inputs and legendary accuracy.”",
    "“Each wand movement creates an unforgettable IMU fingerprint mapped into a high-dimensional latent space.”",
    "“To help the algorithm segment your data, hold the wand steady for a split second at the start and end of every cast.”",
    "“Precision over speed! A well-formed spell gives the model cleaner data than frantic, blurred motion.”",
    "“Euclidean distance matching calculates exactly how close your current cast is to the trained spell prototype.”",
    "“Keep your wand calibrated! Stable IMU gyro readings eliminate baseline drift for crystal-clear detection.”",
    "“If everyday movements trigger accidental magic, your confidence threshold is too low. Raise it to banish false positives!”",
    "“Every great wizard starts with a single sample. Greet the learning curve with patience.”",
    "“Signal processing filters turn noisy physical waves into sharp mathematical beauty before the AI even sees them.”",
    "“Train your muscle memory. Repeatable motion creates tight clusters of data points for the AI to recognize.”",
    "“Lightweight models run directly on the microcontroller (Edge AI) — meaning zero internet, zero lag, and total privacy.”",
    "“Sensor fusion blends acceleration and rotation to craft a multidimensional spell signature no rival can copy.”",
    "“Clean gesture boundaries (windowing) make the difference between a fizzled spell and a flawless cast.”",
    "“Training happens in the lab. Inference is the real-time magic that recognizes your spell out in the wild.”",
    "“We mathematically stretch and twist your samples. This 'data augmentation' makes the model robust against sloppy casting.”",
    "“The magic isn’t just in the wand — it’s in the machine learning algorithms guiding your hand.”",
]

_TIPS_VI: list[str] = [
    "“Có công mài sắt, có ngày nên kim! Hãy ghi lại ít nhất 5 mẫu thật chuẩn để tạo một tập dữ liệu (dataset) xịn xò cho thần chú.”",
    "“Mỗi cú vẫy đũa đều được 'nén' lại thành một vector nhúng (embedding) 16 chiều — đây mới chính là phép thuật thực sự của TinyML.”",
    "“Nhờ công nghệ Học qua vài mẫu (Few-shot learning), đũa phép có thể học một thần chú mới toanh chỉ với 3 đến 5 lần vẫy.”",
    "“Đừng vẫy đũa cứng nhắc một kiểu! Đổi tốc độ và góc nghiêng một chút sẽ giúp AI tổng quát hóa (generalize) tốt hơn đó.”",
    "“Biến tấu một chút khi luyện tập nhé! Nếu vẫy y hệt nhau 100%, AI sẽ bị 'học vẹt' (overfitting) và chỉ nhận diện được đúng tư thế đó thôi.”",
    "“Cứ tự tin vung đũa dứt khoát! Tín hiệu rõ ràng (SNR cao) lúc nào cũng ăn đứt những cú vẫy run rẩy, ngập ngừng.”",
    "“Đũa phép nhìn vào nhịp độ thời gian (time-series) của gia tốc và góc xoay, chứ không phải hình vẽ 3D bạn vạch ra trong không khí đâu.”",
    "“Độ đồng nhất (consistency) thấp? Hãy vào phòng Thí Nghiệm kiểm tra lại các mẫu nhé. Dữ liệu rác thì phép thuật cũng... rác luôn (Garbage In, Garbage Out)!”",
    "“Trạng thái STAND BY giúp AI hiểu thế nào là 'đứng im'. Đừng lười mà bỏ qua việc huấn luyện lớp phủ định (negative class) cực kỳ quan trọng này!”",
    "“Mẫu nguyên bản (Prototype) chính là 'trái tim' toán học (centroid) của mỗi câu thần chú — siêu nhẹ và nằm gọn trong mọi vi mạch.”",
    "“Một cú giật cổ tay tốc độ sẽ tạo ra sóng IMU tần số cao — đây là những đặc điểm (features) hoàn hảo cho các thần chú tấn công.”",
    "“Nơi phép thuật giao thoa cùng AI: cảm biến sẽ hô biến những chuyển động vật lý thô sơ thành dữ liệu sắc sảo.”",
    "“Vẫy đũa càng mượt, tín hiệu càng ít nhiễu. Hãy làm chủ cổ tay để tạo ra dữ liệu đầu vào huyền thoại!”",
    "“Mỗi đường đũa đều để lại một 'dấu vân tay' IMU độc nhất, ẩn mình trong một không gian đa chiều (latent space) đầy bí ẩn.”",
    "“Mẹo nhỏ để AI dễ phân đoạn (segment) dữ liệu: hãy giữ đũa đứng yên khoảng nửa giây trước và sau mỗi lần niệm chú.”",
    "“Chậm mà chắc! Một cử chỉ chuẩn form luôn cho ra dữ liệu sạch và dễ nhận diện hơn là vung đũa loạn xạ.”",
    "“Thuật toán khoảng cách Euclidean sẽ đo xem cú vẫy đũa vừa rồi của bạn giống với mẫu gốc đến mức nào, chính xác đến từng milimet toán học.”",
    "“Nhớ hiệu chuẩn đũa phép thường xuyên nhé! Con quay hồi chuyển (gyro) có ổn định thì mới tránh được hiện tượng trôi dạt (drift) tín hiệu.”",
    "“Gãi đầu mà đũa cũng bắn bùa? Đó là do ngưỡng kích hoạt (threshold) quá thấp. Hãy tăng nó lên để tránh AI nhận diện nhầm (false positives) nhé!”",
    "“Phù thủy vĩ đại nào cũng bắt đầu từ một mẫu dữ liệu nhỏ bé. Hãy kiên nhẫn một chút khi 'huấn luyện' đũa phép của mình.”",
    "“Trước khi AI kịp nhìn thấy, các bộ lọc tín hiệu đã âm thầm gọt giũa những chuyển động nhiễu loạn thành các đường nét toán học tuyệt đẹp.”",
    "“Hãy luyện trí nhớ cơ bắp! Vẫy đũa ổn định sẽ tạo ra các cụm dữ liệu (clusters) chặt chẽ, giúp AI nhận diện dễ như trở bàn tay.”",
    "“Mô hình AI siêu nhẹ này chạy trực tiếp ngay trên vi điều khiển (Edge AI) — không cần mạng, không độ trễ và bảo mật tuyệt đối.”",
    "“Kỹ thuật Hợp nhất cảm biến (Sensor fusion) sẽ hòa trộn gia tốc và độ xoay, tạo nên một 'chữ ký' thần chú không ai có thể làm giả.”",
    "“Đóng khung tín hiệu (windowing) chuẩn xác chính là ranh giới mong manh giữa một câu chú xịt và một pha thi triển hoàn hảo.”",
    "“Phòng Thí Nghiệm là nơi đổ mồ hôi Huấn luyện (Training). Còn Suy luận (Inference) chính là lúc phép màu thực sự tỏa sáng ngoài đời thực.”",
    "“Bí mật này: chúng tôi dùng toán học để nhào nặn các mẫu của bạn. Việc 'Tăng cường dữ liệu' (Data augmentation) này giúp AI vẫn nhận ra bùa chú ngay cả khi bạn vẫy hơi lỗi.”",
    "“Phép thuật không chỉ nằm ở lõi cây đũa, mà còn ở những thuật toán Machine Learning đang âm thầm dẫn lối cho bàn tay bạn.”",
]


def normalize_ui_language(code: str | None) -> Lang:
    """Chuẩn hóa mã ngôn ngữ về 'en' hoặc 'vi'."""
    if code is None:
        return "en"
    c = str(code).strip().lower()
    return "vi" if c in {"vi", "vn", "vietnamese"} else "en"


def get_tip_pool(lang: str | None) -> list[str]:
    """Return the tip pool for the given UI language."""
    return _TIPS_VI if normalize_ui_language(lang) == "vi" else _TIPS_EN