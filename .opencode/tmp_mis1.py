# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("ml_lab/ui/tabs/tab_model_lab.py")
s = p.read_text(encoding="utf-8")

# import
old = "from ml_lab.ui.widgets.class_breakdown_widget import ClassBreakdownWidget"
new = ("from ml_lab.ui.widgets.class_breakdown_widget import ClassBreakdownWidget\n"
       "from ml_lab.ui.widgets.misclassification_widget import MisclassificationWidget")
assert old in s
s = s.replace(old, new, 1)

# sub-tab 4: splitter dọc breakdown + misclassification
old = '''        # Sub-tab 4: Lớp nào yếu?
        tab4 = QWidget()
        t4 = QVBoxLayout(tab4)
        t4.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        t4.setSpacing(ls.SP_2)
        self.class_breakdown = ClassBreakdownWidget()
        t4.addWidget(self.class_breakdown, stretch=1)
        t4.addWidget(self._note_label(
            "<b>Chẩn đoán từng thần chú</b> — lớp yếu nhất đứng đầu kèm gợi ý hành động. "
            "Ghi thêm mẫu theo gợi ý rồi huấn luyện lại để thấy điểm cải thiện."
        ))
        tabs.addTab(tab4, "Lớp nào yếu?")'''
new = '''        # Sub-tab 4: Lớp nào yếu? + xem tại sao máy nhầm
        tab4 = QWidget()
        t4 = QVBoxLayout(tab4)
        t4.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        t4.setSpacing(ls.SP_2)
        split_v = QSplitter(Qt.Orientation.Vertical)
        self.class_breakdown = ClassBreakdownWidget()
        split_v.addWidget(self.class_breakdown)
        self.misclass_widget = MisclassificationWidget()
        split_v.addWidget(self.misclass_widget)
        split_v.setStretchFactor(0, 4)
        split_v.setStretchFactor(1, 6)
        t4.addWidget(split_v, stretch=1)
        t4.addWidget(self._note_label(
            "<b>Chẩn đoán từng thần chú</b> — lớp yếu nhất đứng đầu kèm gợi ý hành động. "
            "Chọn một mẫu bị sai bên dưới để xem dạng sóng thật và hiểu vì sao máy nhầm."
        ))
        tabs.addTab(tab4, "Lớp nào yếu?")'''
assert old in s
s = s.replace(old, new, 1)

# cập nhật khi train xong
old = "        self.class_breakdown.set_result(result)"
new = "        self.class_breakdown.set_result(result)\n        self.misclass_widget.set_result(result)"
assert old in s
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("misclassification wired")
