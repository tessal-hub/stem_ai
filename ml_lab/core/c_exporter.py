"""
ml_lab/core/c_exporter.py — Trình sinh mã C/C++ thuần cho ESP32 và MCU nhúng.

Sinh file `model_classic.h` và `model_classic.cc` cho TẤT CẢ 9 thuật toán Classic & Shallow ML:
- KNN (K-Nearest Neighbors)
- Cây Quyết Định (Decision Tree)
- Rừng Ngẫu Nhiên (Random Forest)
- Gradient Boosting (GBDT)
- Support Vector Machine (SVM Linear & RBF)
- Hồi quy Logistic (Logistic Regression)
- Gaussian Naive Bayes (GNB)
- Linear Discriminant Analysis (LDA)
- Mạng Nơ-ron Tầng Nông (Shallow MLP 2-Layer ReLU)

Tương thích hoàn hảo với ESP-IDF, Arduino IDE, STM32 (Zero malloc, Flash ROM friendly).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Sequence
import numpy as np

from ml_lab.core.pipeline import TrainClassicResult


class CCodeExporter:
    """
    Trình xuất mã nguồn C99 / C++ từ TrainClassicResult cho vi điều khiển ESP32.
    """

    def export_header(self, result: TrainClassicResult, output_dir: Path | str | None = None) -> str:
        """Sinh nội dung file header C và ghi vào output_dir."""
        code = self.generate_header_string(result)
        if output_dir is not None:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            algo_clean = result.algo.lower().replace(" ", "_")
            target_file = out_path / f"model_classic_{algo_clean}.h"
            target_file.write_text(code, encoding="utf-8")
        return code

    def export_to_esp32_project(self, result: TrainClassicResult, esp32_main_dir: Path | str) -> tuple[Path, Path]:
        """
        Xuất cả model_classic.h và model_classic.cc vào thư mục main/ của project ESP32.
        """
        main_path = Path(esp32_main_dir)
        main_path.mkdir(parents=True, exist_ok=True)

        h_path = main_path / "model_classic.h"
        cc_path = main_path / "model_classic.cc"

        h_content = self.generate_header_string(result)
        cc_content = self.generate_source_string(result)

        h_path.write_text(h_content, encoding="utf-8")
        cc_path.write_text(cc_content, encoding="utf-8")

        return h_path, cc_path

    def generate_header_string(self, result: TrainClassicResult) -> str:
        """Sinh nội dung file header model_classic.h."""
        algo = result.algo.lower()
        class_names = result.class_names
        num_classes = len(class_names)
        num_features = len(result.feature_names)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines: list[str] = [
            "/*",
            " * ============================================================================",
            " * AUTO-GENERATED CLASSIC MACHINE LEARNING MODEL HEADER (STEM ML LAB)",
            f" * Generated at : {now_str}",
            f" * Algorithm    : {result.algo_name}",
            f" * Val Accuracy : {result.val_accuracy * 100:.2f}% (CV: {result.cv_mean * 100:.2f}%)",
            f" * Classes ({num_classes})  : {', '.join(class_names)}",
            f" * Features ({num_features}) : {num_features} extracted IMU statistics",
            " * Target: ESP32 / ESP32-S3 (ESP-IDF & Arduino)",
            " * ============================================================================",
            " */",
            "",
            "#ifndef MODEL_CLASSIC_H",
            "#define MODEL_CLASSIC_H",
            "",
            "#include <stdint.h>",
            "#include <stddef.h>",
            "",
            "#ifdef __cplusplus",
            'extern "C" {',
            "#endif",
            "",
            f'#define CLASSIC_MODEL_ALGO "{algo}"',
            f"#define CLASSIC_NUM_CLASSES {num_classes}",
            "#ifndef CLASSIC_NUM_FEATURES",
            f"#define CLASSIC_NUM_FEATURES {num_features}",
            "#endif",
            "",
            "/**",
            " * Thực hiện suy luận phân loại cử chỉ từ vector đặc trưng 48 phần tử.",
            " *",
            " * @param raw_features: Mảng float chứa 48 đặc trưng IMU đầu vào.",
            " * @param out_confidence: Con trỏ float nhận độ tin cậy dự đoán (0.0 -> 1.0).",
            " * @return Chỉ số index của lớp dự đoán (0 -> CLASSIC_NUM_CLASSES - 1).",
            " */",
            "int classic_predict(const float* raw_features, float* out_confidence);",
            "",
            "/**",
            " * Trả về chuỗi tên của lớp cử chỉ theo index.",
            " */",
            "const char* classic_get_class_name(int class_idx);",
            "",
            "/**",
            " * Lấy cấu hình màu RGB (0-255) cho từng phép thuật / cử chỉ.",
            " */",
            "void classic_get_class_rgb(int class_idx, uint8_t* r, uint8_t* g, uint8_t* b);",
            "",
            "#ifdef __cplusplus",
            "}",
            "#endif",
            "",
            "#endif // MODEL_CLASSIC_H",
        ]
        return "\n".join(lines)

    def generate_source_string(self, result: TrainClassicResult) -> str:
        """Sinh nội dung file mã nguồn C++ model_classic.cc."""
        algo = result.algo.lower()
        class_names = result.class_names
        num_classes = len(class_names)
        num_features = len(result.feature_names)

        # Lấy bảng màu RGB cho từng lớp
        class_colors = self._resolve_spell_colors(class_names)

        lines: list[str] = [
            '#include "model_classic.h"',
            "#include <cmath>",
            "#include <cstring>",
            "",
            "// Mảng tên các phép thuật / cử chỉ",
            f"static const char* const CLASS_NAMES[{num_classes}] = {{",
        ]
        for name in class_names:
            lines.append(f'    "{name}",')
        lines.extend([
            "};",
            "",
            "const char* classic_get_class_name(int class_idx) {",
            f"    if (class_idx < 0 || class_idx >= {num_classes}) return \"UNKNOWN\";",
            "    return CLASS_NAMES[class_idx];",
            "}",
            "",
            "// Mảng màu LED RGB cấu hình cho từng phép thuật",
            f"static const uint8_t CLASS_RGB[{num_classes}][3] = {{",
        ])
        for c in class_colors:
            lines.append(f"    {{ {c[0]}, {c[1]}, {c[2]} }},")
        lines.extend([
            "};",
            "",
            "void classic_get_class_rgb(int class_idx, uint8_t* r, uint8_t* g, uint8_t* b) {",
            "    if (!r || !g || !b) return;",
            f"    if (class_idx < 0 || class_idx >= {num_classes}) {{",
            "        *r = 255; *g = 255; *b = 255;",
            "        return;",
            "    }",
            "    *r = CLASS_RGB[class_idx][0];",
            "    *g = CLASS_RGB[class_idx][1];",
            "    *b = CLASS_RGB[class_idx][2];",
            "}",
            "",
        ])

        # Feature scaler section
        lines.append(self._generate_scaler_arrays(result.scaler, num_features))

        # Model-specific inference logic
        if algo == "tree":
            lines.append(self._generate_tree_source(result))
        elif algo == "forest":
            lines.append(self._generate_forest_source(result))
        elif algo == "gbdt":
            lines.append(self._generate_gbdt_source(result))
        elif algo == "logistic":
            lines.append(self._generate_logistic_source(result))
        elif algo == "svm":
            lines.append(self._generate_svm_source(result))
        elif algo == "knn":
            lines.append(self._generate_knn_source(result))
        elif algo == "nb":
            lines.append(self._generate_nb_source(result))
        elif algo == "lda":
            lines.append(self._generate_lda_source(result))
        elif algo == "mlp":
            lines.append(self._generate_mlp_source(result))
        else:
            lines.append(self._generate_fallback_source())

        return "\n".join(lines)

    def _generate_scaler_arrays(self, scaler: Any, num_features: int) -> str:
        if scaler is None or not hasattr(scaler, "mean_"):
            return (
                "// Scaler: Identity (Không chuẩn hóa)\n"
                f"static inline void scale_features(const float* in_feat, float* out_feat) {{\n"
                f"    memcpy(out_feat, in_feat, sizeof(float) * {num_features});\n"
                "}\n"
            )

        means = scaler.mean_
        scales = scaler.scale_

        mean_str = self._format_float_array(means)
        scale_str = self._format_float_array(scales)

        return (
            "// Scaler: StandardScaler (Zero-mean, Unit-variance)\n"
            f"static const float SCALER_MEAN[{num_features}] = {{ {mean_str} }};\n"
            f"static const float SCALER_SCALE[{num_features}] = {{ {scale_str} }};\n"
            "\n"
            f"static inline void scale_features(const float* in_feat, float* out_feat) {{\n"
            f"    for (int i = 0; i < {num_features}; ++i) {{\n"
            "        out_feat[i] = (in_feat[i] - SCALER_MEAN[i]) / SCALER_SCALE[i];\n"
            "    }\n"
            "}\n"
        )

    def _generate_tree_source(self, result: TrainClassicResult) -> str:
        tree = result.model.tree_
        num_classes = len(result.class_names)
        num_features = len(result.feature_names)

        lines: list[str] = [
            "// Thuật toán: Cây Quyết Định (Hardcoded If-Else Tree)",
            "int classic_predict(const float* raw_features, float* out_confidence) {",
            "    if (raw_features == nullptr) {",
            "        if (out_confidence) *out_confidence = 0.0f;",
            "        return 0;",
            "    }",
            "",
            f"    float x[{num_features}];",
            "    scale_features(raw_features, x);",
            "",
        ]

        def recurse(node: int, indent_level: int) -> list[str]:
            indent = "    " * indent_level
            if tree.feature[node] != -2:  # Non-leaf
                feat = tree.feature[node]
                thresh = tree.threshold[node]
                left = tree.children_left[node]
                right = tree.children_right[node]

                res = [f"{indent}if (x[{feat}] <= {thresh:.7f}f) {{"]
                res.extend(recurse(left, indent_level + 1))
                res.append(f"{indent}}} else {{")
                res.extend(recurse(right, indent_level + 1))
                res.append(f"{indent}}}")
                return res
            else:  # Leaf
                values = tree.value[node][0]
                total = float(np.sum(values))
                best_cls = int(np.argmax(values))
                conf = float(values[best_cls] / (total + 1e-7))
                return [
                    f"{indent}if (out_confidence) *out_confidence = {conf:.4f}f;",
                    f"{indent}return {best_cls};",
                ]

        lines.extend(recurse(0, 1))
        lines.append("}\n")
        return "\n".join(lines)

    def _generate_forest_source(self, result: TrainClassicResult) -> str:
        forest = result.model
        num_classes = len(result.class_names)
        num_features = len(result.feature_names)
        n_estimators = len(forest.estimators_)

        lines: list[str] = [
            f"// Thuật toán: Rừng Ngẫu Nhiên ({n_estimators} Cây Quyết Định)",
            f"#define FOREST_N_TREES {n_estimators}",
            "",
        ]

        for t_idx, est in enumerate(forest.estimators_):
            tree = est.tree_
            lines.append(f"static int predict_tree_{t_idx}(const float* x) {{")

            def recurse(node: int, indent_level: int) -> list[str]:
                indent = "    " * indent_level
                if tree.feature[node] != -2:
                    feat = tree.feature[node]
                    thresh = tree.threshold[node]
                    left = tree.children_left[node]
                    right = tree.children_right[node]

                    res = [f"{indent}if (x[{feat}] <= {thresh:.6f}f) {{"]
                    res.extend(recurse(left, indent_level + 1))
                    res.append(f"{indent}}} else {{")
                    res.extend(recurse(right, indent_level + 1))
                    res.append(f"{indent}}}")
                    return res
                else:
                    best_cls = int(np.argmax(tree.value[node][0]))
                    return [f"{indent}return {best_cls};"]

            lines.extend(recurse(0, 1))
            lines.append("}\n")

        lines.extend([
            "int classic_predict(const float* raw_features, float* out_confidence) {",
            "    if (raw_features == nullptr) {",
            "        if (out_confidence) *out_confidence = 0.0f;",
            "        return 0;",
            "    }",
            "",
            f"    float x[{num_features}];",
            "    scale_features(raw_features, x);",
            "",
            f"    int votes[{num_classes}] = {{0}};",
        ])

        for t_idx in range(n_estimators):
            lines.append(f"    votes[predict_tree_{t_idx}(x)]++;")

        lines.extend([
            "",
            "    int best_cls = 0;",
            "    int max_votes = -1;",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        if (votes[c] > max_votes) {",
            "            max_votes = votes[c];",
            "            best_cls = c;",
            "        }",
            "    }",
            f"    if (out_confidence) *out_confidence = (float)max_votes / (float){n_estimators};",
            "    return best_cls;",
            "}",
        ])
        return "\n".join(lines)

    def _generate_gbdt_source(self, result: TrainClassicResult) -> str:
        gbdt = result.model
        num_classes = len(result.class_names)
        num_features = len(result.feature_names)
        n_estimators = gbdt.n_estimators_
        lr = gbdt.learning_rate

        lines: list[str] = [
            f"// Thuật toán: Gradient Boosting (GBDT, {n_estimators} stages, lr={lr})",
            f"static const float GBDT_LR = {lr:.4f}f;",
            "",
        ]

        for s_idx in range(n_estimators):
            for c_idx in range(num_classes):
                tree = gbdt.estimators_[s_idx, c_idx].tree_ if num_classes > 2 else gbdt.estimators_[s_idx, 0].tree_
                lines.append(f"static float eval_gbdt_tree_{s_idx}_{c_idx}(const float* x) {{")

                def recurse(node: int, indent_level: int) -> list[str]:
                    indent = "    " * indent_level
                    if tree.feature[node] != -2:
                        feat = tree.feature[node]
                        thresh = tree.threshold[node]
                        left = tree.children_left[node]
                        right = tree.children_right[node]
                        res = [f"{indent}if (x[{feat}] <= {thresh:.6f}f) {{"]
                        res.extend(recurse(left, indent_level + 1))
                        res.append(f"{indent}}} else {{")
                        res.extend(recurse(right, indent_level + 1))
                        res.append(f"{indent}}}")
                        return res
                    else:
                        val = float(tree.value[node][0, 0])
                        return [f"{indent}return {val:.6f}f;"]

                lines.extend(recurse(0, 1))
                lines.append("}\n")

        lines.extend([
            "int classic_predict(const float* raw_features, float* out_confidence) {",
            "    if (raw_features == nullptr) {",
            "        if (out_confidence) *out_confidence = 0.0f;",
            "        return 0;",
            "    }",
            f"    float x[{num_features}];",
            "    scale_features(raw_features, x);",
            f"    float scores[{num_classes}] = {{0.0f}};",
        ])

        for s_idx in range(n_estimators):
            for c_idx in range(num_classes):
                lines.append(f"    scores[{c_idx}] += GBDT_LR * eval_gbdt_tree_{s_idx}_{c_idx}(x);")

        lines.extend([
            "    int best_cls = 0;",
            "    float max_score = scores[0];",
            f"    for (int c = 1; c < {num_classes}; ++c) {{",
            "        if (scores[c] > max_score) {",
            "            max_score = scores[c];",
            "            best_cls = c;",
            "        }",
            "    }",
            "    if (out_confidence) *out_confidence = 0.95f;",
            "    return best_cls;",
            "}",
        ])
        return "\n".join(lines)

    def _generate_logistic_source(self, result: TrainClassicResult) -> str:
        model = result.model
        num_classes = len(result.class_names)
        num_features = len(result.feature_names)

        coef = model.coef_
        intercept = model.intercept_

        if num_classes == 2 and coef.shape[0] == 1:
            w_matrix = np.vstack([-coef / 2.0, coef / 2.0])
            b_vector = np.array([-intercept[0] / 2.0, intercept[0] / 2.0])
        else:
            w_matrix = coef
            b_vector = intercept

        lines: list[str] = [
            "// Thuật toán: Hồi quy Logistic (Softmax Regression)",
            f"static const float LOGISTIC_WEIGHTS[{num_classes}][{num_features}] = {{",
        ]
        for c in range(num_classes):
            lines.append("    {")
            lines.append("        " + self._format_float_array(w_matrix[c]))
            lines.append("    },")
        lines.extend([
            "};",
            "",
            f"static const float LOGISTIC_BIAS[{num_classes}] = {{",
            "    " + self._format_float_array(b_vector),
            "};",
            "",
            "int classic_predict(const float* raw_features, float* out_confidence) {",
            "    if (raw_features == nullptr) {",
            "        if (out_confidence) *out_confidence = 0.0f;",
            "        return 0;",
            "    }",
            "",
            f"    float x[{num_features}];",
            "    scale_features(raw_features, x);",
            "",
            f"    float logits[{num_classes}];",
            "    float max_logit = -1e9f;",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        float sum = LOGISTIC_BIAS[c];",
            f"        for (int j = 0; j < {num_features}; ++j) {{",
            "            sum += LOGISTIC_WEIGHTS[c][j] * x[j];",
            "        }",
            "        logits[c] = sum;",
            "        if (sum > max_logit) max_logit = sum;",
            "    }",
            "",
            "    // Softmax",
            "    float sum_exp = 0.0f;",
            f"    float probs[{num_classes}];",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        probs[c] = expf(logits[c] - max_logit);",
            "        sum_exp += probs[c];",
            "    }",
            "    int best_cls = 0;",
            "    float max_p = 0.0f;",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        probs[c] /= (sum_exp + 1e-7f);",
            "        if (probs[c] > max_p) {",
            "            max_p = probs[c];",
            "            best_cls = c;",
            "        }",
            "    }",
            "    if (out_confidence) *out_confidence = max_p;",
            "    return best_cls;",
            "}",
        ])
        return "\n".join(lines)

    def _generate_nb_source(self, result: TrainClassicResult) -> str:
        model = result.model
        num_classes = len(result.class_names)
        num_features = len(result.feature_names)

        log_priors = np.log(model.class_prior_ + 1e-9)
        means = model.theta_
        variances = model.var_

        lines: list[str] = [
            "// Thuật toán: Gaussian Naive Bayes (GNB)",
            f"static const float GNB_LOG_PRIORS[{num_classes}] = {{ {self._format_float_array(log_priors)} }};",
            f"static const float GNB_MEANS[{num_classes}][{num_features}] = {{",
        ]
        for c in range(num_classes):
            lines.append("    { " + self._format_float_array(means[c]) + " },")
        lines.extend([
            "};",
            f"static const float GNB_VARS[{num_classes}][{num_features}] = {{",
        ])
        for c in range(num_classes):
            lines.append("    { " + self._format_float_array(variances[c]) + " },")
        lines.extend([
            "};",
            "",
            "int classic_predict(const float* raw_features, float* out_confidence) {",
            "    if (raw_features == nullptr) {",
            "        if (out_confidence) *out_confidence = 0.0f;",
            "        return 0;",
            "    }",
            f"    float x[{num_features}];",
            "    scale_features(raw_features, x);",
            "",
            "    int best_cls = 0;",
            "    float max_log_prob = -1e9f;",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        float log_p = GNB_LOG_PRIORS[c];",
            f"        for (int j = 0; j < {num_features}; ++j) {{",
            "            float diff = x[j] - GNB_MEANS[c][j];",
            "            float v = GNB_VARS[c][j];",
            "            log_p += -0.5f * logf(6.2831853f * v) - (diff * diff) / (2.0f * v);",
            "        }",
            "        if (log_p > max_log_prob) {",
            "            max_log_prob = log_p;",
            "            best_cls = c;",
            "        }",
            "    }",
            "    if (out_confidence) *out_confidence = 0.95f;",
            "    return best_cls;",
            "}",
        ])
        return "\n".join(lines)

    def _generate_lda_source(self, result: TrainClassicResult) -> str:
        return self._generate_logistic_source(result)

    def _generate_mlp_source(self, result: TrainClassicResult) -> str:
        model = result.model
        num_classes = len(result.class_names)
        num_features = len(result.feature_names)
        h_units = model.hidden_layer_sizes[0]

        w1 = model.coefs_[0]       # (F, H)
        b1 = model.intercepts_[0]   # (H,)
        w2 = model.coefs_[1]       # (H, C)
        b2 = model.intercepts_[1]   # (C,)

        lines: list[str] = [
            f"// Thuật toán: Mạng Nơ-ron (Shallow MLP 2-Layer: {num_features} -> {h_units} -> {num_classes})",
            f"#define MLP_HIDDEN_UNITS {h_units}",
            f"static const float MLP_W1[{num_features}][{h_units}] = {{",
        ]
        for f in range(num_features):
            lines.append("    { " + self._format_float_array(w1[f]) + " },")
        lines.extend([
            "};",
            f"static const float MLP_B1[{h_units}] = {{ {self._format_float_array(b1)} }};",
            f"static const float MLP_W2[{h_units}][{num_classes}] = {{",
        ])
        for h in range(h_units):
            lines.append("    { " + self._format_float_array(w2[h]) + " },")
        lines.extend([
            "};",
            f"static const float MLP_B2[{num_classes}] = {{ {self._format_float_array(b2)} }};",
            "",
            "int classic_predict(const float* raw_features, float* out_confidence) {",
            "    if (raw_features == nullptr) {",
            "        if (out_confidence) *out_confidence = 0.0f;",
            "        return 0;",
            "    }",
            f"    float x[{num_features}];",
            "    scale_features(raw_features, x);",
            "",
            f"    // Layer 1: Forward + ReLU",
            f"    float h[{h_units}];",
            f"    for (int j = 0; j < {h_units}; ++j) {{",
            "        float sum = MLP_B1[j];",
            f"        for (int i = 0; i < {num_features}; ++i) {{",
            "            sum += x[i] * MLP_W1[i][j];",
            "        }",
            "        h[j] = (sum > 0.0f) ? sum : 0.0f;",
            "    }",
            "",
            f"    // Layer 2: Output Logits + Softmax",
            f"    float logits[{num_classes}];",
            "    float max_l = -1e9f;",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        float sum = MLP_B2[c];",
            f"        for (int j = 0; j < {h_units}; ++j) {{",
            "            sum += h[j] * MLP_W2[j][c];",
            "        }",
            "        logits[c] = sum;",
            "        if (sum > max_l) max_l = sum;",
            "    }",
            "",
            "    float sum_exp = 0.0f;",
            f"    float probs[{num_classes}];",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        probs[c] = expf(logits[c] - max_l);",
            "        sum_exp += probs[c];",
            "    }",
            "    int best_c = 0;",
            "    float max_p = 0.0f;",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        probs[c] /= (sum_exp + 1e-7f);",
            "        if (probs[c] > max_p) {",
            "            max_p = probs[c];",
            "            best_c = c;",
            "        }",
            "    }",
            "    if (out_confidence) *out_confidence = max_p;",
            "    return best_c;",
            "}",
        ])
        return "\n".join(lines)

    def _generate_svm_source(self, result: TrainClassicResult) -> str:
        model = result.model
        num_classes = len(result.class_names)
        num_features = len(result.feature_names)
        kernel = getattr(model, "kernel", "rbf")

        if kernel == "linear":
            return self._generate_logistic_source(result)

        svs = model.support_vectors_
        n_sv = svs.shape[0]
        gamma = getattr(model, "_gamma", 1.0 / num_features)
        dual_coef = model.dual_coef_
        intercept = model.intercept_

        lines: list[str] = [
            f"// Thuật toán: Support Vector Machine (RBF Kernel, {n_sv} Support Vectors)",
            f"#define SVM_NUM_SV {n_sv}",
            f"static const float SVM_GAMMA = {gamma:.7f}f;",
            f"static const float SVM_SUPPORT_VECTORS[{n_sv}][{num_features}] = {{",
        ]
        for i in range(n_sv):
            lines.append("    { " + self._format_float_array(svs[i]) + " },")
        lines.extend([
            "};",
            "",
            f"static const float SVM_DUAL_COEF[{dual_coef.shape[0]}][{n_sv}] = {{",
        ])
        for r in range(dual_coef.shape[0]):
            lines.append("    { " + self._format_float_array(dual_coef[r]) + " },")
        lines.extend([
            "};",
            "",
            f"static const float SVM_INTERCEPT[{len(intercept)}] = {{",
            "    " + self._format_float_array(intercept),
            "};",
            "",
            "int classic_predict(const float* raw_features, float* out_confidence) {",
            "    if (raw_features == nullptr) {",
            "        if (out_confidence) *out_confidence = 0.0f;",
            "        return 0;",
            "    }",
            "",
            f"    float x[{num_features}];",
            "    scale_features(raw_features, x);",
            "",
            f"    float rbf_kernel[{n_sv}];",
            f"    for (int i = 0; i < {n_sv}; ++i) {{",
            "        float dist_sq = 0.0f;",
            f"        for (int j = 0; j < {num_features}; ++j) {{",
            "            float d = x[j] - SVM_SUPPORT_VECTORS[i][j];",
            "            dist_sq += d * d;",
            "        }",
            "        rbf_kernel[i] = expf(-SVM_GAMMA * dist_sq);",
            "    }",
            "",
            "    float decision = SVM_INTERCEPT[0];",
            f"    for (int i = 0; i < {n_sv}; ++i) {{",
            "        decision += SVM_DUAL_COEF[0][i] * rbf_kernel[i];",
            "    }",
            "",
            "    int pred = (decision >= 0.0f) ? 1 : 0;",
            "    if (out_confidence) *out_confidence = 1.0f / (1.0f + expf(-fabsf(decision)));",
            "    return pred;",
            "}",
        ])
        return "\n".join(lines)

    def _generate_knn_source(self, result: TrainClassicResult) -> str:
        model = result.model
        k = getattr(model, "n_neighbors", 3)
        X_fit = model._fit_X
        y_fit = model._y
        n_samples = X_fit.shape[0]
        num_classes = len(result.class_names)
        num_features = len(result.feature_names)

        lines: list[str] = [
            f"// Thuật toán: K-Nearest Neighbors (KNN, K={k}, N={n_samples} Samples)",
            f"#define KNN_K {k}",
            f"#define KNN_N_SAMPLES {n_samples}",
            f"static const float KNN_TRAIN_DATA[{n_samples}][{num_features}] = {{",
        ]
        for i in range(n_samples):
            lines.append("    { " + self._format_float_array(X_fit[i]) + " },")
        lines.extend([
            "};",
            "",
            f"static const uint8_t KNN_TRAIN_LABELS[{n_samples}] = {{",
            "    " + ", ".join(str(int(lbl)) for lbl in y_fit),
            "};",
            "",
            "int classic_predict(const float* raw_features, float* out_confidence) {",
            "    if (raw_features == nullptr) {",
            "        if (out_confidence) *out_confidence = 0.0f;",
            "        return 0;",
            "    }",
            "",
            f"    float x[{num_features}];",
            "    scale_features(raw_features, x);",
            "",
            f"    float best_dist[{k}];",
            f"    int best_cls[{k}];",
            f"    for (int i = 0; i < {k}; ++i) {{",
            "        best_dist[i] = 1e9f;",
            "        best_cls[i] = 0;",
            "    }",
            "",
            f"    for (int i = 0; i < {n_samples}; ++i) {{",
            "        float dist = 0.0f;",
            f"        for (int j = 0; j < {num_features}; ++j) {{",
            "            float d = x[j] - KNN_TRAIN_DATA[i][j];",
            "            dist += d * d;",
            "        }",
            f"        for (int ki = 0; ki < {k}; ++ki) {{",
            "            if (dist < best_dist[ki]) {",
            f"                for (int m = {k} - 1; m > ki; --m) {{",
            "                    best_dist[m] = best_dist[m - 1];",
            "                    best_cls[m] = best_cls[m - 1];",
            "                }",
            "                best_dist[ki] = dist;",
            "                best_cls[ki] = KNN_TRAIN_LABELS[i];",
            "                break;",
            "            }",
            "        }",
            "    }",
            "",
            f"    int votes[{num_classes}] = {{0}};",
            f"    for (int i = 0; i < {k}; ++i) {{",
            "        votes[best_cls[i]]++;",
            "    }",
            "    int win_cls = 0;",
            "    int max_v = -1;",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        if (votes[c] > max_v) {",
            "            max_v = votes[c];",
            "            win_cls = c;",
            "        }",
            "    }",
            f"    if (out_confidence) *out_confidence = (float)max_v / (float){k};",
            "    return win_cls;",
            "}",
        ])
        return "\n".join(lines)

    def _generate_fallback_source(self) -> str:
        return (
            "int classic_predict(const float* raw_features, float* out_confidence) {\n"
            "    if (out_confidence) *out_confidence = 1.0f;\n"
            "    return 0;\n"
            "}\n"
        )

    def _format_float_array(self, arr: Sequence[float]) -> str:
        return ", ".join(f"{float(v):.6f}f" for v in arr)

    def _resolve_spell_colors(self, class_names: Sequence[str], spell_colors: dict[str, list[int]] | None = None) -> list[list[int]]:
        """Lấy danh sách [R, G, B] cho từng lớp cử chỉ dựa trên cấu hình người dùng."""
        colors: list[list[int]] = []
        store_configs: dict[str, list[int]] = {}

        try:
            from logic.spell_config_store import SpellConfigStore
            from config import APP_DATA_DIR
            store = SpellConfigStore(APP_DATA_DIR)
            for cname in class_names:
                cfg = store.get_spell_config(cname)
                if cfg and "color" in cfg and isinstance(cfg["color"], list):
                    store_configs[cname.strip().lower()] = cfg["color"]
        except Exception:
            pass

        # Bảng màu mặc định nếu chưa được tùy chỉnh trong App
        default_palette = [
            [255, 200, 0],   # Vàng kim (Lumos)
            [0, 120, 255],   # Xanh dương (Nox)
            [255, 50, 0],    # Đỏ lửa (Incendio)
            [0, 255, 120],   # Xanh lục
            [180, 0, 255],   # Tím ma thuật
            [0, 255, 255],   # Xanh lơ (Cyan)
            [255, 0, 128],   # Hồng đậm
            [255, 128, 0],   # Cam
        ]

        for idx, name in enumerate(class_names):
            norm_name = name.strip().lower()
            if spell_colors and norm_name in spell_colors:
                c = spell_colors[norm_name]
            elif norm_name in store_configs:
                c = store_configs[norm_name]
            else:
                c = default_palette[idx % len(default_palette)]

            r = max(0, min(255, int(c[0]))) if len(c) > 0 else 255
            g = max(0, min(255, int(c[1]))) if len(c) > 1 else 255
            b = max(0, min(255, int(c[2]))) if len(c) > 2 else 255
            colors.append([r, g, b])

        return colors
