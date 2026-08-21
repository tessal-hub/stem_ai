#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cmath>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/ledc.h"
#include "esp_task_wdt.h"          // <-- Watchdog

#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "nvs_flash.h"
#include "nvs.h"
#include "esp_partition.h"
#include "spi_flash_mmap.h"

// (Không dùng std::vector, std::string nữa)

static const char* TAG = "SPELLBOOK";

namespace spellbook {

// ========== Cấu hình phần cứng & hệ thống ==========
#if CONFIG_IDF_TARGET_ESP32S3
#ifndef STEM_I2C_PORT
#define STEM_I2C_PORT I2C_NUM_0
#endif
#ifndef STEM_I2C_SDA_PIN
#define STEM_I2C_SDA_PIN GPIO_NUM_8
#endif
#ifndef STEM_I2C_SCL_PIN
#define STEM_I2C_SCL_PIN GPIO_NUM_9
#endif
#ifndef STEM_RGB_R_PIN
#define STEM_RGB_R_PIN GPIO_NUM_4
#endif
#ifndef STEM_RGB_G_PIN
#define STEM_RGB_G_PIN GPIO_NUM_5
#endif
#ifndef STEM_RGB_B_PIN
#define STEM_RGB_B_PIN GPIO_NUM_6
#endif
#else
#ifndef STEM_I2C_PORT
#define STEM_I2C_PORT I2C_NUM_0
#endif
#ifndef STEM_I2C_SDA_PIN
#define STEM_I2C_SDA_PIN GPIO_NUM_21
#endif
#ifndef STEM_I2C_SCL_PIN
#define STEM_I2C_SCL_PIN GPIO_NUM_22
#endif
#ifndef STEM_RGB_R_PIN
#define STEM_RGB_R_PIN GPIO_NUM_25
#endif
#ifndef STEM_RGB_G_PIN
#define STEM_RGB_G_PIN GPIO_NUM_26
#endif
#ifndef STEM_RGB_B_PIN
#define STEM_RGB_B_PIN GPIO_NUM_27
#endif
#endif
#define STEM_RGB_LEDC_MODE LEDC_LOW_SPEED_MODE
#define STEM_RGB_LEDC_TIMER LEDC_TIMER_0
#define STEM_RGB_LEDC_DUTY_RES LEDC_TIMER_8_BIT
#define STEM_RGB_LEDC_FREQ 5000
#define STEM_RGB_CHANNEL_R LEDC_CHANNEL_0
#define STEM_RGB_CHANNEL_G LEDC_CHANNEL_1
#define STEM_RGB_CHANNEL_B LEDC_CHANNEL_2
#ifndef STEM_RGB_TIMEOUT_MS
#define STEM_RGB_TIMEOUT_MS 5000
#endif
#ifndef STEM_I2C_FREQ_HZ
#define STEM_I2C_FREQ_HZ 400000
#endif
#ifndef STEM_TFLM_ARENA_BYTES
#define STEM_TFLM_ARENA_BYTES (96 * 1024)
#endif
#ifndef STEM_SAMPLING_INTERVAL_MS
#define STEM_SAMPLING_INTERVAL_MS 20
#endif
#ifndef STEM_INFERENCE_INTERVAL_MS
#define STEM_INFERENCE_INTERVAL_MS STEM_SAMPLING_INTERVAL_MS
#endif
#ifndef STEM_INFERENCE_POLL_MS
#define STEM_INFERENCE_POLL_MS 2
#endif
#ifndef STEM_DEBUG_VERBOSE
#define STEM_DEBUG_VERBOSE 0
#endif
#ifndef STEM_SAMPLING_TASK_CORE
#define STEM_SAMPLING_TASK_CORE 1
#endif
#ifndef STEM_INFERENCE_TASK_CORE
#define STEM_INFERENCE_TASK_CORE 0
#endif
#ifndef STEM_INFERENCE_STACK_SIZE
#define STEM_INFERENCE_STACK_SIZE 16384   // 16 KB cho TFLM
#endif
#ifndef MAX_GESTURES
#define MAX_GESTURES 50
#endif

// ---------- Watchdog ----------
#ifndef STEM_WDT_TIMEOUT_SEC
#define STEM_WDT_TIMEOUT_SEC 5
#endif

// ---------- IMU ----------
#define MPU6050_ADDR 0x68
#define WINDOW_SIZE 64
#define CHANNELS 6
#define ACCEL_SCALE 16384.0f
#define GYRO_RAW_SCALE 131.0f
#define GYRO_SCALE (131.0f * 125.0f)  // 131 LSB/(°/s) × 125 rescale → matches Python pipeline
#define BUFFER_LENGTH (WINDOW_SIZE * CHANNELS)   // 384 phần tử
#define EMBEDDING_DIM 16

// ========== Cấu trúc dữ liệu (sửa đổi) ==========
struct PreloadedSpell {
    char name[32];
    float centroid[EMBEDDING_DIM];
    bool is_spell;
    float threshold;
    uint8_t r;
    uint8_t g;
    uint8_t b;
};

static PreloadedSpell g_preloaded_spells[MAX_GESTURES];
static int g_preloaded_spell_count = 0;

#ifndef STEM_RGB_ACTIVE_LOW
#define STEM_RGB_ACTIVE_LOW 0
#endif

static void SetRgbColor(uint8_t r, uint8_t g, uint8_t b) {
#if STEM_RGB_ACTIVE_LOW
    r = 255 - r;
    g = 255 - g;
    b = 255 - b;
#endif
    ledc_set_duty(STEM_RGB_LEDC_MODE, STEM_RGB_CHANNEL_R, r);
    ledc_update_duty(STEM_RGB_LEDC_MODE, STEM_RGB_CHANNEL_R);
    ledc_set_duty(STEM_RGB_LEDC_MODE, STEM_RGB_CHANNEL_G, g);
    ledc_update_duty(STEM_RGB_LEDC_MODE, STEM_RGB_CHANNEL_G);
    ledc_set_duty(STEM_RGB_LEDC_MODE, STEM_RGB_CHANNEL_B, b);
    ledc_update_duty(STEM_RGB_LEDC_MODE, STEM_RGB_CHANNEL_B);
}

static esp_timer_handle_t s_rgb_off_timer = nullptr;

static void RgbOffTimerCallback(void* /*arg*/) {
    SetRgbColor(0, 0, 0);
}

static bool InitRgbLed() {
    ledc_timer_config_t ledc_timer = {};
    ledc_timer.speed_mode       = STEM_RGB_LEDC_MODE;
    ledc_timer.duty_resolution  = STEM_RGB_LEDC_DUTY_RES;
    ledc_timer.timer_num        = STEM_RGB_LEDC_TIMER;
    ledc_timer.freq_hz          = STEM_RGB_LEDC_FREQ;
    ledc_timer.clk_cfg          = LEDC_AUTO_CLK;
    if (ledc_timer_config(&ledc_timer) != ESP_OK) return false;

    ledc_channel_config_t ledc_r = {};
    ledc_r.gpio_num       = STEM_RGB_R_PIN;
    ledc_r.speed_mode     = STEM_RGB_LEDC_MODE;
    ledc_r.channel        = STEM_RGB_CHANNEL_R;
    ledc_r.timer_sel      = STEM_RGB_LEDC_TIMER;
    ledc_r.duty           = 0;
    ledc_r.hpoint         = 0;
    ledc_channel_config(&ledc_r);

    ledc_channel_config_t ledc_g = {};
    ledc_g.gpio_num       = STEM_RGB_G_PIN;
    ledc_g.speed_mode     = STEM_RGB_LEDC_MODE;
    ledc_g.channel        = STEM_RGB_CHANNEL_G;
    ledc_g.timer_sel      = STEM_RGB_LEDC_TIMER;
    ledc_g.duty           = 0;
    ledc_g.hpoint         = 0;
    ledc_channel_config(&ledc_g);

    ledc_channel_config_t ledc_b = {};
    ledc_b.gpio_num       = STEM_RGB_B_PIN;
    ledc_b.speed_mode     = STEM_RGB_LEDC_MODE;
    ledc_b.channel        = STEM_RGB_CHANNEL_B;
    ledc_b.timer_sel      = STEM_RGB_LEDC_TIMER;
    ledc_b.duty           = 0;
    ledc_b.hpoint         = 0;
    ledc_channel_config(&ledc_b);

    const esp_timer_create_args_t timer_args = {
        .callback = &RgbOffTimerCallback,
        .arg = nullptr,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "rgb_off_timer",
        .skip_unhandled_events = false
    };
    esp_timer_create(&timer_args, &s_rgb_off_timer);

    // Boot-up flash test (300ms trắng rồi tắt)
    SetRgbColor(80, 80, 80);
    vTaskDelay(pdMS_TO_TICKS(250));
    SetRgbColor(0, 0, 0);
    return true;
}

static const void* g_model_ptr = nullptr;
static spi_flash_mmap_handle_t g_model_map_handle;

alignas(16) static std::uint8_t g_tensor_arena[STEM_TFLM_ARENA_BYTES];
static i2c_master_dev_handle_t s_mpu_handle = nullptr;

// ---------- Buffer dùng chung (int16_t) ----------
static SemaphoreHandle_t s_buffer_mutex = nullptr;
static int16_t s_shared_buffer[BUFFER_LENGTH] = {0};   // <-- int16_t
static uint32_t s_shared_sample_count = 0;
static uint32_t s_shared_version = 0;

static tflite::MicroInterpreter* s_interpreter = nullptr;
static TfLiteTensor* s_input = nullptr;
static TfLiteTensor* s_output = nullptr;
static tflite::MicroMutableOpResolver<20> s_resolver;

// Khung dữ liệu thô từ IMU
struct ImuRawFrame {
    int16_t ax, ay, az;
    int16_t gx, gy, gz;
};

// ========== Khởi tạo phần cứng (giữ nguyên ngoại trừ ReadImu) ==========
static bool InitI2cBus() {
    i2c_master_bus_config_t bus_cfg = {};
    bus_cfg.i2c_port = STEM_I2C_PORT;
    bus_cfg.sda_io_num = STEM_I2C_SDA_PIN;
    bus_cfg.scl_io_num = STEM_I2C_SCL_PIN;
    bus_cfg.clk_source = I2C_CLK_SRC_DEFAULT;
    bus_cfg.glitch_ignore_cnt = 7;
    bus_cfg.flags.enable_internal_pullup = true;

    i2c_master_bus_handle_t bus_handle;
    if (i2c_new_master_bus(&bus_cfg, &bus_handle) != ESP_OK) {
        ESP_LOGE(TAG, "I2C bus init failed");
        return false;
    }

    i2c_device_config_t dev_cfg = {};
    dev_cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    dev_cfg.device_address = MPU6050_ADDR;
    dev_cfg.scl_speed_hz = STEM_I2C_FREQ_HZ;
    if (i2c_master_bus_add_device(bus_handle, &dev_cfg, &s_mpu_handle) != ESP_OK) {
        ESP_LOGE(TAG, "MPU6050 add device failed");
        return false;
    }

    ESP_LOGI(TAG, "I2C bus ready (SDA=%d, SCL=%d, %dHz)",
             STEM_I2C_SDA_PIN, STEM_I2C_SCL_PIN, STEM_I2C_FREQ_HZ);
    return true;
}

static bool InitMpu6050() {
    uint8_t wake[] = {0x6B, 0x00};
    if (i2c_master_transmit(s_mpu_handle, wake, sizeof(wake), -1) != ESP_OK) {
        ESP_LOGE(TAG, "MPU6050 wake failed");
        return false;
    }
    uint8_t dlpf[] = {0x1A, 0x04};
    if (i2c_master_transmit(s_mpu_handle, dlpf, sizeof(dlpf), -1) != ESP_OK) {
        ESP_LOGE(TAG, "MPU6050 DLPF config failed");
        return false;
    }
    uint8_t accel_cfg[] = {0x1C, 0x00};
    if (i2c_master_transmit(s_mpu_handle, accel_cfg, sizeof(accel_cfg), -1) != ESP_OK) {
        ESP_LOGE(TAG, "MPU6050 accel config failed");
        return false;
    }
    uint8_t gyro_cfg[] = {0x1B, 0x00};
    if (i2c_master_transmit(s_mpu_handle, gyro_cfg, sizeof(gyro_cfg), -1) != ESP_OK) {
        ESP_LOGE(TAG, "MPU6050 gyro config failed");
        return false;
    }
    ESP_LOGI(TAG, "MPU6050 ready");
    return true;
}

static bool InitInference() {
    tflite::InitializeTarget();

    const esp_partition_t* model_part = esp_partition_find_first(
        ESP_PARTITION_TYPE_DATA, (esp_partition_subtype_t)0x40, "model");
    if (!model_part) {
        ESP_LOGE(TAG, "Model partition not found!");
        return false;
    }
    esp_err_t err = esp_partition_mmap(model_part, 0, model_part->size,
                                       ESP_PARTITION_MMAP_DATA, &g_model_ptr, &g_model_map_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to mmap model partition");
        return false;
    }

    const tflite::Model* model = tflite::GetModel(g_model_ptr);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        ESP_LOGE(TAG, "Model schema mismatch (%lu vs %d)",
                 static_cast<unsigned long>(model->version()), TFLITE_SCHEMA_VERSION);
        return false;
    }

