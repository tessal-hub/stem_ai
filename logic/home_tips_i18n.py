"""Rotating educational tips for the Home dashboard.

Purely static content — no runtime state, no signals, no DataStore/Handler
dependency. Mirrors the structure of primitive_i18n.py.

Written for readers with little to no AI/ML background: every tip maps a
real mechanism in the recognition pipeline to an everyday analogy, without
using jargon like "embedding", "cosine similarity", or "centroid" directly.
"""
from __future__ import annotations

from typing import Literal

Lang = Literal["en", "vi"]

_TIPS_EN_BY_CONFIDENCE: dict[str, list[str]] = {
    "high": [
        "“Right now your wave matches the 'reference shape' the wand built from your earlier tries — that's why it recognized it so confidently.”",
        "“The wand doesn't remember your exact wave. It remembers an *average shape*, built from every good sample you gave it before.”",
        "“Teaching a brand-new spell doesn't mean re-teaching the whole wand — it just needs a few waves to sketch a new reference shape.”",
        "“Behind the scenes, your wave becomes a short list of numbers — a kind of fingerprint — small enough to fit inside the wand's tiny chip.”",
        "“Even squeezed down to fit on a microcontroller, the math stays precise enough to tell your spells apart cleanly.”",
        "“High confidence means your wave looks a lot like all your past tries — the wand isn't confused by small wobbles, because it has seen them before.”",
        "“Every clean wave you do doesn't just help this spell — it also helps the wand tell this spell apart from every other one you've taught it.”",
        "“The safer a spell is from being triggered by accident, the bigger the 'gap' between your reference shape and every other spell's shape.”",
        "“What feels like 'good form' to your hand is, underneath, your wave staying close to that one reference shape — your muscles and the wand agree.”",
    ],
    "moderate": [
        "“A shaky wave doesn't make the wand think it's a totally different spell — it just makes the wand less *sure* which one it is.”",
        "“Try waving at the same speed a few times in a row. Changing speed between tries is one of the most common reasons confidence jumps around.”",
        "“The wand pays most attention to the strongest, clearest moment of your wave — pause briefly before and after so that moment stands out.”",
        "“If today feels less accurate than yesterday, check how you're holding the wand — tilting it differently shifts everything the wand measures.”",
        "“The wand was trained to accept some natural variation in your speed and angle — but there's still a 'sweet spot' where it recognizes best.”",
        "“A drop in accuracy is often caused by just one bad recording. Removing that one weak sample usually helps more than adding a new one.”",
        "“The wand listens to both movement and rotation together — if one of them barely changes, you may be holding it at an angle it hasn't seen.”",
        "“Only three samples so far means the reference shape is still forming — it can still shift a lot with your very next recording.”",
        "“Sometimes low confidence isn't your fault — the wand is deliberately cautious, so it sometimes doubts a wave that was actually fine.”",
    ],
    "low": [
        "“'STAND BY' isn't a lazy placeholder — it's how the wand learns what 'doing nothing' looks like, so it doesn't mistake a shrug for a spell.”",
        "“Low confidence here is expected: with only a couple of samples, the wand's 'reference shape' for this spell is still a rough guess.”",
        "“If every spell feels like it's being confused with another right now, the wand may need more *variety* in your samples — not just more samples.”",
        "“A good wave has one clear moment of motion. If yours trails off slowly or starts hesitantly, the wand may be looking at the wrong instant.”",
        "“The wand isn't being 'dumb' when it fails to recognize something — it's honestly telling you your wave doesn't yet look like anything it has learned.”",
    ],
}

