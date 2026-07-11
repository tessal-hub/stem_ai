idf_component_register(
    SRCS "gesture_model.cc" "main.cpp"
    INCLUDE_DIRS "."
    REQUIRES
        esp_driver_i2c
        esp_driver_uart
        driver
        spi_flash
        esp_partition
        spiffs
        espressif__esp-tflite-micro
        esp_timer
)