    s_resolver.AddConv2D();
    s_resolver.AddDepthwiseConv2D();
    s_resolver.AddMaxPool2D();
    s_resolver.AddReshape();
    s_resolver.AddFullyConnected();
    s_resolver.AddExpandDims();
    s_resolver.AddSoftmax();
    s_resolver.AddShape();
    s_resolver.AddStridedSlice();
    s_resolver.AddPack();
    s_resolver.AddMul();
    s_resolver.AddAdd();
    s_resolver.AddQuantize();
    s_resolver.AddConcatenation();
    s_resolver.AddMean();
    s_resolver.AddL2Normalization();

    static tflite::MicroInterpreter interpreter(
        model, s_resolver, g_tensor_arena, STEM_TFLM_ARENA_BYTES);
    s_interpreter = &interpreter;

    if (s_interpreter->AllocateTensors() != kTfLiteOk) {
        ESP_LOGE(TAG, "AllocateTensors failed, increase STEM_TFLM_ARENA_BYTES");
        return false;
    }

    s_input = s_interpreter->input(0);
    s_output = s_interpreter->output(0);

    int out_dim = s_output->dims->data[s_output->dims->size - 1];
    if (out_dim != EMBEDDING_DIM) {
        ESP_LOGE(TAG, "Model output dim mismatch: got %d, expected %d",
                 out_dim, EMBEDDING_DIM);
        return false;
    }

