// A compact VT100/xterm-subset terminal emulator: UTF-8 (incl. East Asian wide glyphs),
// cursor movement, erase, insert/delete, scroll regions, alternate screen, DEC line drawing.
// Colours are not drawn on e-paper; a dark background colour is mapped to inverse video.
#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <functional>
#include <string>
#include <vector>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

namespace term {

enum : uint8_t {
    kAttrBold = 1 << 0,
    kAttrUnderline = 1 << 1,
    kAttrInverse = 1 << 2,
    kAttrDarkBg = 1 << 3,  // explicit dark background colour (drawn inverted)
};

struct Cell {
    uint32_t cp;
    uint8_t attr;
    uint8_t width;  // 1 = normal, 2 = leading half of a wide glyph, 0 = trailing half
};

// Terminal column width of a code point (0, 1 or 2).
int charWidth(uint32_t cp);

class Vt {
public:
    Vt(int cols, int rows);
    ~Vt();
    Vt(const Vt&) = delete;
    Vt& operator=(const Vt&) = delete;

    void resize(int cols, int rows);
    void reset();
    void feed(const char* data, size_t len);
    void puts(const char* s) { feed(s, strlen(s)); }
    void printf(const char* fmt, ...) __attribute__((format(printf, 2, 3)));

    // Read access for the renderer: hold lock() while reading cells.
    void lock() const;
    void unlock() const;
    int cols() const { return cols_; }
    int rows() const { return rows_; }
    const Cell& cell(int x, int y) const { return buf_[y * cols_ + x]; }
    int cursorX() const { return cx_; }
    int cursorY() const { return cy_; }
    bool cursorVisible() const { return cursor_visible_; }
    bool appCursorKeys() const { return app_cursor_; }
    std::string title() const;

    // Rows changed since the last call (including cursor moves). Call with lock() held.
    bool collectDirty(std::vector<uint8_t>& rows);
    void markAllDirty();

    // Device replies (DSR/DA) — invoked after feed() returns, outside the lock.
    std::function<void(const char*, size_t)> on_reply;
    std::function<void()> on_bell;
    std::function<void()> on_change;

private:
    enum class St : uint8_t { Ground, Esc, EscInter, Csi, Osc, OscEsc, Str, StrEsc };
    struct Saved {
        int x = 0, y = 0;
        uint8_t attr = 0;
        bool dark = false, origin = false, g0 = false, g1 = false;
        int gl = 0;
    };

    void byte(uint8_t c);
    void control(uint8_t c);
    void print(uint32_t cp);
    void escDispatch(uint8_t c);
    void csiDispatch(uint8_t final_byte);
    void oscDispatch();
    void sgr();
    void setPrivateModes(bool on);
    void setAlt(bool on, bool clear);

    Cell blank() const { return Cell{' ', static_cast<uint8_t>(dark_bg_ ? kAttrDarkBg : 0), 1}; }
    Cell& at(int x, int y) { return buf_[y * cols_ + x]; }
    void dirtyRow(int y) { if (y >= 0 && y < rows_) dirty_[y] = 1; }
    void dirtyRange(int y0, int y1) { for (int y = y0; y <= y1; ++y) dirtyRow(y); }
    void fixWide(int x, int y);
    void lineFeed();
    void reverseIndex();
    void scrollUp(int top, int bot, int n);
    void scrollDown(int top, int bot, int n);
    void eraseCells(int y, int x0, int x1);
    void eraseDisplay(int mode);
    void eraseLine(int mode);
    void insertChars(int n);
    void deleteChars(int n);
    void setCursor(int x, int y);
    void cursorUp(int n);
    void cursorDown(int n);
    void tab(int n);
    void backTab(int n);
    void saveCursor();
    void restoreCursor();
    void reply(const char* s);
    int param(int i, int def) const { return (i < nparams_ && params_[i] > 0) ? params_[i] : def; }
    int param0(int i) const { return i < nparams_ ? params_[i] : 0; }

    int cols_ = 0, rows_ = 0;
    std::vector<Cell> buf_;
    std::vector<Cell> main_saved_;  // main screen while the alternate screen is active
    bool alt_active_ = false;

    int cx_ = 0, cy_ = 0;
    bool wrap_pending_ = false;
    uint8_t attr_ = 0;
    bool dark_bg_ = false;
    int top_ = 0, bot_ = 0;
    bool autowrap_ = true, insert_ = false, origin_ = false, app_cursor_ = false;
    bool cursor_visible_ = true, lnm_ = false;
    bool g0_graphics_ = false, g1_graphics_ = false;
    int gl_ = 0;
    uint32_t last_char_ = ' ';
    Saved saved_main_, saved_alt_;
    std::vector<uint8_t> tabs_;

    St st_ = St::Ground;
    static constexpr int kMaxParams = 16;
    int params_[kMaxParams] = {};
    int nparams_ = 0;
    bool param_open_ = false;
    uint8_t priv_ = 0, inter_ = 0, esc_inter_ = 0;
    std::string osc_;
    std::string title_;

    uint32_t u8_cp_ = 0;
    int u8_need_ = 0;

    std::vector<uint8_t> dirty_;
    int last_cx_ = -1, last_cy_ = -1;
    bool last_cv_ = false;
    bool changed_ = false;
    std::string replies_;

    SemaphoreHandle_t mtx_ = nullptr;
};

}  // namespace term
