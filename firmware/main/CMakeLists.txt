idf_component_register(
    SRCS "main.cpp"
         "ui/app.cpp"
         "term/vt.cpp"
         "term/renderer.cpp"
         "input/keyboard.cpp"
         "input/ble_kbd.cpp"
         "net/wifi_mgr.cpp"
         "net/ssh_client.cpp"
         "storage/settings.cpp"
         "storage/sdcard.cpp"
    INCLUDE_DIRS "."
    PRIV_REQUIRES M5GFX M5Unified libssh2 esp_wifi esp_event esp_netif nvs_flash bt esp_hid
                  fatfs sdmmc esp_driver_sdspi esp_driver_spi esp_driver_gpio vfs mbedtls lwip esp_timer)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-missing-field-initializers)
