/*
 * main.cpp — Chương trình thực thi chính (Main Runtime) cho ESP32 Classic ML.
 *
 * Đọc dữ liệu cảm biến MPU6050 qua I2C (50Hz), duy trì cửa sổ trượt 64 mẫu.
 * Tích hợp Motion Gate (Ngưỡng kích hoạt động học) để loại bỏ nhiễu khi đũa đứng yên,
 * trích xuất đặc trưng và gọi suy luận `classic_predict()` khi có chuyển động thực tế.
 * Hiển thị màu LED RGB theo đúng cấu hình của từng phép thuật trong SpellConfigStore.
 * Xuất dữ liệu qua UART tương thích với Tab 7 Serial Monitor của STEM ML Lab.
 */

#include <cstdio>
#include <cstring>
#include <cmath>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/ledc.h"

#include "classic_features.h"
#include "model_classic.h"

static const char* TAG = "STEM_CLASSIC_ML";

// ========== Cấu hình I2C & MPU6050 ==========
#define I2C_PORT               I2C_NUM_0
#define I2C_SDA_PIN            GPIO_NUM_21
#define I2C_SCL_PIN            GPIO_NUM_22
#define I2C_FREQ_HZ            400000
#define MPU6050_ADDR           0x68

// ========== Cấu hình Cửa Sổ Trượt ==========
#define WINDOW_SAMPLES         64    // 64 mẫu (~1.28 giây tại 50Hz)
#define STEP_SAMPLES           16    // Bước nhảy 16 mẫu (~320ms quét 1 lần)
#define SAMPLING_PERIOD_MS     20    // 50Hz = 20ms
#define COOLDOWN_SAMPLES       36    // Cooldown ~720ms sau mỗi lần kích hoạt cử chỉ

// Ngưỡng chuyển động tối thiểu để kích hoạt AI (loại bỏ trạng thái Standby / Đứng yên)
#define MIN_ACC_STD_SUM        0.12f // Tổng độ lệch chuẩn gia tốc 3 trục >= 0.12g
#define MIN_GYR_STD_SUM        20.0f // Tổng độ lệch chuẩn vận tốc góc 3 trục >= 20 dps
#define MIN_CONFIDENCE         0.70f // Độ tin cậy tối thiểu của mô hình

// Buffer tĩnh để không gây tràn stack FreeRTOS
static int16_t s_raw_buffer[WINDOW_SAMPLES * 6];
static int16_t s_ordered_buffer[WINDOW_SAMPLES * 6];
static int s_buffer_head = 0;
static int s_sample_count = 0;
static int s_step_counter = 0;
static int s_cooldown_counter = 0;

static float s_features[CLASSIC_NUM_FEATURES];

// ========== Cấu hình LED RGB (LEDC PWM 24-bit Color) ==========
#define RGB_R_PIN              GPIO_NUM_25
#define RGB_G_PIN              GPIO_NUM_26
#define RGB_B_PIN              GPIO_NUM_27

static void init_rgb_led() {
    ledc_timer_config_t ledc_timer = {};
    ledc_timer.speed_mode       = LEDC_LOW_SPEED_MODE;
    ledc_timer.timer_num        = LEDC_TIMER_0;
    ledc_timer.duty_resolution  = LEDC_TIMER_8_BIT; // 0 - 255
    ledc_timer.freq_hz          = 5000;              // 5 kHz PWM
    ledc_timer.clk_cfg          = LEDC_AUTO_CLK;
    ledc_timer_config(&ledc_timer);

    ledc_channel_config_t ch_r = {};
    ch_r.speed_mode = LEDC_LOW_SPEED_MODE;
    ch_r.channel    = LEDC_CHANNEL_0;
    ch_r.timer_sel  = LEDC_TIMER_0;
    ch_r.gpio_num   = RGB_R_PIN;
    ch_r.duty       = 0;
    ch_r.hpoint     = 0;
    ledc_channel_config(&ch_r);

    ledc_channel_config_t ch_g = {};
    ch_g.speed_mode = LEDC_LOW_SPEED_MODE;
    ch_g.channel    = LEDC_CHANNEL_1;
    ch_g.timer_sel  = LEDC_TIMER_0;
    ch_g.gpio_num   = RGB_G_PIN;
    ch_g.duty       = 0;
    ch_g.hpoint     = 0;
    ledc_channel_config(&ch_g);

    ledc_channel_config_t ch_b = {};
    ch_b.speed_mode = LEDC_LOW_SPEED_MODE;
    ch_b.channel    = LEDC_CHANNEL_2;
    ch_b.timer_sel  = LEDC_TIMER_0;
    ch_b.gpio_num   = RGB_B_PIN;
    ch_b.duty       = 0;
    ch_b.hpoint     = 0;
    ledc_channel_config(&ch_b);
}

