#include "renderer.h"

#include <algorithm>

#include "esp_log.h"
#include "esp_timer.h"

namespace term {
namespace {

constexpr char kTag[] = "render";
constexpr uint16_t kBlack = TFT_BLACK;
constexpr uint16_t kWhite = TFT_WHITE;
constexpr int64_t kCleanupIdleUs = 4 * 1000 * 1000;  // full refresh after 4 s of quiet...
constexpr int kCleanupAfterPartials = 12;           // ...if this many fast partial updates piled up
constexpr int kForceCleanupPartials = 120;          // never let ghosting grow beyond this

int s_base_rotation = 0;

// Box drawing segments: 2 bits each for left, right, up, down (1 light, 2 heavy, 3 double)
constexpr uint8_t seg(int l, int r, int u, int d) { return l | (r << 2) | (u << 4) | (d << 6); }

uint8_t boxSegments(uint32_t cp)
{
    switch (cp) {
        case 0x2500: case 0x2504: case 0x2508: case 0x254C: return seg(1, 1, 0, 0);
        case 0x2501: case 0x2505: case 0x2509: case 0x254D: return seg(2, 2, 0, 0);
        case 0x2502: case 0x2506: case 0x250A: case 0x254E: return seg(0, 0, 1, 1);
        case 0x2503: case 0x2507: case 0x250B: case 0x254F: return seg(0, 0, 2, 2);
        case 0x250C: case 0x256D: return seg(0, 1, 0, 1);
        case 0x2510: case 0x256E: return seg(1, 0, 0, 1);
        case 0x2514: case 0x2570: return seg(0, 1, 1, 0);
        case 0x2518: case 0x256F: return seg(1, 0, 1, 0);
        case 0x251C: return seg(0, 1, 1, 1);
        case 0x2524: return seg(1, 0, 1, 1);
        case 0x252C: return seg(1, 1, 0, 1);
        case 0x2534: return seg(1, 1, 1, 0);
        case 0x253C: return seg(1, 1, 1, 1);
        case 0x250F: return seg(0, 2, 0, 2);
        case 0x2513: return seg(2, 0, 0, 2);
        case 0x2517: return seg(0, 2, 2, 0);
        case 0x251B: return seg(2, 0, 2, 0);
        case 0x2523: return seg(0, 2, 2, 2);
        case 0x252B: return seg(2, 0, 2, 2);
        case 0x2533: return seg(2, 2, 0, 2);
        case 0x253B: return seg(2, 2, 2, 0);
        case 0x254B: return seg(2, 2, 2, 2);
        case 0x2550: return seg(3, 3, 0, 0);
        case 0x2551: return seg(0, 0, 3, 3);
        case 0x2552: return seg(0, 3, 0, 1);
        case 0x2553: return seg(0, 1, 0, 3);
        case 0x2554: return seg(0, 3, 0, 3);
        case 0x2555: return seg(3, 0, 0, 1);
        case 0x2556: return seg(1, 0, 0, 3);
        case 0x2557: return seg(3, 0, 0, 3);
        case 0x2558: return seg(0, 3, 1, 0);
        case 0x2559: return seg(0, 1, 3, 0);
        case 0x255A: return seg(0, 3, 3, 0);
        case 0x255B: return seg(3, 0, 1, 0);
        case 0x255C: return seg(1, 0, 3, 0);
        case 0x255D: return seg(3, 0, 3, 0);
        case 0x255E: return seg(0, 3, 1, 1);
        case 0x255F: return seg(0, 1, 3, 3);
        case 0x2560: return seg(0, 3, 3, 3);
        case 0x2561: return seg(3, 0, 1, 1);
        case 0x2562: return seg(1, 0, 3, 3);
        case 0x2563: return seg(3, 0, 3, 3);
        case 0x2564: return seg(3, 3, 0, 1);
        case 0x2565: return seg(1, 1, 0, 3);
        case 0x2566: return seg(3, 3, 0, 3);
        case 0x2567: return seg(3, 3, 1, 0);
        case 0x2568: return seg(1, 1, 3, 0);
        case 0x2569: return seg(3, 3, 3, 0);
        case 0x256A: return seg(3, 3, 1, 1);
        case 0x256B: return seg(1, 1, 3, 3);
        case 0x256C: return seg(3, 3, 3, 3);
        case 0x2574: return seg(1, 0, 0, 0);
        case 0x2575: return seg(0, 0, 1, 0);
        case 0x2576: return seg(0, 1, 0, 0);
        case 0x2577: return seg(0, 0, 0, 1);
        case 0x2578: return seg(2, 0, 0, 0);
        case 0x2579: return seg(0, 0, 2, 0);
        case 0x257A: return seg(0, 2, 0, 0);
        case 0x257B: return seg(0, 0, 0, 2);
        default: return 0;
    }
}

size_t utf8Encode(uint32_t cp, char* out)
{
    if (cp < 0x80) {
        out[0] = static_cast<char>(cp);
        return 1;
    }
    if (cp < 0x800) {
        out[0] = static_cast<char>(0xC0 | (cp >> 6));
        out[1] = static_cast<char>(0x80 | (cp & 0x3F));
        return 2;
    }
    if (cp < 0x10000) {
        out[0] = static_cast<char>(0xE0 | (cp >> 12));
        out[1] = static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out[2] = static_cast<char>(0x80 | (cp & 0x3F));
        return 3;
    }
    out[0] = '?';
    return 1;
}

}  // namespace

void Renderer::begin(M5GFX* gfx, int font_px, bool rotate180)
{
    gfx_ = gfx;
    mtx_ = xSemaphoreCreateMutex();
    font_px_ = (font_px == 16) ? 16 : 24;
    gfx_->setAutoDisplay(false);
    int r = gfx_->getRotation();
    if (gfx_->width() < gfx_->height()) r = (r + 1) & 3;  // landscape: 960 x 540
    s_base_rotation = r;
    gfx_->setRotation(rotate180 ? ((r + 2) & 3) : r);
    layout();
    gfx_->setEpdMode(epd_mode_t::epd_quality);
    gfx_->fillScreen(kWhite);
    xTaskCreatePinnedToCore(taskEntry, "render", 6144, this, 4, &task_, 1);
}

void Renderer::layout()
{
    width_ = gfx_->width();
    height_ = gfx_->height();
    cell_h_ = font_px_;
    cell_w_ = font_px_ / 2;
    cols_ = width_ / cell_w_;
    rows_ = height_ / cell_h_ - 1;  // last text row is the status bar
    status_y_ = rows_ * cell_h_;
    gfx_->setFont(font_px_ == 24 ? &fonts::efontJA_24 : &fonts::efontJA_16);
    gfx_->setTextDatum(textdatum_t::top_left);
    gfx_->setTextWrap(false);
    snapshot_.assign(static_cast<size_t>(cols_) * rows_, Cell{' ', 0, 1});
    ESP_LOGI(kTag, "layout %dx%d px, %dx%d cells", width_, height_, cols_, rows_);
}

void Renderer::setFont(int font_px)
{
    xSemaphoreTake(mtx_, portMAX_DELAY);
    gfx_->waitDisplay();
    font_px_ = (font_px == 16) ? 16 : 24;
    layout();
    status_dirty_ = true;
    full_request_ = true;
    xSemaphoreGive(mtx_);
    kick();
}

void Renderer::setRotate180(bool flip)
{
    xSemaphoreTake(mtx_, portMAX_DELAY);
    gfx_->waitDisplay();
    gfx_->setRotation(flip ? ((s_base_rotation + 2) & 3) : s_base_rotation);
    layout();
    status_dirty_ = true;
    full_request_ = true;
    xSemaphoreGive(mtx_);
    kick();
}

void Renderer::attach(Vt* vt)
{
    xSemaphoreTake(mtx_, portMAX_DELAY);
    vt_ = vt;
    xSemaphoreGive(mtx_);
    kick();
}

void Renderer::setStatus(const std::string& left, const std::string& right)
{
    xSemaphoreTake(mtx_, portMAX_DELAY);
    if (left != status_left_ || right != status_right_) {
        status_left_ = left;
        status_right_ = right;
        status_dirty_ = true;
    }
    xSemaphoreGive(mtx_);
    if (status_dirty_) kick();
}

void Renderer::requestFullRefresh()
{
    full_request_ = true;
    kick();
}

void Renderer::kick()
{
    if (task_) xTaskNotifyGive(task_);
}

void Renderer::taskEntry(void* arg) { static_cast<Renderer*>(arg)->loop(); }

void Renderer::loop()
{
    for (;;) {
        ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(500));
        vTaskDelay(pdMS_TO_TICKS(15));  // let bursts of output coalesce into one update
        gfx_->waitDisplay();

        xSemaphoreTake(mtx_, portMAX_DELAY);
        Vt* vt = vt_;
        if (!vt) {
            xSemaphoreGive(mtx_);
            continue;
        }
        bool full = full_request_.exchange(false) || vt != drawn_vt_;
        vt->lock();
        if (vt->cols() != cols_ || vt->rows() != rows_) {
            // the app resizes screens after a font change; try again shortly
            vt->unlock();
            full_request_ = full_request_ || full;
            xSemaphoreGive(mtx_);
            vTaskDelay(pdMS_TO_TICKS(20));
            continue;
        }
        if (full) vt->markAllDirty();
        vt->collectDirty(dirty_);
        const int cur_x = vt->cursorVisible() ? vt->cursorX() : -1;
        const int cur_y = vt->cursorY();
        // A row marked dirty may still look the same (menus redraw the whole screen, for example).
        // Skip rows whose cells and cursor are unchanged so that e-paper does not flash for nothing.
        bool any = false;
        for (int y = 0; y < rows_; ++y) {
            if (!dirty_[y]) continue;
            bool same = !full && (y == drawn_cur_y_ ? drawn_cur_x_ : -1) == (y == cur_y ? cur_x : -1);
            Cell* row = &snapshot_[y * cols_];
            for (int x = 0; x < cols_; ++x) {
                const Cell c = vt->cell(x, y);
                if (same && (c.cp != row[x].cp || c.attr != row[x].attr || c.width != row[x].width)) same = false;
                row[x] = c;
            }
            if (same) dirty_[y] = 0;
            else any = true;
        }
        drawn_cur_x_ = cur_x;
        drawn_cur_y_ = cur_y;
        vt->unlock();
        drawn_vt_ = vt;
        const bool status = status_dirty_ || full;
        status_dirty_ = false;

        const int64_t now = esp_timer_get_time();
        if (!any && !status) {
            if (partials_since_clean_ >= kCleanupAfterPartials && now - last_draw_us_ > kCleanupIdleUs) {
                gfx_->setEpdMode(epd_mode_t::epd_quality);
                gfx_->display(0, 0, width_, height_);
                partials_since_clean_ = 0;
            }
            xSemaphoreGive(mtx_);
            continue;
        }

        int y0 = height_, y1 = 0;
        gfx_->startWrite();
        for (int y = 0; y < rows_; ++y) {
            if (!dirty_[y]) continue;
            drawRow(y, &snapshot_[y * cols_], y == cur_y ? cur_x : -1);
            y0 = std::min(y0, y * cell_h_);
            y1 = std::max(y1, (y + 1) * cell_h_);
        }
        if (status) {
            drawStatus();
            y0 = std::min(y0, status_y_);
            y1 = height_;
        }
        gfx_->endWrite();

        if (full || partials_since_clean_ >= kForceCleanupPartials) {
            gfx_->setEpdMode(epd_mode_t::epd_quality);
            gfx_->display(0, 0, width_, height_);
            partials_since_clean_ = 0;
        } else if (y1 > y0) {
            gfx_->setEpdMode(epd_mode_t::epd_fastest);
            gfx_->display(0, y0, width_, y1 - y0);
            partials_since_clean_++;
        }
        last_draw_us_ = now;
        xSemaphoreGive(mtx_);
    }
}

