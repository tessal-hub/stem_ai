idf_component_register(
    SRCS "main.cpp" "model_classic.cc"
    INCLUDE_DIRS "."
    REQUIRES driver esp_driver_gpio esp_driver_i2c esp_driver_ledc esp_timer freertos log nvs_flash esp_event esp_wifi
)