static void set_rgb_color(uint8_t r, uint8_t g, uint8_t b) {
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, (uint32_t)r);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);

    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1, (uint32_t)g);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1);

    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_2, (uint32_t)b);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_2);
}

// ========== I2C MPU6050 Driver ==========
static i2c_master_bus_handle_t s_i2c_bus = NULL;
static i2c_master_dev_handle_t s_mpu_dev = NULL;

static esp_err_t init_mpu6050() {
    i2c_master_bus_config_t bus_config = {};
    bus_config.i2c_port = I2C_PORT;
    bus_config.sda_io_num = (gpio_num_t)I2C_SDA_PIN;
    bus_config.scl_io_num = (gpio_num_t)I2C_SCL_PIN;
    bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
    bus_config.glitch_ignore_cnt = 7;
    bus_config.flags.enable_internal_pullup = true;

    esp_err_t ret = i2c_new_master_bus(&bus_config, &s_i2c_bus);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Lỗi khởi tạo I2C bus: %s", esp_err_to_name(ret));
        return ret;
    }

    i2c_device_config_t dev_config = {};
    dev_config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    dev_config.device_address = MPU6050_ADDR;
    dev_config.scl_speed_hz = I2C_FREQ_HZ;

    ret = i2c_master_bus_add_device(s_i2c_bus, &dev_config, &s_mpu_dev);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Lỗi add MPU6050 device: %s", esp_err_to_name(ret));
        return ret;
    }

    // Wake up MPU6050 (PWR_MGMT_1 = 0)
    uint8_t wake_cmd[2] = {0x6B, 0x00};
    ret = i2c_master_transmit(s_mpu_dev, wake_cmd, sizeof(wake_cmd), 100);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Không thể đánh thức MPU6050 (thử lại)");
    } else {
        ESP_LOGI(TAG, "MPU6050 đã sẵn sàng!");
    }
    return ret;
}

static bool read_mpu6050_raw(int16_t* ax, int16_t* ay, int16_t* az, int16_t* gx, int16_t* gy, int16_t* gz) {
    if (!s_mpu_dev) return false;

    uint8_t reg = 0x3B; // ACCEL_XOUT_H
    uint8_t data[14];

    esp_err_t ret = i2c_master_transmit_receive(s_mpu_dev, &reg, 1, data, 14, 50);
    if (ret != ESP_OK) {
        return false;
    }

    *ax = (int16_t)((data[0] << 8) | data[1]);
    *ay = (int16_t)((data[2] << 8) | data[3]);
    *az = (int16_t)((data[4] << 8) | data[5]);
    *gx = (int16_t)((data[8] << 8) | data[9]);
    *gy = (int16_t)((data[10] << 8) | data[11]);
    *gz = (int16_t)((data[12] << 8) | data[13]);

    return true;
}