_TIPS_VI_BY_CONFIDENCE: dict[str, list[str]] = {
    "high": [
        "“Cú vẫy vừa rồi rất giống với 'hình mẫu' mà đũa đã dựng từ những lần bạn tập trước — vì vậy nó nhận ra ngay lập tức.”",
        "“Đũa phép không nhớ chính xác từng cú vẫy của bạn. Nó nhớ một 'dáng vẫy trung bình', được dựng từ tất cả những lần bạn vẫy tốt trước đó.”",
        "“Dạy một thần chú hoàn toàn mới không có nghĩa là phải dạy lại từ đầu — đũa chỉ cần vài lần vẫy để phác ra một hình mẫu mới.”",
        "“Đằng sau hậu trường, cú vẫy của bạn được rút gọn thành một dãy số ngắn — giống như một dấu vân tay — đủ nhỏ để nhét vào con chip bé xíu của đũa.”",
        "“Dù bị nén nhỏ lại để vừa với con chip, phép tính bên trong vẫn đủ chính xác để phân biệt rạch ròi các thần chú với nhau.”",
        "“Độ tự tin cao nghĩa là cú vẫy của bạn rất giống với những lần tập trước — đũa không bị lúng túng bởi vài rung lắc nhỏ, vì nó đã 'thấy' những rung lắc đó trước rồi.”",
        "“Mỗi cú vẫy chuẩn không chỉ giúp riêng thần chú này — nó còn giúp đũa phân biệt thần chú này rõ hơn với mọi thần chú khác bạn từng dạy.”",
        "“Thần chú càng khó bị kích hoạt nhầm, tức là 'khoảng cách' giữa hình mẫu của nó và hình mẫu của các thần chú khác càng lớn.”",
        "“Cái mà tay bạn cảm nhận là 'vẫy đúng form' thực chất là cú vẫy vẫn nằm gần sát hình mẫu chuẩn — tay bạn và đũa đang 'hiểu nhau'.”",
    ],
    "moderate": [
        "“Vẫy run tay không khiến đũa nghĩ đó là một thần chú hoàn toàn khác — nó chỉ khiến đũa *bớt chắc chắn* hơn về việc đó là thần chú nào.”",
        "“Hãy thử vẫy cùng một tốc độ vài lần liên tiếp. Đổi tốc độ giữa các lần vẫy là lý do phổ biến nhất khiến độ tự tin lên xuống thất thường.”",
        "“Đũa chú ý nhiều nhất vào khoảnh khắc bạn vẫy mạnh và rõ nhất — hãy khựng lại một chút trước và sau cú vẫy để khoảnh khắc đó nổi bật lên.”",
        "“Nếu hôm nay cảm giác kém chính xác hơn hôm qua, hãy kiểm tra cách bạn cầm đũa — cầm nghiêng khác đi sẽ làm lệch mọi thứ đũa đo được.”",
        "“Đũa đã được dạy để chấp nhận một chút thay đổi về tốc độ và góc nghiêng — nhưng vẫn có một 'điểm ngọt' mà ở đó nó nhận diện tốt nhất.”",
        "“Độ chính xác giảm thường chỉ do MỘT lần ghi bị lỗi. Xóa lần ghi yếu đó đi thường giúp ích nhiều hơn là thêm một lần ghi mới.”",
        "“Đũa 'lắng nghe' cả chuyển động thẳng lẫn xoay cùng lúc — nếu một trong hai gần như không đổi, có thể bạn đang cầm đũa ở góc nó chưa từng thấy.”",
        "“Mới có ba lần ghi thì hình mẫu vẫn còn đang 'định hình' — nó vẫn có thể thay đổi nhiều chỉ với lần ghi tiếp theo của bạn.”",
        "“Đôi khi độ tự tin thấp không phải lỗi của bạn — đũa được chỉnh để 'thận trọng', nên đôi lúc nó nghi ngờ một cú vẫy thực ra vẫn ổn.”",
    ],
    "low": [
        "“'STAND BY' không phải là một lớp thừa cho có — đó là cách đũa học thế nào là 'không làm gì', để nó không nhầm một cái nhún vai thành phép thuật.”",
        "“Độ tự tin thấp lúc này là bình thường: mới chỉ vài lần ghi, nên 'hình mẫu' của đũa cho thần chú này vẫn còn là một phỏng đoán thô.”",
        "“Nếu bây giờ các thần chú cứ bị lẫn vào nhau, có thể đũa cần dữ liệu *đa dạng* hơn — không chỉ là nhiều lần ghi hơn.”",
        "“Một cú vẫy tốt nên có một khoảnh khắc chuyển động rõ ràng. Nếu cú vẫy của bạn trôi chậm dần hoặc bắt đầu do dự, đũa có thể đang nhìn nhầm khoảnh khắc.”",
        "“Đũa không hề 'ngu' khi không nhận ra được — nó chỉ đang thành thật báo rằng cú vẫy của bạn chưa giống bất cứ điều gì nó từng học.”",
    ],
}

_TIPS_EN: list[str] = (
    _TIPS_EN_BY_CONFIDENCE["low"]
    + _TIPS_EN_BY_CONFIDENCE["moderate"]
    + _TIPS_EN_BY_CONFIDENCE["high"]
)

_TIPS_VI: list[str] = (
    _TIPS_VI_BY_CONFIDENCE["low"]
    + _TIPS_VI_BY_CONFIDENCE["moderate"]
    + _TIPS_VI_BY_CONFIDENCE["high"]
)


def normalize_ui_language(code: str | None) -> Lang:
    """Chuẩn hóa mã ngôn ngữ về 'en' hoặc 'vi'."""
    if code is None:
        return "en"
    c = str(code).strip().lower()
    return "vi" if c in {"vi", "vn", "vietnamese"} else "en"


def get_tip_pool(lang: str | None, confidence_level: str | None = None) -> list[str]:
    """Return tip pool for UI language, optionally filtered by confidence level ('high', 'moderate', 'low')."""
    is_vi = normalize_ui_language(lang) == "vi"
    by_conf = _TIPS_VI_BY_CONFIDENCE if is_vi else _TIPS_EN_BY_CONFIDENCE
    if confidence_level and confidence_level in by_conf:
        return by_conf[confidence_level]
    return _TIPS_VI if is_vi else _TIPS_EN