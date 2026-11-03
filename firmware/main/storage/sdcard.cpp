#include "sdcard.h"

#include "driver/gpio.h"
#include "driver/sdspi_host.h"
#include "driver/spi_master.h"
#include "esp_log.h"
#include "esp_vfs_fat.h"

namespace sdcard {
namespace {

constexpr char kTag[] = "sdcard";
constexpr gpio_num_t kMiso = GPIO_NUM_40;
constexpr gpio_num_t kMosi = GPIO_NUM_38;
constexpr gpio_num_t kSclk = GPIO_NUM_39;
constexpr gpio_num_t kCs = GPIO_NUM_47;
constexpr gpio_num_t kDetect = GPIO_NUM_48;

sdmmc_card_t* s_card = nullptr;
bool s_bus_ready = false;
bool s_detect_ready = false;

}  // namespace

bool inserted()
{
    if (!s_detect_ready) {
        gpio_config_t cfg = {};
        cfg.pin_bit_mask = 1ULL << kDetect;
        cfg.mode = GPIO_MODE_INPUT;
        cfg.pull_up_en = GPIO_PULLUP_ENABLE;
        gpio_config(&cfg);
        s_detect_ready = true;
    }
    return gpio_get_level(kDetect) == 0;
}

bool mounted() { return s_card != nullptr; }

bool mount()
{
    if (s_card) return true;
    if (!inserted()) return false;

    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    if (!s_bus_ready) {
        spi_bus_config_t bus = {};
        bus.mosi_io_num = kMosi;
        bus.miso_io_num = kMiso;
        bus.sclk_io_num = kSclk;
        bus.quadwp_io_num = -1;
        bus.quadhd_io_num = -1;
        bus.max_transfer_sz = 4000;
        esp_err_t err = spi_bus_initialize(static_cast<spi_host_device_t>(host.slot), &bus, SDSPI_DEFAULT_DMA);
        if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
            ESP_LOGE(kTag, "spi bus init failed: %s", esp_err_to_name(err));
            return false;
        }
        s_bus_ready = true;
    }

    esp_vfs_fat_sdmmc_mount_config_t mount_cfg = {};
    mount_cfg.format_if_mount_failed = false;
    mount_cfg.max_files = 4;
    mount_cfg.allocation_unit_size = 16 * 1024;

    sdspi_device_config_t slot = SDSPI_DEVICE_CONFIG_DEFAULT();
    slot.gpio_cs = kCs;
    slot.host_id = static_cast<spi_host_device_t>(host.slot);

    esp_err_t err = esp_vfs_fat_sdspi_mount(kMountPoint, &host, &slot, &mount_cfg, &s_card);
    if (err != ESP_OK) {
        ESP_LOGW(kTag, "mount failed: %s", esp_err_to_name(err));
        s_card = nullptr;
        return false;
    }
    ESP_LOGI(kTag, "mounted at %s", kMountPoint);
    return true;
}

}  // namespace sdcard
