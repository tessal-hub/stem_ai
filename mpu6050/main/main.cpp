#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/i2c_master.h"
#include "driver/uart.h"
#include "esp_spiffs.h"
#include "esp_system.h"

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

// Đổi WINDOW_SIZE từ 40 sang 64 để đồng bộ với model encoder mới
#define WINDOW_SIZE 64
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

// Buffer chứa model nạp động từ SPIFFS
static uint8_t* s_dynamic_model_buf = nullptr;

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

// --- HÀM KHỞI TẠO SPIFFS ---
static bool InitSpiffs() {
  esp_vfs_spiffs_conf_t conf = {
      .base_path = "/storage",
      .partition_label = "storage",
      .max_files = 5,
      .format_if_mount_failed = true
  };
  esp_err_t ret = esp_vfs_spiffs_register(&conf);
  if (ret != ESP_OK) {
      ESP_LOGE(TAG, "Mount SPIFFS failed (%s)", esp_err_to_name(ret));
      return false;
  }
  ESP_LOGI(TAG, "SPIFFS Mounted successfully");
  return true;
}

// --- HÀM KHỞI TẠO AI ---
static bool InitAI() {
  tflite::InitializeTarget();

  const tflite::Model* model = nullptr;

  // Thử nạp model động từ SPIFFS trước
  FILE* f = fopen("/storage/model.tflite", "rb");
  if (f != nullptr) {
      fseek(f, 0, SEEK_END);
      long size = ftell(f);
      fseek(f, 0, SEEK_SET);
      s_dynamic_model_buf = (uint8_t*) malloc(size);
      if (s_dynamic_model_buf != nullptr) {
          fread(s_dynamic_model_buf, 1, size, f);
          model = tflite::GetModel(s_dynamic_model_buf);
          ESP_LOGI(TAG, "Loaded dynamic model from SPIFFS (%ld bytes)", size);
      } else {
          ESP_LOGE(TAG, "Failed to allocate memory for dynamic model (%ld bytes)", size);
      }
      fclose(f);
  }

  // Fallback về model tĩnh nếu không tìm thấy hoặc lỗi memory
  if (model == nullptr) {
      model = tflite::GetModel(g_model);
      ESP_LOGI(TAG, "Using static fallback model");
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

  static tflite::MicroInterpreter interpreter(model, s_resolver, g_tensor_arena, STEM_TFLM_ARENA_BYTES);
  s_interpreter = &interpreter;

  if (s_interpreter->AllocateTensors() != kTfLiteOk) return false;

  s_input = s_interpreter->input(0);
  s_output = s_interpreter->output(0);
  
  ESP_LOGI(TAG, "AI OK");
  return true;
}

// --- HÀM CHẠY AI (Cốt lõi, không State Machine) ---
static int RunAI(const ImuFrame& frame) {
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
  if (s_interpreter->Invoke() != kTfLiteOk) return -1;

  // 4. Đọc kết quả và tìm Class có xác suất cao nhất
  const float out_scale = s_output->params.scale;
  const int out_zp = s_output->params.zero_point;
  
  int num_classes = s_output->dims->data[s_output->dims->size - 1];
  float max_prob = 0.0f;
  int max_idx = -1;

  for (int i = 0; i < num_classes; ++i) {
    float prob = (s_output->data.int8[i] - out_zp) * out_scale;
    if (prob > max_prob) {
      max_prob = prob;
      max_idx = i;
    }
  }

  // Nếu AI chắc chắn trên 80% thì trả về index lớp
  if (max_prob > 0.80f) {
      return max_idx;
  }

  return -1;
}

// --- TASK NHẬN MODEL QUA SERIAL (115200 baud) ---
void model_upload_task(void *pvParameters) {
    const uart_port_t uart_num = UART_NUM_0;
    uart_config_t uart_config = {};
    uart_config.baud_rate = 115200;
    uart_config.data_bits = UART_DATA_8_BITS;
    uart_config.parity = UART_PARITY_DISABLE;
    uart_config.stop_bits = UART_STOP_BITS_1;
    uart_config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    uart_config.source_clk = UART_SCLK_DEFAULT;
    
    // Cấu hình UART0 buffer lớn để tránh tràn bộ đệm
    uart_driver_install(uart_num, 8192, 0, 0, NULL, 0);
    uart_param_config(uart_num, &uart_config);

    uint8_t* dtmp = (uint8_t*) malloc(4096);
    char line_buf[128];
    int line_idx = 0;

    // ESP_LOGI(TAG, "Model Upload Listener Task Started (115200 baud)");

    while (1) {
        uint8_t ch;
        int len = uart_read_bytes(uart_num, &ch, 1, portMAX_DELAY);
        if (len <= 0) continue;

        if (ch == '\n' || ch == '\r') {
            line_buf[line_idx] = '\0';
            int file_size = 0;
            if (sscanf(line_buf, "CMD:UPLOAD_MODEL:%d", &file_size) == 1) {
                // Tắt log ngay lập tức để không có gì khác ghi ra UART0
                // trước khi gửi ACK, tránh làm hỏng giao thức nhị phân.
                esp_log_level_set("*", ESP_LOG_NONE);

                FILE* f = fopen("/storage/model.tflite", "wb");
                if (f == nullptr) {
                    esp_log_level_set("*", ESP_LOG_INFO);
                    uart_write_bytes(uart_num, "ACK:FAIL_OPEN\n", 14);
                    line_idx = 0;
                    continue;
                }
                
                // Trả về ACK:READY báo cho PC biết đã sẵn sàng nhận
                uart_write_bytes(uart_num, "ACK:READY\n", 10);

                int remaining = file_size;
                bool success = true;

                while (remaining > 0) {
                    int chunk_to_read = (remaining > 4096) ? 4096 : remaining;
                    int bytes_read = 0;
                    
                    // Đọc đủ block 4096 bytes (hoặc block cuối)
                    while (bytes_read < chunk_to_read) {
                        int r = uart_read_bytes(uart_num, dtmp + bytes_read, 
                                                chunk_to_read - bytes_read, pdMS_TO_TICKS(5000));
                        if (r <= 0) {
                            success = false;
                            break; // Timeout
                        }
                        bytes_read += r;
                    }
                    if (!success) break;

                    fwrite(dtmp, 1, chunk_to_read, f);
                    remaining -= chunk_to_read;
                    
                    uart_write_bytes(uart_num, "ACK:CHUNK_RECEIVED\n", 19);
                }

                fclose(f);

                if (success) {
                    uart_write_bytes(uart_num, "ACK:UPLOAD_COMPLETE\n", 20);
                    vTaskDelay(pdMS_TO_TICKS(1500));
                    esp_restart(); // Restart chip để chạy model mới
                } else {
                    // ESP_LOGE(TAG, "Upload failed due to serial timeout");
                }
            }
            line_idx = 0;
        } else {
            if (line_idx < 127) {
                line_buf[line_idx++] = ch;
            }
        }
    }
    
    free(dtmp);
    vTaskDelete(NULL);
}

// --- VÒNG LẶP CHÍNH ---
extern "C" void app_main(void) {
  // 1. Khởi động hệ thống file SPIFFS
  InitSpiffs();

  // 2. Chạy Thread nhận dạng model ngầm
  xTaskCreate(model_upload_task, "model_upload_task", 8192, NULL, 5, NULL);

  // 3. Khởi tạo cảm biến MPU6050 & AI
  if (!InitMpu6050() || !InitAI()) {
    ESP_LOGE(TAG, "Loi khoi tao phan cung hoac AI!");
    return;
  }

  ImuFrame frame{};
  int last_class_idx = -1;

  TickType_t xLastWakeTime = xTaskGetTickCount();

  while (1) {
    if (ReadImuFrame(&frame)) {
      int current_class_idx = RunAI(frame);

      if (current_class_idx != -1) {
          if (current_class_idx != last_class_idx) {
              // Lấy xác suất của class chiến thắng
              float prob = (s_output->data.int8[current_class_idx] - s_output->params.zero_point) * s_output->params.scale;
              // In đúng định dạng giao thức để ứng dụng PC hiển thị thời gian thực (PREDICT:<label>:<confidence>)
              printf("PREDICT:%d:%.2f\n", current_class_idx, prob);
              last_class_idx = current_class_idx;
          }
      } else {
          last_class_idx = -1; // Reset trạng thái khi đũa quay về tĩnh (idle)
      }
    }
    vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(20));
  }
}