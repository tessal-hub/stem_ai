/*
 * ESP-NOW Receiver Example for ESP-IDF
 * 
 * Catch spell index 0, 1, 2, ... from STEM Magic Wand to control hardware.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_now.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "driver/gpio.h"

static const char* TAG = "SPELL_RECV";

#define PIN_RELAY_1     GPIO_NUM_23
#define PIN_RELAY_2     GPIO_NUM_22
#define PIN_STATUS_LED  GPIO_NUM_2

struct __attribute__((packed)) SpellEspNowPacket {
    uint8_t magic[2];      // 'S', 'P' (0x53, 0x50)
    uint8_t spell_index;   // Spell index: 0, 1, 2, ...
    char spell_name[16];   // e.g. "LUMOS", "NOX"
    uint8_t confidence;    // 0 - 100 (%)
    uint8_t r;
    uint8_t g;
    uint8_t b;
};

static void OnEspNowRecv(const esp_now_recv_info_t *recv_info, const uint8_t *data, int len) {
    if (len < sizeof(SpellEspNowPacket)) return;

    SpellEspNowPacket packet;
    memcpy(&packet, data, sizeof(SpellEspNowPacket));

    if (packet.magic[0] != 'S' || packet.magic[1] != 'P') return;

    ESP_LOGI(TAG, "🔮 SPELL RECEIVED: Index=%d | Name=%s | Conf=%d%% | RGB=(%d,%d,%d)",
             packet.spell_index, packet.spell_name, packet.confidence, packet.r, packet.g, packet.b);

    gpio_set_level(PIN_STATUS_LED, 1);

    // Control hardware based on spell_index
    switch (packet.spell_index) {
        case 0:
            ESP_LOGI(TAG, "Action: [Spell 0] -> Turn ON Relay 1");
            gpio_set_level(PIN_RELAY_1, 1);
            break;
        case 1:
            ESP_LOGI(TAG, "Action: [Spell 1] -> Turn OFF Relay 1");
            gpio_set_level(PIN_RELAY_1, 0);
            break;
        case 2:
            ESP_LOGI(TAG, "Action: [Spell 2] -> Toggle Relay 2");
            gpio_set_level(PIN_RELAY_2, 1);
            vTaskDelay(pdMS_TO_TICKS(1000));
            gpio_set_level(PIN_RELAY_2, 0);
            break;
        default:
            ESP_LOGI(TAG, "Action: [Spell %d] -> Custom action", packet.spell_index);
            break;
    }

    vTaskDelay(pdMS_TO_TICKS(200));
    gpio_set_level(PIN_STATUS_LED, 0);
}

void app_main(void) {
    // 1. Init NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    // 2. Init GPIOs
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << PIN_RELAY_1) | (1ULL << PIN_RELAY_2) | (1ULL << PIN_STATUS_LED),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
    gpio_set_level(PIN_RELAY_1, 0);
    gpio_set_level(PIN_RELAY_2, 0);
    gpio_set_level(PIN_STATUS_LED, 0);

    // 3. Init Wi-Fi in Station Mode (Channel 1)
    esp_netif_init();
    esp_event_loop_create_default();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_storage(WIFI_STORAGE_RAM);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();
    esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);

    // 4. Init ESP-NOW
    esp_now_init();
    esp_now_register_recv_cb(OnEspNowRecv);

    ESP_LOGI(TAG, "✅ ESP-NOW Receiver ready on Channel 1. Waiting for spells...");
}