    ESP_LOGI(TAG, "TFLM ready, arena used: %d / %d",
             static_cast<int>(s_interpreter->arena_used_bytes()),
             STEM_TFLM_ARENA_BYTES);
    return true;
}

// Đọc dữ liệu thô từ IMU (int16_t)
static bool ReadImuRaw(ImuRawFrame* out) {
    if (!out) return false;
    uint8_t reg = 0x3B;
    uint8_t data[14];
    if (i2c_master_transmit_receive(s_mpu_handle, &reg, 1, data, 14, -1) != ESP_OK) {
        return false;
    }
    // MPU6050 trả về big-endian
    out->ax = static_cast<int16_t>((data[0] << 8) | data[1]);
    out->ay = static_cast<int16_t>((data[2] << 8) | data[3]);
    out->az = static_cast<int16_t>((data[4] << 8) | data[5]);
    // Bỏ qua temp (data[6..7])
    out->gx = static_cast<int16_t>((data[8] << 8)  | data[9]);
    out->gy = static_cast<int16_t>((data[10] << 8) | data[11]);
    out->gz = static_cast<int16_t>((data[12] << 8) | data[13]);
    return true;
}

const char* SpellNameFromClassIndex(int class_index) {
    if (class_index < 0 || class_index >= g_preloaded_spell_count)
        return "UNKNOWN";
    return g_preloaded_spells[class_index].name;
}