void Renderer::drawRow(int y, const Cell* cells, int cursor_x)
{
    const int py = y * cell_h_;
    gfx_->fillRect(0, py, width_, cell_h_, kWhite);
    for (int x = 0; x < cols_; ++x) {
        const Cell& c = cells[x];
        if (c.width == 0) continue;
        const int w = (c.width == 2 && x + 1 < cols_) ? 2 : 1;
        bool inv = ((c.attr & kAttrInverse) != 0) != ((c.attr & kAttrDarkBg) != 0);
        if (x == cursor_x || (w == 2 && x + 1 == cursor_x)) inv = !inv;
        if (c.cp == ' ' && !inv && !(c.attr & kAttrUnderline)) continue;
        drawGlyph(c.cp, x * cell_w_, py, w, inv, c.attr);
    }
}

void Renderer::drawGlyph(uint32_t cp, int px, int py, int wcells, bool inverse, uint8_t attr)
{
    const int w = cell_w_ * wcells;
    const uint16_t fg = inverse ? kWhite : kBlack;
    if (inverse) gfx_->fillRect(px, py, w, cell_h_, kBlack);
    if (cp != ' ' && !drawBoxChar(cp, px, py, fg)) {
        char s[5] = {};
        utf8Encode(cp, s);
        gfx_->setTextColor(fg);
        gfx_->drawString(s, px, py);
        if (attr & kAttrBold) gfx_->drawString(s, px + 1, py);
    }
    if (attr & kAttrUnderline) gfx_->fillRect(px, py + cell_h_ - 2, w, 1 + cell_h_ / 24, fg);
}

