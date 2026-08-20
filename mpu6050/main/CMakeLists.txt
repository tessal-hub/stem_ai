idf_component_register(
    SRCS "main.cpp"
    INCLUDE_DIRS "."
    REQUIRES
        esp_driver_i2c
        esp_driver_ledc
        esp_driver_uart
        driver
        spi_flash
        esp_partition
        spiffs
        espressif__esp-tflite-micro
        esp_timer
        nvs_flash
        esp_driver_gpio
        esp_rom
        esp_system
)