// ========== Tác vụ ==========
static void SamplingTask(void* /*arg*/) {
    // Đăng ký watchdog
    esp_task_wdt_add(NULL);
    TickType_t last_wake = xTaskGetTickCount();
    const TickType_t period_ticks = pdMS_TO_TICKS(STEM_SAMPLING_INTERVAL_MS);
    int consecutive_failures = 0;

    while (true) {
        // Reset watchdog mỗi vòng lặp
        esp_task_wdt_reset();

        ImuRawFrame raw;
        if (ReadImuRaw(&raw)) {
            consecutive_failures = 0;
            if (xSemaphoreTake(s_buffer_mutex, portMAX_DELAY) == pdTRUE) {
                // Dịch chuyển buffer trượt (6 kênh int16)
                memmove(s_shared_buffer, s_shared_buffer + CHANNELS,
                        (BUFFER_LENGTH - CHANNELS) * sizeof(int16_t));
                // Ghi mẫu mới vào cuối buffer
                s_shared_buffer[BUFFER_LENGTH - 6] = raw.ax;
                s_shared_buffer[BUFFER_LENGTH - 5] = raw.ay;
                s_shared_buffer[BUFFER_LENGTH - 4] = raw.az;
                s_shared_buffer[BUFFER_LENGTH - 3] = raw.gx;
                s_shared_buffer[BUFFER_LENGTH - 2] = raw.gy;
                s_shared_buffer[BUFFER_LENGTH - 1] = raw.gz;
                s_shared_sample_count++;
                s_shared_version++;
                xSemaphoreGive(s_buffer_mutex);
            }
        } else {
            consecutive_failures++;
            if (consecutive_failures >= 10) {
                ESP_LOGW(TAG, "IMU read failed 10 times consecutively. Attempting MPU6050 re-init...");
                InitMpu6050();
                consecutive_failures = 0;
            }
        }
        vTaskDelayUntil(&last_wake, period_ticks);
    }
    esp_task_wdt_delete(NULL); // không bao giờ chạy tới
}

// Inference task
static bool s_is_moving = false;
static float s_best_spell_prob = 0.0f;
static int s_best_spell_class = -1;
static float s_best_primitive_prob = 0.0f;
static int s_best_primitive_class = -1;
static int s_recent_classes[3] = {-1, -1, -1};
static int s_recent_idx = 0;
static int s_accepted_count_this_gesture = 0;

// Buffer cục bộ dạng int16_t
static int16_t s_local_buffer[BUFFER_LENGTH] = {0};

__attribute__((weak)) void OnSpellDetected(int class_index) {
    if (class_index >= 0 && class_index < g_preloaded_spell_count) {
        const auto& spell = g_preloaded_spells[class_index];
        SetRgbColor(spell.r, spell.g, spell.b);
        if (s_rgb_off_timer != nullptr) {
            esp_timer_stop(s_rgb_off_timer);
            esp_timer_start_once(s_rgb_off_timer, (uint64_t)STEM_RGB_TIMEOUT_MS * 1000ULL);
        }
    } else {
        SetRgbColor(0, 0, 0);
        if (s_rgb_off_timer != nullptr) {
            esp_timer_stop(s_rgb_off_timer);
        }
    }
}