bool Renderer::drawBoxChar(uint32_t cp, int px, int py, uint16_t fg)
{
    const int cw = cell_w_, ch = cell_h_;
    // Block elements and shades
    if (cp >= 0x2580 && cp <= 0x259F) {
        const int hw = cw / 2, hh = ch / 2;
        auto quad = [&](bool ul, bool ur, bool ll, bool lr) {
            if (ul) gfx_->fillRect(px, py, hw, hh, fg);
            if (ur) gfx_->fillRect(px + hw, py, cw - hw, hh, fg);
            if (ll) gfx_->fillRect(px, py + hh, hw, ch - hh, fg);
            if (lr) gfx_->fillRect(px + hw, py + hh, cw - hw, ch - hh, fg);
        };
        if (cp == 0x2580) gfx_->fillRect(px, py, cw, hh, fg);
        else if (cp >= 0x2581 && cp <= 0x2588) {
            int h = ch * (cp - 0x2580) / 8;
            gfx_->fillRect(px, py + ch - h, cw, h, fg);
        } else if (cp >= 0x2589 && cp <= 0x258F) {
            int w = cw * (0x2590 - cp) / 8;
            gfx_->fillRect(px, py, std::max(1, w), ch, fg);
        } else if (cp == 0x2590) gfx_->fillRect(px + hw, py, cw - hw, ch, fg);
        else if (cp >= 0x2591 && cp <= 0x2593) {
            // shades as a checker pattern (e-paper fast mode is two-level)
            const int step = (cp == 0x2591) ? 4 : (cp == 0x2592 ? 2 : 1);
            for (int yy = 0; yy < ch; ++yy) {
                for (int xx = (yy % 2) * (step == 1 ? 0 : step / 2); xx < cw; xx += step) {
                    if (step == 1 && ((xx + yy) % 4 == 0)) continue;
                    gfx_->drawPixel(px + xx, py + yy, fg);
                }
            }
        } else if (cp == 0x2594) gfx_->fillRect(px, py, cw, std::max(1, ch / 8), fg);
        else if (cp == 0x2595) gfx_->fillRect(px + cw - std::max(1, cw / 8), py, std::max(1, cw / 8), ch, fg);
        else if (cp == 0x2596) quad(false, false, true, false);
        else if (cp == 0x2597) quad(false, false, false, true);
        else if (cp == 0x2598) quad(true, false, false, false);
        else if (cp == 0x2599) quad(true, false, true, true);
        else if (cp == 0x259A) quad(true, false, false, true);
        else if (cp == 0x259B) quad(true, true, true, false);
        else if (cp == 0x259C) quad(true, true, false, true);
        else if (cp == 0x259D) quad(false, true, false, false);
        else if (cp == 0x259E) quad(false, true, true, false);
        else if (cp == 0x259F) quad(false, true, true, true);
        return true;
    }
    // Scan lines from DEC graphics
    if (cp >= 0x23BA && cp <= 0x23BD) {
        const int t = std::max(1, ch / 12);
        const int yy = py + (ch - t) * (cp - 0x23BA) / 3;
        gfx_->fillRect(px, yy, cw, t, fg);
        return true;
    }
    const uint8_t s = boxSegments(cp);
    if (!s) return false;
    const int t1 = std::max(1, ch / 12);  // light line thickness
    const int gap = std::max(2, ch / 8);  // double-line spacing
    const int cx = px + cw / 2, cy = py + ch / 2;
    auto hline = [&](int x0, int x1, int weight) {
        if (weight == 3) {
            gfx_->fillRect(x0, cy - gap / 2 - t1 / 2, x1 - x0, t1, fg);
            gfx_->fillRect(x0, cy + gap / 2 - t1 / 2, x1 - x0, t1, fg);
        } else {
            int t = weight == 2 ? t1 * 2 + 1 : t1;
            gfx_->fillRect(x0, cy - t / 2, x1 - x0, t, fg);
        }
    };
    auto vline = [&](int y0, int y1, int weight) {
        if (weight == 3) {
            gfx_->fillRect(cx - gap / 2 - t1 / 2, y0, t1, y1 - y0, fg);
            gfx_->fillRect(cx + gap / 2 - t1 / 2, y0, t1, y1 - y0, fg);
        } else {
            int t = weight == 2 ? t1 * 2 + 1 : t1;
            gfx_->fillRect(cx - t / 2, y0, t, y1 - y0, fg);
        }
    };
    const int l = s & 3, r = (s >> 2) & 3, u = (s >> 4) & 3, d = (s >> 6) & 3;
    const int ext = gap / 2 + t1;  // overlap at the centre so corners join
    if (l) hline(px, cx + (u || d ? ext : 0), l);
    if (r) hline(cx - (u || d ? ext : 0), px + cw, r);
    if (u) vline(py, cy + (l || r ? ext : 0), u);
    if (d) vline(cy - (l || r ? ext : 0), py + ch, d);
    return true;
}

void Renderer::drawStatus()
{
    gfx_->fillRect(0, status_y_, width_, height_ - status_y_, kBlack);
    gfx_->setTextColor(kWhite);
    const int ty = status_y_ + (height_ - status_y_ - cell_h_) / 2;
    gfx_->drawString(status_left_.c_str(), cell_w_ / 2, ty);
    const int rw = gfx_->textWidth(status_right_.c_str());
    gfx_->drawString(status_right_.c_str(), width_ - rw - cell_w_ / 2, ty);
}

}  // namespace term
