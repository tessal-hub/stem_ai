/*
 * ============================================================================
 * AUTO-GENERATED CLASSIC MACHINE LEARNING MODEL HEADER (STEM ML LAB)
 * Generated at : 2026-08-26 14:51:07
 * Algorithm    : Linear Discriminant Analysis (LDA)
 * Val Accuracy : 96.64% (CV: 95.56%)
 * Classes (8)  : A, B, BOOST, COPY, FIREBALL, P, REFLECT, STOP
 * Features (63) : 63 extracted IMU statistics
 * Target: ESP32 / ESP32-S3 (ESP-IDF & Arduino)
 * ============================================================================
 */

#ifndef MODEL_CLASSIC_H
#define MODEL_CLASSIC_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define CLASSIC_MODEL_ALGO "lda"
#define CLASSIC_NUM_CLASSES 8
#ifndef CLASSIC_NUM_FEATURES
#define CLASSIC_NUM_FEATURES 63
#endif

/**
 * Thực hiện suy luận phân loại cử chỉ từ vector đặc trưng IMU đầu vào.
 *
 * @param raw_features: Mảng float gồm 63 đặc trưng IMU (đúng thứ tự feature_names).
 * @param out_confidence: Con trỏ float nhận độ tin cậy dự đoán (0.0 -> 1.0).
 * @return Chỉ số index của lớp dự đoán (0 -> CLASSIC_NUM_CLASSES - 1).
 */
int classic_predict(const float* raw_features, float* out_confidence);

/**
 * Trả về chuỗi tên của lớp cử chỉ theo index.
 */
const char* classic_get_class_name(int class_idx);

/**
 * Lấy cấu hình màu RGB (0-255) cho từng phép thuật / cử chỉ.
 */
void classic_get_class_rgb(int class_idx, uint8_t* r, uint8_t* g, uint8_t* b);

#ifdef __cplusplus
}
#endif

#endif // MODEL_CLASSIC_H