// ========== Main Inference Task ==========
static void classic_ml_task(void* pvParameters) {
    ESP_LOGI(TAG, "Bắt đầu Classic ML Inference Engine...");
    ESP_LOGI(TAG, "Mô hình: %s | Số lớp: %d | Số đặc trưng: %d",
             CLASSIC_MODEL_ALGO, CLASSIC_NUM_CLASSES, CLASSIC_NUM_FEATURES);

    init_mpu6050();
    init_rgb_led();

    // Hiệu ứng LED chào mừng (Xanh lam -> Tắt)
    set_rgb_color(0, 0, 255);
    vTaskDelay(pdMS_TO_TICKS(250));
    set_rgb_color(0, 0, 0);

    TickType_t last_wake_time = xTaskGetTickCount();

    while (1) {
        int16_t ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0;
        if (read_mpu6050_raw(&ax, &ay, &az, &gx, &gy, &gz)) {
            // Đưa mẫu vào buffer xoay vòng
            int base_idx = (s_buffer_head % WINDOW_SAMPLES) * 6;
            s_raw_buffer[base_idx + 0] = ax;
            s_raw_buffer[base_idx + 1] = ay;
            s_raw_buffer[base_idx + 2] = az;
            s_raw_buffer[base_idx + 3] = gx;
            s_raw_buffer[base_idx + 4] = gy;
            s_raw_buffer[base_idx + 5] = gz;

            s_buffer_head = (s_buffer_head + 1) % WINDOW_SAMPLES;
            s_sample_count++;
            s_step_counter++;

            // Giảm dần bộ đếm Cooldown
            if (s_cooldown_counter > 0) {
                s_cooldown_counter--;
            }

            // Khi đủ 1 cửa sổ và đúng chu kỳ step
            if (s_sample_count >= WINDOW_SAMPLES && s_step_counter >= STEP_SAMPLES) {
                s_step_counter = 0;

                // Chuẩn bị buffer tuần tự theo thời gian
                for (int i = 0; i < WINDOW_SAMPLES; ++i) {
                    int src_idx = ((s_buffer_head + i) % WINDOW_SAMPLES) * 6;
                    memcpy(&s_ordered_buffer[i * 6], &s_raw_buffer[src_idx], sizeof(int16_t) * 6);
                }

                // 1. Trích xuất đặc trưng
                int64_t t_start = esp_timer_get_time();
                memset(s_features, 0, sizeof(s_features));
                extract_classic_features(s_ordered_buffer, WINDOW_SAMPLES, s_features);

                // 2. Motion Gate: Kiểm tra độ biến thiên động học thực tế
                // std_val của từng kênh: ax[1], ay[9], az[17], gx[25], gy[33], gz[41]
                float acc_std_sum = s_features[0 * 8 + 1] + s_features[1 * 8 + 1] + s_features[2 * 8 + 1];
                float gyr_std_sum = s_features[3 * 8 + 1] + s_features[4 * 8 + 1] + s_features[5 * 8 + 1];

                bool is_moving = (acc_std_sum >= MIN_ACC_STD_SUM) || (gyr_std_sum >= MIN_GYR_STD_SUM);

                // Chỉ chạy suy luận và kích hoạt cử chỉ khi đũa thực sự chuyển động và hết cooldown
                if (is_moving && s_cooldown_counter == 0) {
                    float confidence = 0.0f;
                    int pred_class = classic_predict(s_features, &confidence);
                    int64_t t_end = esp_timer_get_time();
                    float elapsed_ms = (float)(t_end - t_start) / 1000.0f;

                    if (confidence >= MIN_CONFIDENCE) {
                        const char* spell_name = classic_get_class_name(pred_class);
                        printf("[PREDICT] %s (conf=%.1f%%, latency=%.2fms)\n",
                               spell_name, confidence * 100.0f, elapsed_ms);
                        ESP_LOGI(TAG, "✨ [CỬ CHỈ] %s (Conf: %.1f%%, Time: %.3f ms)",
                                 spell_name, confidence * 100.0f, elapsed_ms);

                        // Lấy màu RGB đã cấu hình cho phép thuật này
                        uint8_t r = 255, g = 255, b = 255;
                        classic_get_class_rgb(pred_class, &r, &g, &b);
                        set_rgb_color(r, g, b);
                        vTaskDelay(pdMS_TO_TICKS(220));
                        set_rgb_color(0, 0, 0);

                        // Kích hoạt cooldown tránh spam liên tiếp trên cùng một cử chỉ
                        s_cooldown_counter = COOLDOWN_SAMPLES;
                    }
                }
            }
        }

        vTaskDelayUntil(&last_wake_time, pdMS_TO_TICKS(SAMPLING_PERIOD_MS));
    }
}

extern "C" void app_main(void) {
    ESP_LOGI(TAG, "=== STEM SPELLBOOK CLASSIC ML RUNTIME ===");
    xTaskCreatePinnedToCore(classic_ml_task, "classic_ml_task", 8192, NULL, 5, NULL, 1);
}