static void InferenceTask(void* /*arg*/) {
    // Đăng ký watchdog cho task này
    esp_task_wdt_add(NULL);

    uint32_t last_seen_version = 0;
#if STEM_DEBUG_VERBOSE
    int64_t invoke_us_max = 0;
#endif

    while (true) {
        // Reset watchdog
        esp_task_wdt_reset();

        vTaskDelay(1);  // tránh đói idle

        uint32_t sample_count_snapshot = 0;
        uint32_t version_snapshot = 0;

        if (xSemaphoreTake(s_buffer_mutex, portMAX_DELAY) == pdTRUE) {
            memcpy(s_local_buffer, s_shared_buffer, sizeof(s_local_buffer));
            sample_count_snapshot = s_shared_sample_count;
            version_snapshot = s_shared_version;
            xSemaphoreGive(s_buffer_mutex);
        }

        if (version_snapshot == last_seen_version) {
            vTaskDelay(pdMS_TO_TICKS(STEM_INFERENCE_POLL_MS));
            continue;
        }
        last_seen_version = version_snapshot;

        if (sample_count_snapshot < WINDOW_SIZE) {
            vTaskDelay(pdMS_TO_TICKS(STEM_INFERENCE_POLL_MS));
            continue;
        }

        // ----- Phát hiện chuyển động bằng tail variance (TAIL_LEN = 25 ~ 500ms) -----
        const int TAIL_LEN = 25;
        int start_idx = WINDOW_SIZE - TAIL_LEN;
        float sum_ax = 0, sum_ay = 0, sum_az = 0, sum_gx = 0, sum_gy = 0, sum_gz = 0;
        for (int i = start_idx; i < WINDOW_SIZE; ++i) {
            float ax = s_local_buffer[i * CHANNELS + 0] / ACCEL_SCALE;
            float ay = s_local_buffer[i * CHANNELS + 1] / ACCEL_SCALE;
            float az = s_local_buffer[i * CHANNELS + 2] / ACCEL_SCALE;
            float gx = s_local_buffer[i * CHANNELS + 3] / GYRO_RAW_SCALE;
            float gy = s_local_buffer[i * CHANNELS + 4] / GYRO_RAW_SCALE;
            float gz = s_local_buffer[i * CHANNELS + 5] / GYRO_RAW_SCALE;
            sum_ax += ax; sum_ay += ay; sum_az += az;
            sum_gx += gx; sum_gy += gy; sum_gz += gz;
        }
        float mean_ax = sum_ax / TAIL_LEN, mean_ay = sum_ay / TAIL_LEN, mean_az = sum_az / TAIL_LEN;
        float mean_gx = sum_gx / TAIL_LEN, mean_gy = sum_gy / TAIL_LEN, mean_gz = sum_gz / TAIL_LEN;

        float var_accel = 0, var_gyro = 0;
        for (int i = start_idx; i < WINDOW_SIZE; ++i) {
            float ax = s_local_buffer[i * CHANNELS + 0] / ACCEL_SCALE;
            float ay = s_local_buffer[i * CHANNELS + 1] / ACCEL_SCALE;
            float az = s_local_buffer[i * CHANNELS + 2] / ACCEL_SCALE;
            float gx = s_local_buffer[i * CHANNELS + 3] / GYRO_RAW_SCALE;
            float gy = s_local_buffer[i * CHANNELS + 4] / GYRO_RAW_SCALE;
            float gz = s_local_buffer[i * CHANNELS + 5] / GYRO_RAW_SCALE;
            float dx = ax - mean_ax, dy = ay - mean_ay, dz = az - mean_az;
            var_accel += (dx*dx + dy*dy + dz*dz);
            float dgx = gx - mean_gx, dgy = gy - mean_gy, dgz = gz - mean_gz;
            var_gyro += (dgx*dgx + dgy*dgy + dgz*dgz);
        }
        var_accel /= TAIL_LEN;
        var_gyro /= TAIL_LEN;
        float motion_energy = var_accel + (var_gyro / 10000.0f);

        // Motion State Machine
        if (s_is_moving) {
            if (motion_energy < 0.02f) {
                s_is_moving = false;
                int predicted_class = -1;
                if (s_best_spell_class >= 0) {
                    // Temporal agreement check: adaptive quorum based on total accepted windows this gesture
                    int match_count = 0;
                    for (int r = 0; r < 3; ++r) {
                        if (s_recent_classes[r] == s_best_spell_class) {
                            match_count++;
                        }
                    }
                    int quorum_votes = (s_accepted_count_this_gesture < 3) ? 1 : 2;
                    if (match_count >= quorum_votes) {
                        printf("FINAL PREDICT:%s:%.2f\n", SpellNameFromClassIndex(s_best_spell_class), s_best_spell_prob);
                        predicted_class = s_best_spell_class;
                    } else {
#if STEM_DEBUG_VERBOSE
                        ESP_LOGW(TAG, "Spell %s rejected by temporal agreement (%d/%d required)",
                                 SpellNameFromClassIndex(s_best_spell_class), match_count, quorum_votes);
#endif
                    }
                } else if (s_best_primitive_class >= 0) {
#if STEM_DEBUG_VERBOSE
                    printf("DEBUG_BLACKHOLE:%s (prob: %.2f)\n", SpellNameFromClassIndex(s_best_primitive_class), s_best_primitive_prob);
#endif
                }
                // Reset
                s_best_spell_prob = 0.0f; s_best_spell_class = -1;
                s_best_primitive_prob = 0.0f; s_best_primitive_class = -1;
                for (int r = 0; r < 3; ++r) s_recent_classes[r] = -1;
                s_recent_idx = 0;
                s_accepted_count_this_gesture = 0;

                // Giữ lại frame cuối trong buffer để tránh glitch
                if (xSemaphoreTake(s_buffer_mutex, portMAX_DELAY) == pdTRUE) {
                    int16_t last_ax = s_local_buffer[BUFFER_LENGTH - 6];
                    int16_t last_ay = s_local_buffer[BUFFER_LENGTH - 5];
                    int16_t last_az = s_local_buffer[BUFFER_LENGTH - 4];
                    int16_t last_gx = s_local_buffer[BUFFER_LENGTH - 3];
                    int16_t last_gy = s_local_buffer[BUFFER_LENGTH - 2];
                    int16_t last_gz = s_local_buffer[BUFFER_LENGTH - 1];
                    for (int i = 0; i < WINDOW_SIZE; ++i) {
                        s_shared_buffer[i * CHANNELS + 0] = last_ax;
                        s_shared_buffer[i * CHANNELS + 1] = last_ay;
                        s_shared_buffer[i * CHANNELS + 2] = last_az;
                        s_shared_buffer[i * CHANNELS + 3] = last_gx;
                        s_shared_buffer[i * CHANNELS + 4] = last_gy;
                        s_shared_buffer[i * CHANNELS + 5] = last_gz;
                    }
                    s_shared_version++;
                    xSemaphoreGive(s_buffer_mutex);
                }
                if (predicted_class != -1) OnSpellDetected(predicted_class);
                continue;
            }
        } else {
            if (motion_energy > 0.10f) {
                s_is_moving = true;
            } else {
                continue;
            }
        }

        // ---------- Chuẩn bị input cho TFLM (từ int16_t -> float -> clip[-2, 2] -> int8) ----------
        int model_frames = s_input->dims->data[1];
        int model_channels = s_input->dims->data[2];
        if (model_channels != 6 && model_channels != 9) {
            ESP_LOGE(TAG, "Unsupported input channels: %d", model_channels);
            vTaskDelay(pdMS_TO_TICKS(STEM_INFERENCE_POLL_MS));
            continue;
        }

        const float in_scale = s_input->params.scale;
        const float inv_scale = 1.0f / in_scale;
        const int in_zp = s_input->params.zero_point;
        int start_offset = BUFFER_LENGTH - (model_frames * 6);
        if (start_offset < 0) start_offset = 0;

        for (int f = 0; f < model_frames; ++f) {
            int idx = start_offset + f * 6;
            // Chuyển raw -> float
            float ax = s_local_buffer[idx]     / ACCEL_SCALE;
            float ay = s_local_buffer[idx + 1] / ACCEL_SCALE;
            float az = s_local_buffer[idx + 2] / ACCEL_SCALE;
            float gx = s_local_buffer[idx + 3] / GYRO_SCALE;
            float gy = s_local_buffer[idx + 4] / GYRO_SCALE;
            float gz = s_local_buffer[idx + 5] / GYRO_SCALE;

            if (model_channels == 9) {
                float derived0 = az * gx;
                float derived1 = az * gy;
                float jerkz = (idx >= 6) ? (az - (s_local_buffer[idx - 6 + 2] / ACCEL_SCALE)) : 0.0f;
                float in_vals[9] = {ax, ay, az, gx, gy, gz, derived0, derived1, jerkz};
                for (int c = 0; c < 9; c++) {
                    float v_clipped = in_vals[c] > 2.0f ? 2.0f : (in_vals[c] < -2.0f ? -2.0f : in_vals[c]);
                    int val = static_cast<int>(std::roundf(v_clipped * inv_scale)) + in_zp;
                    val = val > 127 ? 127 : (val < -128 ? -128 : val);
                    s_input->data.int8[f * 9 + c] = static_cast<int8_t>(val);
                }
            } else { // 6 kênh
                float in_vals[6] = {ax, ay, az, gx, gy, gz};
                for (int c = 0; c < 6; c++) {
                    float v_clipped = in_vals[c] > 2.0f ? 2.0f : (in_vals[c] < -2.0f ? -2.0f : in_vals[c]);
                    int val = static_cast<int>(std::roundf(v_clipped * inv_scale)) + in_zp;
                    val = val > 127 ? 127 : (val < -128 ? -128 : val);
                    s_input->data.int8[f * 6 + c] = static_cast<int8_t>(val);
                }
            }
        }

#if STEM_DEBUG_VERBOSE
        int64_t t_invoke_start = esp_timer_get_time();
#endif
        if (s_interpreter->Invoke() != kTfLiteOk) {
            ESP_LOGE(TAG, "Invoke failed");
            continue;
        }
#if STEM_DEBUG_VERBOSE
        int64_t invoke_us = esp_timer_get_time() - t_invoke_start;
        if (invoke_us > invoke_us_max) invoke_us_max = invoke_us;
        {
            static int invoke_dbg_counter = 0;
            if (++invoke_dbg_counter >= 10) {
                invoke_dbg_counter = 0;
                ESP_LOGI(TAG, "DEBUG_TIMING invoke_us=%lld invoke_us_max=%lld", (long long)invoke_us, (long long)invoke_us_max);
            }
        }
#endif

        // Đọc embedding & tính L2-norm
        const float out_scale = s_output->params.scale;
        const int out_zp = s_output->params.zero_point;
        float current_embedding[EMBEDDING_DIM];
        for (int i = 0; i < EMBEDDING_DIM; ++i)
            current_embedding[i] = (s_output->data.int8[i] - out_zp) * out_scale;

        float v_out[EMBEDDING_DIM];
        float norm_curr = 0.0f;
        for (int i = 0; i < EMBEDDING_DIM; ++i) {
            v_out[i] = current_embedding[i];
            norm_curr += v_out[i] * v_out[i];
        }
        float inv_norm = 1.0f / (std::sqrt(norm_curr) + 1e-6f);
        for (int i = 0; i < EMBEDDING_DIM; ++i) v_out[i] *= inv_norm;

        // Cosine similarity matching (tìm best match theo cosine distance)
        float max_cos = -1.0f;
        int max_idx = -1;
        for (int i = 0; i < g_preloaded_spell_count; ++i) {
            float cos_sim = 0.0f;
            for (int j = 0; j < EMBEDDING_DIM; ++j)
                cos_sim += v_out[j] * g_preloaded_spells[i].centroid[j];
            if (cos_sim > max_cos) {
                max_cos = cos_sim;
                max_idx = i;
            }
        }

        // Cập nhật candidate tốt nhất theo Cosine Confidence
        if (max_idx >= 0 && max_cos >= g_preloaded_spells[max_idx].threshold) {
            // Track accepted window class and count for adaptive temporal agreement
            s_recent_classes[s_recent_idx % 3] = max_idx;
            s_recent_idx++;
            s_accepted_count_this_gesture++;

            bool is_spell = g_preloaded_spells[max_idx].is_spell;
            if (is_spell) {
                if (max_cos > s_best_spell_prob) {
                    s_best_spell_prob = max_cos;
                    s_best_spell_class = max_idx;
                }
            } else {
                if (max_cos > s_best_primitive_prob) {
                    s_best_primitive_prob = max_cos;
                    s_best_primitive_class = max_idx;
                }
            }
#if STEM_DEBUG_VERBOSE
        } else if (max_idx >= 0) {
            static int miss_dbg_counter = 0;
            if (++miss_dbg_counter >= 5) {
                miss_dbg_counter = 0;
                ESP_LOGI(TAG, "DEBUG_MISS:%s cos=%.3f threshold=%.3f",
                         g_preloaded_spells[max_idx].name, max_cos, g_preloaded_spells[max_idx].threshold);
            }
#endif
        }
    }
    esp_task_wdt_delete(NULL);
}

