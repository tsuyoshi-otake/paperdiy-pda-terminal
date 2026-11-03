// Draws a term::Vt onto the PaperDIY e-paper with partial refreshes, plus a status bar.
#pragma once

#include <M5GFX.h>

#include <atomic>
#include <string>
#include <vector>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "vt.h"

namespace term {

class Renderer {
public:
    // font_px: 16 (8x16 cells, 120x32) or 24 (12x24 cells, 80x21)
    void begin(M5GFX* gfx, int font_px, bool rotate180);
    void setFont(int font_px);
    void setRotate180(bool flip);
    int cols() const { return cols_; }
    int rows() const { return rows_; }
    int fontPx() const { return font_px_; }

    void attach(Vt* vt);  // the screen to show (console or SSH session)
    Vt* attached() const { return vt_; }
    void setStatus(const std::string& left, const std::string& right);
    void requestFullRefresh();
    void kick();  // something changed: wake the render task

private:
    static void taskEntry(void* arg);
    void loop();
    void layout();
    void drawRow(int y, const Cell* cells, int cursor_x);
    void drawGlyph(uint32_t cp, int px, int py, int wcells, bool inverse, uint8_t attr);
    bool drawBoxChar(uint32_t cp, int px, int py, uint16_t fg);
    void drawStatus();

    M5GFX* gfx_ = nullptr;
    TaskHandle_t task_ = nullptr;
    SemaphoreHandle_t mtx_ = nullptr;
    Vt* vt_ = nullptr;
    Vt* drawn_vt_ = nullptr;
    int font_px_ = 24;
    int cell_w_ = 12, cell_h_ = 24;
    int cols_ = 80, rows_ = 21;
    int width_ = 960, height_ = 540;
    int status_y_ = 0;
    std::string status_left_, status_right_;
    bool status_dirty_ = true;
    std::atomic<bool> full_request_{true};
    int partials_since_clean_ = 0;
    int64_t last_draw_us_ = 0;
    int drawn_cur_x_ = -1, drawn_cur_y_ = -1;  // cursor as last drawn (x = -1: hidden)
    std::vector<Cell> snapshot_;
    std::vector<uint8_t> dirty_;
};

}  // namespace term
