/*
 * classic_features.h — Bộ trích xuất đặc trưng thống kê & động lực IMU cho ESP32.
 *
 * Đồng nhất 1:1 với `ml_lab/data/feature_extraction.py` (ClassicFeatureExtractor).
 * Chuẩn C99 / C++, không cấp phát động (Zero malloc), tối ưu cho vi điều khiển ESP32.
 */

#ifndef CLASSIC_FEATURES_H
#define CLASSIC_FEATURES_H

#include <stdint.h>
#include <stddef.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef CLASSIC_NUM_FEATURES
#define CLASSIC_NUM_FEATURES 63
#endif

#define CLASSIC_ACCEL_SCALE  16384.0f  // MPU6050 +-2g (1g = 16384 LSB)
#define CLASSIC_GYRO_SCALE   131.0f    // MPU6050 +-250dps (1 dps = 131 LSB)

/**
 * Trích xuất đặc trưng từ mảng buffer IMU thô (int16_t).
 *
 * @param raw_buffer: Mảng int16_t chứa num_samples * 6 giá trị [ax, ay, az, gx, gy, gz, ...].
 * @param num_samples: Số lượng mẫu trong cửa sổ trượt (mặc định 64 mẫu ~ 1.28s tại 50Hz).
 * @param out_features: Mảng float đầu ra kích thước tối thiểu CLASSIC_NUM_FEATURES.
 * @return Số lượng đặc trưng đã trích xuất.
 */
