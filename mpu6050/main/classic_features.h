/*
 * classic_features.h
 *
 * Bộ trích xuất đặc trưng thống kê C99 cho các thuật toán Classic Machine Learning.
 * Tính toán 1:1 đồng nhất với `logic/classic_ml/feature_extractor.py`.
 */

#ifndef CLASSIC_FEATURES_H
#define CLASSIC_FEATURES_H

#include <stdint.h>
#include <stddef.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

#define CLASSIC_ACCEL_SCALE   16384.0f  // MPU6050 +-2g
#define CLASSIC_GYRO_SCALE    131.0f    // MPU6050 +-250dps

/**
 * Trích xuất các đặc trưng thống kê từ buffer IMU thô (int16_t).
 *
 * @param raw_buffer: Mảng int16_t chứa num_samples * 6 giá trị [ax, ay, az, gx, gy, gz, ...].
 * @param num_samples: Số lượng mẫu trong cửa sổ (thường là 64).
 * @param out_features: Mảng float đầu ra chứa các đặc trưng đã tính toán.
 * @return Số lượng đặc trưng đã ghi vào out_features.
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

    // 1. Trích xuất đặc trưng trên từng kênh trong 6 kênh
    for (int ch = 0; ch < 6; ++ch) {
        float scale = (ch < 3) ? CLASSIC_ACCEL_SCALE : CLASSIC_GYRO_SCALE;
        float inv_scale = 1.0f / scale;

        float sum = 0.0f;
        float min_val = 1e9f;
        float max_val = -1e9f;
        float sum_sq = 0.0f;

        // Pass 1: Mean, Min, Max, SumSq
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

        // Pass 2: Std và Zero-Crossing Rate
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

        // Lưu các đặc trưng theo đúng thứ tự của Python feature_extractor
        out_features[feat_idx++] = mean;
        out_features[feat_idx++] = std_val;
        out_features[feat_idx++] = min_val;
        out_features[feat_idx++] = max_val;
        out_features[feat_idx++] = range_val;
        out_features[feat_idx++] = rms;
        out_features[feat_idx++] = energy;
        out_features[feat_idx++] = zcr;
    }

    // 2. Magnitudes (acc_mag & gyro_mag)
    for (int mag_type = 0; mag_type < 2; ++mag_type) {
        float sum = 0.0f;
        float min_val = 1e9f;
        float max_val = -1e9f;
        float sum_sq = 0.0f;

        float inv_s = (mag_type == 0) ? (1.0f / CLASSIC_ACCEL_SCALE) : (1.0f / CLASSIC_GYRO_SCALE);
        int ch_offset = (mag_type == 0) ? 0 : 3;

        for (int i = 0; i < num_samples; ++i) {
            float x = (float)raw_buffer[i * 6 + ch_offset + 0] * inv_s;
            float y = (float)raw_buffer[i * 6 + ch_offset + 1] * inv_s;
            float z = (float)raw_buffer[i * 6 + ch_offset + 2] * inv_s;
            float mag = sqrtf(x * x + y * y + z * z);

            sum += mag;
            sum_sq += mag * mag;
            if (mag < min_val) min_val = mag;
            if (mag > max_val) max_val = mag;
        }

        float mean = sum * inv_N;
        float range_val = max_val - min_val;
        float rms = sqrtf(sum_sq * inv_N);
        float energy = sum_sq * inv_N;

        // Pass 2: Std
        float var_sum = 0.0f;
        for (int i = 0; i < num_samples; ++i) {
            float x = (float)raw_buffer[i * 6 + ch_offset + 0] * inv_s;
            float y = (float)raw_buffer[i * 6 + ch_offset + 1] * inv_s;
            float z = (float)raw_buffer[i * 6 + ch_offset + 2] * inv_s;
            float mag = sqrtf(x * x + y * y + z * z);
            float diff = mag - mean;
            var_sum += diff * diff;
        }
        float std_val = sqrtf(var_sum * inv_N);

        out_features[feat_idx++] = mean;
        out_features[feat_idx++] = std_val;
        out_features[feat_idx++] = max_val;
        out_features[feat_idx++] = range_val;
        out_features[feat_idx++] = rms;
        out_features[feat_idx++] = energy;
    }

    // 3. Cross derivatives
    float sum_az_gx = 0.0f;
    float sum_az_gy = 0.0f;
    float max_jerk_z = 0.0f;
    float prev_az = (float)raw_buffer[0 * 6 + 2] / CLASSIC_ACCEL_SCALE;

    for (int i = 0; i < num_samples; ++i) {
        float az = (float)raw_buffer[i * 6 + 2] / CLASSIC_ACCEL_SCALE;
        float gx = (float)raw_buffer[i * 6 + 3] / CLASSIC_GYRO_SCALE;
        float gy = (float)raw_buffer[i * 6 + 4] / CLASSIC_GYRO_SCALE;

        sum_az_gx += (az * gx);
        sum_az_gy += (az * gy);

        if (i > 0) {
            float jerk = fabsf(az - prev_az);
            if (jerk > max_jerk_z) max_jerk_z = jerk;
            prev_az = az;
        }
    }

    out_features[feat_idx++] = sum_az_gx * inv_N;
    out_features[feat_idx++] = sum_az_gy * inv_N;
    out_features[feat_idx++] = max_jerk_z;

    return feat_idx;
}

#ifdef __cplusplus
}
#endif

#endif // CLASSIC_FEATURES_H
