#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/i2c_master.h"

// TFLite Micro Headers
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

// File model của bạn (Sinh ra từ Python)
#include "gesture_model.cc"

static const char* TAG = "STEM_AI_BASIC";

// --- CẤU HÌNH ---
#define STEM_I2C_PORT I2C_NUM_0
#define STEM_I2C_SDA_PIN GPIO_NUM_8
#define STEM_I2C_SCL_PIN GPIO_NUM_9
#define STEM_I2C_FREQ_HZ 400000

#define STEM_TFLM_ARENA_BYTES (80 * 1024)
#define MPU6050_ADDR 0x68

#define WINDOW_SIZE 40
#define CHANNELS 6
#define BUFFER_LENGTH (WINDOW_SIZE * CHANNELS)
#define IMU_SCALE 32768.0f 

// --- ĐỊNH NGHĨA CLASSES ---
enum class SpellId {
  STAND_BY, // Index 0
  CIRCLE,   // Index 1
  WAVE,     // Index 2
  UNKNOWN
};

// --- BIẾN TOÀN CỤC ---
alignas(16) static std::uint8_t g_tensor_arena[STEM_TFLM_ARENA_BYTES];
static i2c_master_dev_handle_t s_mpu_handle = nullptr;

// Bộ đệm lưu dữ liệu float
static float s_input_buffer[BUFFER_LENGTH] = {0};

// Biến cho AI
static tflite::MicroInterpreter* s_interpreter = nullptr;
static TfLiteTensor* s_input = nullptr;
static TfLiteTensor* s_output = nullptr;
static tflite::MicroMutableOpResolver<13> s_resolver;

struct ImuFrame { float ax, ay, az, gx, gy, gz; };

// --- HÀM GIAO TIẾP PHẦN CỨNG ---
static bool InitMpu6050() {
  i2c_master_bus_config_t bus_cfg = {};
  bus_cfg.i2c_port = STEM_I2C_PORT;
  bus_cfg.sda_io_num = STEM_I2C_SDA_PIN;
  bus_cfg.scl_io_num = STEM_I2C_SCL_PIN;
  bus_cfg.clk_source = I2C_CLK_SRC_DEFAULT;
  bus_cfg.flags.enable_internal_pullup = true;

  i2c_master_bus_handle_t bus_handle;
  if (i2c_new_master_bus(&bus_cfg, &bus_handle) != ESP_OK) return false;

  i2c_device_config_t dev_cfg = {};
  dev_cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  dev_cfg.device_address = MPU6050_ADDR;
  dev_cfg.scl_speed_hz = STEM_I2C_FREQ_HZ;
  if (i2c_master_bus_add_device(bus_handle, &dev_cfg, &s_mpu_handle) != ESP_OK) return false;

  // Đánh thức MPU6050
  uint8_t wake[] = {0x6B, 0x00};
  i2c_master_transmit(s_mpu_handle, wake, sizeof(wake), 100);
  
  ESP_LOGI(TAG, "MPU6050 OK");
  return true;
}

static bool ReadImuFrame(ImuFrame* out) {
  uint8_t reg = 0x3B;
  uint8_t data[14];
  if (i2c_master_transmit_receive(s_mpu_handle, &reg, 1, data, 14, 100) != ESP_OK) return false;

  out->ax = (int16_t)((data[0] << 8) | data[1]) / IMU_SCALE;
  out->ay = (int16_t)((data[2] << 8) | data[3]) / IMU_SCALE;
  out->az = (int16_t)((data[4] << 8) | data[5]) / IMU_SCALE;
  out->gx = (int16_t)((data[8] << 8) | data[9]) / IMU_SCALE;
  out->gy = (int16_t)((data[10] << 8) | data[11]) / IMU_SCALE;
  out->gz = (int16_t)((data[12] << 8) | data[13]) / IMU_SCALE;
  return true;
}