static inline int extract_classic_features(
    const int16_t* raw_buffer,
    int num_samples,
    float* out_features
) {
    if (raw_buffer == NULL || out_features == NULL || num_samples < 2) {
        return 0;
    }

    int feat_idx = 0;
    const float inv_N = 1.0f / (float)num_samples;

    // 1. Trích xuất đặc trưng cơ bản trên 6 kênh (6 * 8 = 48 đặc trưng)
    for (int ch = 0; ch < 6; ++ch) {
        float scale = (ch < 3) ? CLASSIC_ACCEL_SCALE : CLASSIC_GYRO_SCALE;
        float inv_scale = 1.0f / scale;

        float sum = 0.0f;
        float min_val = 1e9f;
        float max_val = -1e9f;
        float sum_sq = 0.0f;

        // Pass 1: Sum, Min, Max, Energy (SumSq)
        for (int i = 0; i < num_samples; ++i) {
            float val = (float)raw_buffer[i * 6 + ch] * inv_scale;
            sum += val;
            sum_sq += val * val;
            if (val < min_val) min_val = val;
            if (val > max_val) max_val = val;
        }

        float mean = sum * inv_N;
        float range_val = max_val - min_val;
        float rms = sqrtf(sum_sq * inv_N);
        float energy = sum_sq * inv_N;

        // Pass 2: Std (Độ lệch chuẩn) và Zero-Crossing Rate (Tần số đổi dấu)
        float var_sum = 0.0f;
        int zcr_count = 0;
        float prev_centered = ((float)raw_buffer[0 * 6 + ch] * inv_scale) - mean;

        for (int i = 0; i < num_samples; ++i) {
            float val = (float)raw_buffer[i * 6 + ch] * inv_scale;
            float diff = val - mean;
            var_sum += diff * diff;

            if (i > 0) {
                if ((prev_centered < 0.0f && diff >= 0.0f) || (prev_centered >= 0.0f && diff < 0.0f)) {
                    zcr_count++;
                }
                prev_centered = diff;
            }
        }

        float std_val = sqrtf(var_sum * inv_N);
        float zcr = (float)zcr_count / (float)(num_samples - 1);

        // Ghi tuần tự 8 đặc trưng cho mỗi kênh
        out_features[feat_idx++] = mean;
        out_features[feat_idx++] = std_val;
        out_features[feat_idx++] = min_val;
        out_features[feat_idx++] = max_val;
        out_features[feat_idx++] = range_val;
        out_features[feat_idx++] = rms;
        out_features[feat_idx++] = energy;
        out_features[feat_idx++] = zcr;
    }

    // 2. Độ lớn tổng hợp (Magnitudes: acc_mag, gyro_mag -> 12 đặc trưng)
    if (feat_idx < CLASSIC_NUM_FEATURES) {
        float inv_acc_scale = 1.0f / CLASSIC_ACCEL_SCALE;
        float inv_gyr_scale = 1.0f / CLASSIC_GYRO_SCALE;

        for (int mag_type = 0; mag_type < 2; ++mag_type) {
            float sum = 0.0f;
            float sum_sq = 0.0f;
            float min_val = 1e9f;
            float max_val = -1e9f;

            for (int i = 0; i < num_samples; ++i) {
                float v0, v1, v2;
                if (mag_type == 0) {
                    v0 = (float)raw_buffer[i * 6 + 0] * inv_acc_scale;
                    v1 = (float)raw_buffer[i * 6 + 1] * inv_acc_scale;
                    v2 = (float)raw_buffer[i * 6 + 2] * inv_acc_scale;
                } else {
                    v0 = (float)raw_buffer[i * 6 + 3] * inv_gyr_scale;
                    v1 = (float)raw_buffer[i * 6 + 4] * inv_gyr_scale;
                    v2 = (float)raw_buffer[i * 6 + 5] * inv_gyr_scale;
                }
                float mag = sqrtf(v0 * v0 + v1 * v1 + v2 * v2);
                sum += mag;
                sum_sq += mag * mag;
                if (mag < min_val) min_val = mag;
                if (mag > max_val) max_val = mag;
            }

            float mean = sum * inv_N;
            float range_val = max_val - min_val;
            float rms = sqrtf(sum_sq * inv_N);
            float energy = sum_sq * inv_N;

            float var_sum = 0.0f;
            for (int i = 0; i < num_samples; ++i) {
                float v0, v1, v2;
                if (mag_type == 0) {
                    v0 = (float)raw_buffer[i * 6 + 0] * inv_acc_scale;
                    v1 = (float)raw_buffer[i * 6 + 1] * inv_acc_scale;
                    v2 = (float)raw_buffer[i * 6 + 2] * inv_acc_scale;
                } else {
                    v0 = (float)raw_buffer[i * 6 + 3] * inv_gyr_scale;
                    v1 = (float)raw_buffer[i * 6 + 4] * inv_gyr_scale;
                    v2 = (float)raw_buffer[i * 6 + 5] * inv_gyr_scale;
                }
                float mag = sqrtf(v0 * v0 + v1 * v1 + v2 * v2);
                float diff = mag - mean;
                var_sum += diff * diff;
            }
            float std_val = sqrtf(var_sum * inv_N);

            if (feat_idx < CLASSIC_NUM_FEATURES) out_features[feat_idx++] = mean;
            if (feat_idx < CLASSIC_NUM_FEATURES) out_features[feat_idx++] = std_val;
            if (feat_idx < CLASSIC_NUM_FEATURES) out_features[feat_idx++] = max_val;
            if (feat_idx < CLASSIC_NUM_FEATURES) out_features[feat_idx++] = range_val;
            if (feat_idx < CLASSIC_NUM_FEATURES) out_features[feat_idx++] = rms;
            if (feat_idx < CLASSIC_NUM_FEATURES) out_features[feat_idx++] = energy;
        }
    }

    // 3. Vi phân chéo (Cross Derivatives: az_gx, az_gy, jerk_z_max -> 3 đặc trưng)
    if (feat_idx < CLASSIC_NUM_FEATURES) {
        float inv_acc_scale = 1.0f / CLASSIC_ACCEL_SCALE;
        float inv_gyr_scale = 1.0f / CLASSIC_GYRO_SCALE;

        float sum_az_gx = 0.0f;
        float sum_az_gy = 0.0f;
        float max_jerk_z = 0.0f;
        float prev_az = (float)raw_buffer[0 * 6 + 2] * inv_acc_scale;

        for (int i = 0; i < num_samples; ++i) {
            float az = (float)raw_buffer[i * 6 + 2] * inv_acc_scale;
            float gx = (float)raw_buffer[i * 6 + 3] * inv_gyr_scale;
            float gy = (float)raw_buffer[i * 6 + 4] * inv_gyr_scale;

            sum_az_gx += az * gx;
            sum_az_gy += az * gy;

            if (i > 0) {
                float jerk = fabsf(az - prev_az);
                if (jerk > max_jerk_z) max_jerk_z = jerk;
                prev_az = az;
            }
        }

        if (feat_idx < CLASSIC_NUM_FEATURES) out_features[feat_idx++] = sum_az_gx * inv_N;
        if (feat_idx < CLASSIC_NUM_FEATURES) out_features[feat_idx++] = sum_az_gy * inv_N;
        if (feat_idx < CLASSIC_NUM_FEATURES) out_features[feat_idx++] = max_jerk_z;
    }

    return feat_idx;
}

#ifdef __cplusplus
}
#endif

#endif // CLASSIC_FEATURES_H