// ========== Khởi tạo runtime (giữ nguyên việc đọc NVS, thêm init watchdog) ==========
bool InitializeSpellRuntime() {
    // Khởi tạo NVS partition labels
    esp_err_t err = nvs_flash_init_partition("labels");
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "nvs_flash_init_partition 'labels' returned %s (0x%x). Erasing and re-initializing...", esp_err_to_name(err), err);
        nvs_flash_erase_partition("labels");
        err = nvs_flash_init_partition("labels");
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to init labels NVS partition: %s", esp_err_to_name(err));
        return false;
    }

    nvs_handle_t h;
    err = nvs_open_from_partition("labels", "cfg", NVS_READONLY, &h);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace 'cfg': %s", esp_err_to_name(err));
        return false;
    }

    uint8_t count = 0;
    err = nvs_get_u8(h, "count", &count);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read count from NVS: %s", esp_err_to_name(err));
        nvs_close(h);
        return false;
    }
    if (count == 0 || count > MAX_GESTURES) {
        ESP_LOGE(TAG, "Invalid gesture count: %d (max %d)", count, MAX_GESTURES);
        nvs_close(h);
        return false;
    }

    g_preloaded_spell_count = 0;
    for (int i = 0; i < count; i++) {
        PreloadedSpell spell;
        memset(&spell, 0, sizeof(spell));

        char name_key[16]; snprintf(name_key, sizeof(name_key), "g%d", i);
        char name_buf[32] = {0}; size_t name_len = sizeof(name_buf);
        err = nvs_get_str(h, name_key, name_buf, &name_len);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Failed to read name for g%d", i);
            snprintf(name_buf, sizeof(name_buf), "unknown_%d", i);
        }
        name_buf[sizeof(name_buf)-1] = '\0';
        strncpy(spell.name, name_buf, sizeof(spell.name) - 1);
        spell.name[sizeof(spell.name)-1] = '\0';

        char cen_key[16]; snprintf(cen_key, sizeof(cen_key), "g%d_cen", i);
        size_t blob_size = 0;
        err = nvs_get_blob(h, cen_key, NULL, &blob_size);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Failed to query blob for g%d_cen", i);
            continue;
        }
        size_t v1_size = EMBEDDING_DIM * sizeof(float) + sizeof(float) + sizeof(uint8_t);
        size_t v2_size = v1_size + 3 * sizeof(uint8_t);
        if (blob_size == v2_size || blob_size == v1_size) {
            uint8_t blob[128]; // đủ lớn
            if (blob_size > sizeof(blob)) continue;
            err = nvs_get_blob(h, cen_key, blob, &blob_size);
            if (err != ESP_OK) continue;

            memcpy(spell.centroid, blob, EMBEDDING_DIM * sizeof(float));
            // Chuẩn hóa centroid nếu cần
            float norm = 0.0f;
            for (int j = 0; j < EMBEDDING_DIM; ++j) norm += spell.centroid[j] * spell.centroid[j];
            norm = std::sqrt(norm);
            if (norm > 1e-6f && std::abs(norm - 1.0f) > 1e-4f) {
                float inv_norm = 1.0f / norm;
                for (int j = 0; j < EMBEDDING_DIM; ++j) spell.centroid[j] *= inv_norm;
                ESP_LOGI(TAG, "Normalized centroid %d", i);
            }
            memcpy(&spell.threshold, blob + EMBEDDING_DIM * sizeof(float), sizeof(float));
            spell.is_spell = blob[EMBEDDING_DIM * sizeof(float) + sizeof(float)] != 0;

            if (blob_size == v2_size) {
                spell.r = blob[v1_size];
                spell.g = blob[v1_size + 1];
                spell.b = blob[v1_size + 2];
            } else {
                spell.r = 255;
                spell.g = 255;
                spell.b = 255;
            }

            if (g_preloaded_spell_count < MAX_GESTURES) {
                g_preloaded_spells[g_preloaded_spell_count] = spell;
                g_preloaded_spell_count++;
            }
        } else {
            ESP_LOGE(TAG, "Invalid blob size for gesture %d (size: %u)", i, (unsigned)blob_size);
        }
    }
    nvs_close(h);
    ESP_LOGI(TAG, "Loaded %d gestures", g_preloaded_spell_count);
    if (g_preloaded_spell_count == 0) {
        ESP_LOGE(TAG, "0 gestures parsed successfully");
        return false;
    }

    InitRgbLed();

    if (!InitI2cBus() || !InitMpu6050() || !InitInference()) {
        return false;
    }

    s_buffer_mutex = xSemaphoreCreateMutex();
    if (s_buffer_mutex == nullptr) {
        ESP_LOGE(TAG, "Failed to create buffer mutex");
        return false;
    }

    // Tạo task
    xTaskCreatePinnedToCore(SamplingTask, "imu_sampling", 4096, nullptr,
                             configMAX_PRIORITIES - 2, nullptr,
                             STEM_SAMPLING_TASK_CORE);
    xTaskCreatePinnedToCore(InferenceTask, "gesture_inference", STEM_INFERENCE_STACK_SIZE, nullptr,
                             configMAX_PRIORITIES - 4, nullptr,
                             STEM_INFERENCE_TASK_CORE);
    return true;
}

}  // namespace spellbook

extern "C" void app_main(void) {
    // Khởi tạo Task Watchdog toàn cục
    esp_task_wdt_config_t wdt_cfg = {
        .timeout_ms      = STEM_WDT_TIMEOUT_SEC * 1000,
        .idle_core_mask  = 0,               // <-- second
        .trigger_panic   = true,            // <-- third
    };
    esp_task_wdt_init(&wdt_cfg);

    if (!spellbook::InitializeSpellRuntime()) {
        ESP_LOGE("MAIN", "Runtime initialization failed - halting");
        while (true) { vTaskDelay(pdMS_TO_TICKS(1000)); }
    }
    ESP_LOGI("MAIN", "Sampling + inference tasks started (decoupled, WDT active, int16 buffers)");
}