"""
logic/classic_ml/c_generator.py

Trình sinh mã nguồn C thuần (Pure C99 Code Generator) cho các mô hình Classic ML.
Sinh file header-only `model_classic.h` không phụ thuộc bất kỳ thư viện ngoài nào,
tương thích hoàn hảo với ESP32 ESP-IDF, Arduino IDE, STM32 và mọi nền tảng nhúng C/C++.
"""

from __future__ import annotations

import datetime
from typing import Any
import numpy as np

from logic.classic_ml.trainer import TrainResult


class CCodeGenerator:
    """
    Sinh mã nguồn C99 độc lập từ kết quả huấn luyện TrainResult.
    """

    def generate_header(self, result: TrainResult) -> str:
        """
        Sinh toàn bộ nội dung file header C `model_classic.h`.
        """
        model_type = result.model_type.lower()
        class_names = result.class_names
        num_classes = len(class_names)
        num_features = len(result.feature_names)

        # Header metadata
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines: list[str] = [
            "/*",
            " * AUTO-GENERATED CLASSIC MACHINE LEARNING MODEL HEADER",
            f" * Generated at: {now_str}",
            f" * Model Type   : {result.model_name_display}",
            f" * Test Accuracy: {result.accuracy * 100:.2f}% (CV: {result.cv_mean * 100:.2f}%)",
            f" * Classes ({num_classes}) : {', '.join(class_names)}",
            f" * Features ({num_features}): {', '.join(result.feature_names[:6])}...",
            " *",
            " * Target: ESP32 / Arduino / Any C99 Microcontroller",
            " * Zero external dependencies, pure standard math.h",
            " */",
            "",
            "#ifndef MODEL_CLASSIC_H",
            "#define MODEL_CLASSIC_H",
            "",
            "#include <stdint.h>",
            "#include <stddef.h>",
            "#include <math.h>",
            "",
            "#ifdef __cplusplus",
            'extern "C" {',
            "#endif",
            "",
            f"#define CLASSIC_MODEL_TYPE_{model_type.upper()} 1",
            f"#define CLASSIC_NUM_CLASSES {num_classes}",
            f"#define CLASSIC_NUM_FEATURES {num_features}",
            "",
            "// Tên các lớp cử chỉ",
            "static const char* const CLASSIC_CLASS_NAMES[CLASSIC_NUM_CLASSES] = {",
        ]
        for name in class_names:
            lines.append(f'    "{name}",')
        lines.append("};")
        lines.append("")

        # 1. Standard Scaler parameters
        if result.scaler is not None:
            means = result.scaler.mean_
            scales = result.scaler.scale_
            lines.append("// Tham số chuẩn hóa StandardScaler (x - mean) / scale")
            lines.append(f"static const float CLASSIC_SCALER_MEANS[{num_features}] = {{")
            lines.append(self._format_float_array(means))
            lines.append("};")
            lines.append(f"static const float CLASSIC_SCALER_SCALES[{num_features}] = {{")
            lines.append(self._format_float_array(scales))
            lines.append("};")
            lines.append("")
            lines.append("static inline void classic_scale_features(const float* in, float* out) {")
            lines.append(f"    for (int i = 0; i < {num_features}; ++i) {{")
            lines.append("        out[i] = (in[i] - CLASSIC_SCALER_MEANS[i]) / CLASSIC_SCALER_SCALES[i];")
            lines.append("    }")
            lines.append("}")
        else:
            lines.append("// Không sử dụng StandardScaler cho mô hình này")
            lines.append("static inline void classic_scale_features(const float* in, float* out) {")
            lines.append(f"    for (int i = 0; i < {num_features}; ++i) {{ out[i] = in[i]; }}")
            lines.append("}")
        lines.append("")

        # 2. Sinh mã cho từng loại mô hình cụ thể
        if model_type == "tree":
            lines.extend(self._generate_decision_tree(result.model, num_classes))
        elif model_type == "forest":
            lines.extend(self._generate_random_forest(result.model, num_classes))
        elif model_type == "logistic":
            lines.extend(self._generate_logistic_regression(result.model, num_classes, num_features))
        elif model_type == "svm":
            lines.extend(self._generate_svm(result.model, num_classes, num_features))
        elif model_type == "knn":
            lines.extend(self._generate_knn(result.model, num_classes, num_features))
        else:
            lines.extend(self._generate_fallback(num_classes))

        # Helper getters
        lines.extend([
            "",
            "static inline const char* classic_get_class_name(int class_idx) {",
            "    if (class_idx >= 0 && class_idx < CLASSIC_NUM_CLASSES) {",
            "        return CLASSIC_CLASS_NAMES[class_idx];",
            "    }",
            '    return "UNKNOWN";',
            "}",
            "",
            "#ifdef __cplusplus",
            "}",
            "#endif",
            "",
            "#endif // MODEL_CLASSIC_H",
        ])

        return "\n".join(lines)

    def _format_float_array(self, arr: Sequence[float], indent: str = "    ") -> str:
        """Format mảng số thực float với căn lề đẹp."""
        items: list[str] = []
        for i, val in enumerate(arr):
            v_str = f"{float(val):.7f}f"
            items.append(v_str)
        # Nhóm mỗi dòng 6 phần tử
        lines: list[str] = []
        for i in range(0, len(items), 6):
            chunk = items[i:i + 6]
            lines.append(f"{indent}{', '.join(chunk)},")
        return "\n".join(lines)

    def _generate_decision_tree(self, tree_model: Any, num_classes: int) -> list[str]:
        """Sinh mã C duyệt node cây quyết định nhị phân."""
        tree = tree_model.tree_
        n_nodes = tree.node_count
        children_left = tree.children_left
        children_right = tree.children_right
        feature = tree.feature
        threshold = tree.threshold
        value = tree.value

        lines: list[str] = [
            "// Cấu trúc Node Cây Quyết Định",
            "typedef struct {",
            "    int16_t feature;       // Chỉ số đặc trưng so sánh (< 0 nếu là node lá)",
            "    float threshold;       // Ngưỡng so sánh",
            "    int16_t left_child;    // Chỉ số node con bên trái",
            "    int16_t right_child;   // Chỉ số node con bên phải",
            "    int8_t class_idx;      // Lớp phân loại tại node lá",
            "} TreeNode_t;",
            "",
            f"static const TreeNode_t TREE_NODES[{n_nodes}] = {{",
        ]

        for i in range(n_nodes):
            f_idx = feature[i]
            thresh = threshold[i]
            left = children_left[i]
            right = children_right[i]
            cls_idx = int(np.argmax(value[i][0])) if left == -1 else -1

            lines.append(
                f"    {{{f_idx}, {thresh:.7f}f, {left}, {right}, {cls_idx}}}, // Node {i}"
            )
        lines.append("};")
        lines.append("")

        lines.extend([
            "// Hàm dự đoán phân loại qua Cây Quyết Định",
            "static inline int classic_predict(const float* raw_features, float* out_confidence) {",
            "    float scaled[CLASSIC_NUM_FEATURES];",
            "    classic_scale_features(raw_features, scaled);",
            "",
            "    int curr = 0;",
            f"    while (curr >= 0 && curr < {n_nodes}) {{",
            "        const TreeNode_t* node = &TREE_NODES[curr];",
            "        if (node->left_child == -1 && node->right_child == -1) {",
            "            if (out_confidence != NULL) *out_confidence = 1.0f;",
            "            return (int)node->class_idx;",
            "        }",
            "        if (scaled[node->feature] <= node->threshold) {",
            "            curr = node->left_child;",
            "        } else {",
            "            curr = node->right_child;",
            "        }",
            "    }",
            "    if (out_confidence != NULL) *out_confidence = 0.0f;",
            "    return 0;",
            "}",
        ])
        return lines

    def _generate_random_forest(self, forest_model: Any, num_classes: int) -> list[str]:
        """Sinh mã C cho tập hợp cây Random Forest và biểu quyết đa số."""
        estimators = forest_model.estimators_
        n_trees = len(estimators)

        lines: list[str] = [
            "typedef struct {",
            "    int16_t feature;",
            "    float threshold;",
            "    int16_t left_child;",
            "    int16_t right_child;",
            "    int8_t class_idx;",
            "} RFNode_t;",
            "",
        ]

        tree_node_counts: list[int] = []
        for t_idx, est in enumerate(estimators):
            tree = est.tree_
            n_nodes = tree.node_count
            tree_node_counts.append(n_nodes)
            lines.append(f"static const RFNode_t RF_TREE_{t_idx}_NODES[{n_nodes}] = {{")
            for i in range(n_nodes):
                f_idx = tree.feature[i]
                thresh = tree.threshold[i]
                left = tree.children_left[i]
                right = tree.children_right[i]
                cls_idx = int(np.argmax(tree.value[i][0])) if left == -1 else -1
                lines.append(f"    {{{f_idx}, {thresh:.7f}f, {left}, {right}, {cls_idx}}},")
            lines.append("};")
            lines.append("")

        lines.extend([
            f"#define RF_NUM_TREES {n_trees}",
            "",
            "static inline int classic_predict(const float* raw_features, float* out_confidence) {",
            "    float scaled[CLASSIC_NUM_FEATURES];",
            "    classic_scale_features(raw_features, scaled);",
            "",
            f"    int votes[{num_classes}] = {{0}};",
            "    int curr = 0;",
            "",
        ])

        for t_idx in range(n_trees):
            lines.extend([
                f"    // Duyệt Tree {t_idx}",
                "    curr = 0;",
                f"    while (curr >= 0 && curr < {tree_node_counts[t_idx]}) {{",
                f"        const RFNode_t* node = &RF_TREE_{t_idx}_NODES[curr];",
                "        if (node->left_child == -1) {",
                "            votes[node->class_idx]++;",
                "            break;",
                "        }",
                "        curr = (scaled[node->feature] <= node->threshold) ? node->left_child : node->right_child;",
                "    }",
            ])

        lines.extend([
            "",
            "    int best_class = 0;",
            "    int max_votes = votes[0];",
            f"    for (int c = 1; c < {num_classes}; ++c) {{",
            "        if (votes[c] > max_votes) {",
            "            max_votes = votes[c];",
            "            best_class = c;",
            "        }",
            "    }",
            f"    if (out_confidence != NULL) *out_confidence = (float)max_votes / (float)RF_NUM_TREES;",
            "    return best_class;",
            "}",
        ])
        return lines

    def _generate_logistic_regression(
        self, model: Any, num_classes: int, num_features: int
    ) -> list[str]:
        """Sinh mã C tính toán W * x + b và Softmax cho Logistic Regression."""
        raw_w = model.coef_
        raw_b = model.intercept_
        if len(raw_w) == 1 and num_classes == 2:
            weights = np.vstack([-raw_w[0] / 2.0, raw_w[0] / 2.0])
            biases = np.array([-raw_b[0] / 2.0, raw_b[0] / 2.0])
        else:
            weights = raw_w
            biases = raw_b

        lines: list[str] = [
            f"static const float LOGISTIC_WEIGHTS[{num_classes}][{num_features}] = {{",
        ]
        for c in range(num_classes):
            lines.append(f"    // Class {c}")
            lines.append(f"    {{")
            lines.append(self._format_float_array(weights[c], indent="        "))
            lines.append(f"    }},")
        lines.append("};")
        lines.append("")

        lines.append(f"static const float LOGISTIC_BIASES[{num_classes}] = {{")
        lines.append(self._format_float_array(biases))
        lines.append("};")
        lines.append("")

        lines.extend([
            "// Hàm dự đoán phân loại qua Hồi quy Logistic (Softmax argmax)",
            "static inline int classic_predict(const float* raw_features, float* out_confidence) {",
            "    float scaled[CLASSIC_NUM_FEATURES];",
            "    classic_scale_features(raw_features, scaled);",
            "",
            f"    float logits[{num_classes}];",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        float dot = LOGISTIC_BIASES[c];",
            f"        for (int j = 0; j < {num_features}; ++j) {{",
            "            dot += LOGISTIC_WEIGHTS[c][j] * scaled[j];",
            "        }",
            "        logits[c] = dot;",
            "    }",
            "",
            "    // Softmax",
            "    float max_logit = logits[0];",
            f"    for (int c = 1; c < {num_classes}; ++c) {{",
            "        if (logits[c] > max_logit) max_logit = logits[c];",
            "    }",
            "    float sum_exp = 0.0f;",
            f"    for (int c = 0; c < {num_classes}; ++c) {{",
            "        logits[c] = expf(logits[c] - max_logit);",
            "        sum_exp += logits[c];",
            "    }",
            "",
            "    int best_class = 0;",
            "    float best_prob = logits[0] / sum_exp;",
            f"    for (int c = 1; c < {num_classes}; ++c) {{",
            "        float prob = logits[c] / sum_exp;",
            "        if (prob > best_prob) {",
            "            best_prob = prob;",
            "            best_class = c;",
            "        }",
            "    }",
            "    if (out_confidence != NULL) *out_confidence = best_prob;",
            "    return best_class;",
            "}",
        ])
        return lines

    def _generate_svm(self, model: Any, num_classes: int, num_features: int) -> list[str]:
        """Sinh mã C cho SVM (hỗ trợ Linear và RBF kernel)."""
        kernel = model.kernel
        if kernel == "linear":
            # Linear SVM rút gọn thành trọng số W và bias b
            w = model.coef_ if hasattr(model, "coef_") else np.zeros((num_classes, num_features))
            b = model.intercept_ if hasattr(model, "intercept_") else np.zeros(num_classes)
            return self._generate_linear_svm(w, b, num_classes, num_features)
        else:
            # RBF Kernel SVM
            return self._generate_rbf_svm(model, num_classes, num_features)

    def _generate_linear_svm(
        self, w: np.ndarray, b: np.ndarray, num_classes: int, num_features: int
    ) -> list[str]:
        n_rows = len(w)
        lines: list[str] = [
            f"static const float SVM_W[{n_rows}][{num_features}] = {{",
        ]
        for c in range(n_rows):
            lines.append("    {")
            lines.append(self._format_float_array(w[c], indent="        "))
            lines.append("    },")
        lines.append("};")
        lines.append(f"static const float SVM_B[{n_rows}] = {{")
        lines.append(self._format_float_array(b))
        lines.append("};")
        lines.append("")

        lines.extend([
            "static inline int classic_predict(const float* raw_features, float* out_confidence) {",
            "    float scaled[CLASSIC_NUM_FEATURES];",
            "    classic_scale_features(raw_features, scaled);",
            "",
            f"    float scores[{n_rows}];",
            f"    for (int i = 0; i < {n_rows}; ++i) {{",
            "        float s = SVM_B[i];",
            f"        for (int j = 0; j < {num_features}; ++j) {{",
            "            s += SVM_W[i][j] * scaled[j];",
            "        }",
            "        scores[i] = s;",
            "    }",
            "",
            "    int best_c = 0;",
            "    float max_s = scores[0];",
            f"    for (int i = 1; i < {n_rows}; ++i) {{",
            "        if (scores[i] > max_s) { max_s = scores[i]; best_c = i; }",
            "    }",
            "    if (out_confidence != NULL) *out_confidence = 1.0f / (1.0f + expf(-fabsf(max_s)));",
            "    return best_c;",
            "}",
        ])
        return lines

    def _generate_rbf_svm(self, model: Any, num_classes: int, num_features: int) -> list[str]:
        sv = model.support_vectors_
        dual_coef = model.dual_coef_
        intercept = model.intercept_
        gamma = float(model._gamma) if hasattr(model, "_gamma") else 0.05
        n_sv = len(sv)

        lines: list[str] = [
            f"#define SVM_RBF_NUM_SV {n_sv}",
            f"#define SVM_RBF_GAMMA {gamma:.7f}f",
            "",
            f"static const float SVM_RBF_SV[SVM_RBF_NUM_SV][{num_features}] = {{",
        ]
        for i in range(n_sv):
            lines.append("    {")
            lines.append(self._format_float_array(sv[i], indent="        "))
            lines.append("    },")
        lines.append("};")
        lines.append("")

        n_coef_rows = len(dual_coef)
        lines.append(f"static const float SVM_RBF_DUAL_COEF[{n_coef_rows}][SVM_RBF_NUM_SV] = {{")
        for r in range(n_coef_rows):
            lines.append("    {")
            lines.append(self._format_float_array(dual_coef[r], indent="        "))
            lines.append("    },")
        lines.append("};")
        lines.append("")

        lines.append(f"static const float SVM_RBF_INTERCEPT[{len(intercept)}] = {{")
        lines.append(self._format_float_array(intercept))
        lines.append("};")
        lines.append("")

        lines.extend([
            "static inline int classic_predict(const float* raw_features, float* out_confidence) {",
            "    float scaled[CLASSIC_NUM_FEATURES];",
            "    classic_scale_features(raw_features, scaled);",
            "",
            "    float rbf_k[SVM_RBF_NUM_SV];",
            "    for (int i = 0; i < SVM_RBF_NUM_SV; ++i) {",
            "        float dist_sq = 0.0f;",
            f"        for (int j = 0; j < {num_features}; ++j) {{",
            "            float diff = scaled[j] - SVM_RBF_SV[i][j];",
            "            dist_sq += diff * diff;",
            "        }",
            "        rbf_k[i] = expf(-SVM_RBF_GAMMA * dist_sq);",
            "    }",
            "",
            f"    float dec[{len(intercept)}];",
            f"    for (int r = 0; r < {len(intercept)}; ++r) {{",
            "        float val = SVM_RBF_INTERCEPT[r];",
            "        for (int i = 0; i < SVM_RBF_NUM_SV; ++i) {",
            "            val += SVM_RBF_DUAL_COEF[r][i] * rbf_k[i];",
            "        }",
            "        dec[r] = val;",
            "    }",
            "",
            "    int best_c = (dec[0] >= 0.0f) ? 1 : 0;",
            "    if (out_confidence != NULL) *out_confidence = 1.0f / (1.0f + expf(-fabsf(dec[0])));",
            "    return best_c;",
            "}",
        ])
        return lines

    def _generate_knn(self, model: Any, num_classes: int, num_features: int) -> list[str]:
        """Sinh mã C tìm kiếm K láng giềng gần nhất (Euclidean Distance)."""
        X_train = model._fit_X
        y_train = model._y
        n_samples = len(X_train)
        k_val = int(model.n_neighbors)

        lines: list[str] = [
            f"#define KNN_K {k_val}",
            f"#define KNN_NUM_SAMPLES {n_samples}",
            "",
            f"static const float KNN_SAMPLES[KNN_NUM_SAMPLES][{num_features}] = {{",
        ]
        for i in range(n_samples):
            lines.append("    {")
            lines.append(self._format_float_array(X_train[i], indent="        "))
            lines.append("    },")
        lines.append("};")
        lines.append("")

        lines.append("static const uint8_t KNN_LABELS[KNN_NUM_SAMPLES] = {")
        lines.append("    " + ", ".join(str(int(l)) for l in y_train))
        lines.append("};")
        lines.append("")

        lines.extend([
            "static inline int classic_predict(const float* raw_features, float* out_confidence) {",
            "    float scaled[CLASSIC_NUM_FEATURES];",
            "    classic_scale_features(raw_features, scaled);",
            "",
            "    float top_dists[KNN_K];",
            "    int top_labels[KNN_K];",
            "    for (int k = 0; k < KNN_K; ++k) { top_dists[k] = 1e30f; top_labels[k] = -1; }",
            "",
            "    for (int s = 0; s < KNN_NUM_SAMPLES; ++s) {",
            "        float d = 0.0f;",
            f"        for (int j = 0; j < {num_features}; ++j) {{",
            "            float diff = scaled[j] - KNN_SAMPLES[s][j];",
            "            d += diff * diff;",
            "        }",
            "        // Insertion sort vao top-k",
            "        for (int k = 0; k < KNN_K; ++k) {",
            "            if (d < top_dists[k]) {",
            "                for (int m = KNN_K - 1; m > k; --m) {",
            "                    top_dists[m] = top_dists[m - 1];",
            "                    top_labels[m] = top_labels[m - 1];",
            "                }",
            "                top_dists[k] = d;",
            "                top_labels[k] = (int)KNN_LABELS[s];",
            "                break;",
            "            }",
            "        }",
            "    }",
            "",
            f"    int votes[{num_classes}] = {{0}};",
            "    for (int k = 0; k < KNN_K; ++k) {",
            "        if (top_labels[k] >= 0) votes[top_labels[k]]++;",
            "    }",
            "    int best_c = 0;",
            "    int max_v = votes[0];",
            f"    for (int c = 1; c < {num_classes}; ++c) {{",
            "        if (votes[c] > max_v) { max_v = votes[c]; best_c = c; }",
            "    }",
            "    if (out_confidence != NULL) *out_confidence = (float)max_v / (float)KNN_K;",
            "    return best_c;",
            "}",
        ])
        return lines

    def _generate_fallback(self, num_classes: int) -> list[str]:
        return [
            "static inline int classic_predict(const float* raw_features, float* out_confidence) {",
            "    (void)raw_features;",
            "    if (out_confidence != NULL) *out_confidence = 1.0f;",
            "    return 0;",
            "}",
        ]