// --- HÀM KHỞI TẠO AI ---
static bool InitAI() {
  tflite::InitializeTarget();
  const tflite::Model* model = tflite::GetModel(g_model);

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

  static tflite::MicroInterpreter interpreter(model, s_resolver, g_tensor_arena, STEM_TFLM_ARENA_BYTES);
  s_interpreter = &interpreter;

  if (s_interpreter->AllocateTensors() != kTfLiteOk) return false;

  s_input = s_interpreter->input(0);
  s_output = s_interpreter->output(0);
  
  ESP_LOGI(TAG, "AI OK");
  return true;
}

// --- HÀM CHẠY AI (Cốt lõi, không State Machine) ---
static SpellId RunAI(const ImuFrame& frame) {
  // 1. Dịch buffer sang trái và thêm data mới vào cuối (Window trượt)
  memmove(s_input_buffer, s_input_buffer + CHANNELS, (BUFFER_LENGTH - CHANNELS) * sizeof(float));

  auto clamp = [](float v) { return v > 2.0f ? 2.0f : (v < -2.0f ? -2.0f : v); };
  s_input_buffer[BUFFER_LENGTH - 6] = clamp(frame.ax);
  s_input_buffer[BUFFER_LENGTH - 5] = clamp(frame.ay);
  s_input_buffer[BUFFER_LENGTH - 4] = clamp(frame.az);
  s_input_buffer[BUFFER_LENGTH - 3] = clamp(frame.gx);
  s_input_buffer[BUFFER_LENGTH - 2] = clamp(frame.gy);
  s_input_buffer[BUFFER_LENGTH - 1] = clamp(frame.gz);

  // 2. Chuyển float sang int8 (Lượng tử hóa chuẩn bị cho TFLite)
  const float in_scale = s_input->params.scale;
  const int in_zp = s_input->params.zero_point;
  
  for (int i = 0; i < BUFFER_LENGTH; ++i) {
    int32_t val = (int32_t)(s_input_buffer[i] / in_scale + in_zp + (s_input_buffer[i] > 0 ? 0.5f : -0.5f));
    if (val > 127) val = 127;
    if (val < -128) val = -128;
    s_input->data.int8[i] = (int8_t)val;
  }

  // 3. Chạy model AI
  if (s_interpreter->Invoke() != kTfLiteOk) return SpellId::UNKNOWN;

  // 4. Đọc kết quả và tìm Class có xác suất cao nhất
  const float out_scale = s_output->params.scale;
  const int out_zp = s_output->params.zero_point;
  
  float max_prob = 0.0f;
  int max_idx = -1;

  for (int i = 0; i < 3; ++i) {
    float prob = (s_output->data.int8[i] - out_zp) * out_scale;
    if (prob > max_prob) {
      max_prob = prob;
      max_idx = i;
    }
  }

  // Nếu AI chắc chắn trên 80% thì trả về kết quả
  if (max_prob > 0.80f) {
      if (max_idx == 0) return SpellId::STAND_BY;
      if (max_idx == 1) return SpellId::CIRCLE;
      if (max_idx == 2) return SpellId::WAVE;
  }

  return SpellId::UNKNOWN;
}

// --- VÒNG LẶP CHÍNH ---
extern "C" void app_main(void) {
  if (!InitMpu6050() || !InitAI()) {
    ESP_LOGE(TAG, "Loi khoi tao phan cung hoac AI!");
    return;
  }

  ImuFrame frame{};
  SpellId last_spell = SpellId::UNKNOWN;

  // Dùng vTaskDelayUntil để đảm bảo chu kỳ 50Hz (20ms) chính xác
  TickType_t xLastWakeTime = xTaskGetTickCount();

  while (1) {
    if (ReadImuFrame(&frame)) {
      SpellId current_spell = RunAI(frame);

      // Chỉ in ra nếu kết quả khác với UNKNOWN và khác với động tác liền trước đó
      if (current_spell != SpellId::UNKNOWN && current_spell != last_spell) {
          
          if (current_spell == SpellId::STAND_BY) {
              ESP_LOGI(TAG, "=> STAND_BY");
          } 
          else if (current_spell == SpellId::CIRCLE) {
              ESP_LOGW(TAG, "=> CIRCLE");
          } 
          else if (current_spell == SpellId::WAVE) {
              ESP_LOGW(TAG, "=> WAVE");
          }
          
          last_spell = current_spell;
      }
    }
    
    vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(20));
  }
}