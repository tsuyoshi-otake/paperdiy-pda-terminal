// PaperDIY Terminal — BLE keyboard + Wi-Fi + SSH terminal on M5Stack PaperDIY (ESP32-S3, 4.7" e-paper)
#include "ui/app.h"

extern "C" void app_main(void)
{
    static App app;
    app.run();
}
