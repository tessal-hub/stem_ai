/*
 * ESP-NOW Receiver for STEM Magic Wand
 * 
 * Target: Any ESP32 board (ESP32 DevKit, ESP32-S3, ESP32-C3, etc.)
 * Platform: Arduino IDE
 * 
 * How it works:
 * The Magic Wand broadcasts an ESP-NOW packet on Wi-Fi Channel 1 whenever a spell is cast.
 * Each spell has an index: 0, 1, 2, 3, ... (based on the order loaded in NVS).
 * This receiver catches the index and triggers hardware (Relay, LED, Servo, Buzzer, etc.).
 */

#include <WiFi.h>
#include <esp_now.h>

// ========== Pin Configuration for Hardware ==========
#define PIN_RELAY_1   23    // Example: Relay or Light for Spell 0
#define PIN_RELAY_2   22    // Example: Relay or Light for Spell 1
#define PIN_BUZZER    19    // Example: Feedback buzzer
#define PIN_STATUS_LED 2    // Built-in LED on most ESP32 DevKits

// ========== Packet Structure (Must match Magic Wand firmware) ==========
struct __attribute__((packed)) SpellEspNowPacket {
    uint8_t magic[2];      // 'S', 'P' (0x53, 0x50)
    uint8_t spell_index;   // Spell index: 0, 1, 2, ...
    char spell_name[16];   // e.g. "LUMOS", "NOX", "ALOHOMORA" (null-terminated)
    uint8_t confidence;    // 0 - 100 (%)
    uint8_t r;             // RGB color (0 - 255)
    uint8_t g;
    uint8_t b;
};

// Callback when data is received via ESP-NOW
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
    if (len < sizeof(SpellEspNowPacket)) {
        return;
    }

    SpellEspNowPacket packet;
    memcpy(&packet, incomingData, sizeof(SpellEspNowPacket));

    // Verify packet header
    if (packet.magic[0] != 'S' || packet.magic[1] != 'P') {
        return;
    }

    Serial.println("========================================");
    Serial.printf("🔮 SPELL RECEIVED!\n");
    Serial.printf("👉 Index      : %d\n", packet.spell_index);
    Serial.printf("👉 Name       : %s\n", packet.spell_name);
    Serial.printf("👉 Confidence : %d%%\n", packet.confidence);
    Serial.printf("👉 RGB Color  : R=%d, G=%d, B=%d\n", packet.r, packet.g, packet.b);
    Serial.println("========================================");

    // Visual feedback on Status LED
    digitalWrite(PIN_STATUS_LED, HIGH);

    // =========================================================================
    // CONTROL YOUR HARDWARE HERE BASED ON spell_index (0, 1, 2, 3, ...)
    // =========================================================================
    switch (packet.spell_index) {
        case 0:
            // Spell 0 (e.g. LUMOS -> Turn ON light/relay)
            Serial.println("Action: [Spell 0] -> Turn ON Relay 1");
            digitalWrite(PIN_RELAY_1, HIGH);
            break;

        case 1:
            // Spell 1 (e.g. NOX -> Turn OFF light/relay)
            Serial.println("Action: [Spell 1] -> Turn OFF Relay 1");
            digitalWrite(PIN_RELAY_1, LOW);
            break;

        case 2:
            // Spell 2 (e.g. ALOHOMORA -> Toggle Relay 2 or open door)
            Serial.println("Action: [Spell 2] -> Trigger Relay 2");
            digitalWrite(PIN_RELAY_2, HIGH);
            delay(1000);
            digitalWrite(PIN_RELAY_2, LOW);
            break;

        case 3:
            // Spell 3 (e.g. AGUAMENTI)
            Serial.println("Action: [Spell 3] -> Custom action");
            break;

        default:
            Serial.printf("Action: [Spell %d] -> Unassigned action\n", packet.spell_index);
            break;
    }

    delay(200);
    digitalWrite(PIN_STATUS_LED, LOW);
}

void setup() {
    Serial.begin(115200);
    Serial.println("\n--- STEM Magic Wand ESP-NOW Receiver ---");

    // Initialize hardware output pins
    pinMode(PIN_RELAY_1, OUTPUT);
    pinMode(PIN_RELAY_2, OUTPUT);
    pinMode(PIN_STATUS_LED, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);

    digitalWrite(PIN_RELAY_1, LOW);
    digitalWrite(PIN_RELAY_2, LOW);
    digitalWrite(PIN_STATUS_LED, LOW);
    digitalWrite(PIN_BUZZER, LOW);

    // Set ESP32 to Wi-Fi Station mode
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    // Init ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("❌ Error initializing ESP-NOW");
        return;
    }

    // Register receive callback
    esp_now_register_recv_cb(OnDataRecv);

    Serial.println("✅ ESP-NOW Receiver ready on Channel 1!");
    Serial.println("Waiting for Magic Wand gestures...\n");
}

void loop() {
    delay(100);
}
