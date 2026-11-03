#include "vt.h"

#include <algorithm>
#include <cstdarg>
#include <cstdio>

namespace term {

int charWidth(uint32_t cp)
{
    if (cp == 0) return 0;
    if (cp < 0x20 || (cp >= 0x7f && cp < 0xa0)) return 0;
    // Combining marks and zero-width characters
    if ((cp >= 0x0300 && cp <= 0x036F) || (cp >= 0x1AB0 && cp <= 0x1AFF) || (cp >= 0x1DC0 && cp <= 0x1DFF) ||
        (cp >= 0x20D0 && cp <= 0x20FF) || (cp >= 0xFE20 && cp <= 0xFE2F) || (cp >= 0x200B && cp <= 0x200F) ||
        cp == 0xFE0E || cp == 0xFE0F || cp == 0x3099 || cp == 0x309A) {
        return 0;
    }
    // East Asian Wide / Fullwidth
    if ((cp >= 0x1100 && cp <= 0x115F) || cp == 0x2329 || cp == 0x232A || (cp >= 0x2E80 && cp <= 0x303E) ||
        (cp >= 0x3041 && cp <= 0x33FF) || (cp >= 0x3400 && cp <= 0x4DBF) || (cp >= 0x4E00 && cp <= 0x9FFF) ||
        (cp >= 0xA000 && cp <= 0xA4CF) || (cp >= 0xAC00 && cp <= 0xD7A3) || (cp >= 0xF900 && cp <= 0xFAFF) ||
        (cp >= 0xFE30 && cp <= 0xFE4F) || (cp >= 0xFF00 && cp <= 0xFF60) || (cp >= 0xFFE0 && cp <= 0xFFE6) ||
        (cp >= 0x1F300 && cp <= 0x1F64F) || (cp >= 0x1F900 && cp <= 0x1F9FF) || (cp >= 0x20000 && cp <= 0x3FFFD)) {
        return 2;
    }
    return 1;
}

namespace {

// DEC Special Graphics for 0x5f..0x7e
constexpr uint16_t kDecGraphics[32] = {
    0x0020, 0x25C6, 0x2592, 0x2409, 0x240C, 0x240D, 0x240A, 0x00B0, 0x00B1, 0x2424, 0x240B,
    0x2518, 0x2510, 0x250C, 0x2514, 0x253C, 0x23BA, 0x23BB, 0x2500, 0x23BC, 0x23BD, 0x251C,
    0x2524, 0x2534, 0x252C, 0x2502, 0x2264, 0x2265, 0x03C0, 0x2260, 0x00A3, 0x00B7,
};

bool darkRgb(int r, int g, int b) { return (299 * r + 587 * g + 114 * b) / 1000 < 110; }

bool darkIndex(int idx)
{
    static const uint8_t basic[16][3] = {
        {0, 0, 0},       {205, 0, 0},   {0, 205, 0},   {205, 205, 0}, {0, 0, 238},     {205, 0, 205},
        {0, 205, 205},   {229, 229, 229}, {127, 127, 127}, {255, 0, 0}, {0, 255, 0},     {255, 255, 0},
        {92, 92, 255},   {255, 0, 255}, {0, 255, 255}, {255, 255, 255},
    };
    if (idx < 0) return false;
    if (idx < 16) return darkRgb(basic[idx][0], basic[idx][1], basic[idx][2]);
    if (idx < 232) {
        static const int lv[6] = {0, 95, 135, 175, 215, 255};
        int i = idx - 16;
        return darkRgb(lv[i / 36], lv[(i / 6) % 6], lv[i % 6]);
    }
    if (idx < 256) {
        int v = 8 + 10 * (idx - 232);
        return darkRgb(v, v, v);
    }
    return false;
}

}  // namespace

Vt::Vt(int cols, int rows)
{
    mtx_ = xSemaphoreCreateRecursiveMutex();
    resize(cols, rows);
    reset();
}

Vt::~Vt()
{
    if (mtx_) vSemaphoreDelete(mtx_);
}

void Vt::lock() const { xSemaphoreTakeRecursive(mtx_, portMAX_DELAY); }
void Vt::unlock() const { xSemaphoreGiveRecursive(mtx_); }

std::string Vt::title() const
{
    lock();
    std::string t = title_;
    unlock();
    return t;
}

void Vt::resize(int cols, int rows)
{
    lock();
    cols = std::max(cols, 2);
    rows = std::max(rows, 2);
    // When the screen gets shorter, drop lines from the top so the cursor stays visible.
    const int shift = buf_.empty() ? 0 : std::max(0, cy_ - (rows - 1));
    auto remap = [&](const std::vector<Cell>& src) {
        std::vector<Cell> dst(static_cast<size_t>(cols) * rows, Cell{' ', 0, 1});
        if (src.size() == static_cast<size_t>(cols_) * rows_ && !src.empty()) {
            const int cw = std::min(cols, cols_);
            for (int y = 0; y < rows && y + shift < rows_; ++y) {
                for (int x = 0; x < cw; ++x) dst[y * cols + x] = src[(y + shift) * cols_ + x];
                if (dst[y * cols + cw - 1].width == 2) dst[y * cols + cw - 1] = Cell{' ', 0, 1};
            }
        }
        return dst;
    };
    std::vector<Cell> nb = remap(buf_);
    if (alt_active_) main_saved_ = remap(main_saved_);
    buf_.swap(nb);
    cy_ -= shift;
    cols_ = cols;
    rows_ = rows;
    cx_ = std::clamp(cx_, 0, cols_ - 1);
    cy_ = std::clamp(cy_, 0, rows_ - 1);
    top_ = 0;
    bot_ = rows_ - 1;
    wrap_pending_ = false;
    tabs_.assign(cols_, 0);
    for (int x = 8; x < cols_; x += 8) tabs_[x] = 1;
    dirty_.assign(rows_, 1);
    changed_ = true;
    unlock();
}

void Vt::reset()
{
    lock();
    alt_active_ = false;
    main_saved_.clear();
    std::fill(buf_.begin(), buf_.end(), Cell{' ', 0, 1});
    cx_ = cy_ = 0;
    wrap_pending_ = false;
    attr_ = 0;
    dark_bg_ = false;
    top_ = 0;
    bot_ = rows_ - 1;
    autowrap_ = true;
    insert_ = origin_ = app_cursor_ = lnm_ = false;
    cursor_visible_ = true;
    g0_graphics_ = g1_graphics_ = false;
    gl_ = 0;
    saved_main_ = saved_alt_ = Saved{};
    tabs_.assign(cols_, 0);
    for (int x = 8; x < cols_; x += 8) tabs_[x] = 1;
    st_ = St::Ground;
    u8_need_ = 0;
    title_.clear();
    dirty_.assign(rows_, 1);
    changed_ = true;
    unlock();
}

void Vt::printf(const char* fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (n > 0) feed(buf, std::min<size_t>(n, sizeof(buf) - 1));
}

void Vt::markAllDirty()
{
    lock();
    std::fill(dirty_.begin(), dirty_.end(), 1);
    unlock();
}

bool Vt::collectDirty(std::vector<uint8_t>& rows)
{
    if (cx_ != last_cx_ || cy_ != last_cy_ || cursor_visible_ != last_cv_) {
        dirtyRow(last_cy_);
        dirtyRow(cy_);
        last_cx_ = cx_;
        last_cy_ = cy_;
        last_cv_ = cursor_visible_;
    }
    rows = dirty_;
    bool any = std::find(dirty_.begin(), dirty_.end(), 1) != dirty_.end();
    std::fill(dirty_.begin(), dirty_.end(), 0);
    return any;
}

void Vt::feed(const char* data, size_t len)
{
    lock();
    for (size_t i = 0; i < len; ++i) {
        uint8_t b = static_cast<uint8_t>(data[i]);

        // String states (OSC / DCS / APC ...) swallow bytes until BEL or ST
        if (st_ == St::Osc || st_ == St::Str) {
            if (b == 0x07) {
                if (st_ == St::Osc) oscDispatch();
                st_ = St::Ground;
            } else if (b == 0x1b) {
                st_ = (st_ == St::Osc) ? St::OscEsc : St::StrEsc;
            } else if (st_ == St::Osc && osc_.size() < 256) {
                osc_.push_back(static_cast<char>(b));
            }
            continue;
        }
        if (st_ == St::OscEsc || st_ == St::StrEsc) {
            if (st_ == St::OscEsc) oscDispatch();
            st_ = St::Ground;
            if (b == '\\') continue;
            st_ = St::Esc;
            escDispatch(b);
            continue;
        }

        if (u8_need_ > 0) {
            if ((b & 0xC0) == 0x80) {
                u8_cp_ = (u8_cp_ << 6) | (b & 0x3F);
                if (--u8_need_ == 0) print(u8_cp_);
                continue;
            }
            u8_need_ = 0;
            print(0xFFFD);
        }
        if (b < 0x80) {
            byte(b);
        } else {
            if (st_ != St::Ground) st_ = St::Ground;  // 8-bit data aborts a sequence
            if ((b & 0xE0) == 0xC0) {
                u8_cp_ = b & 0x1F;
                u8_need_ = 1;
            } else if ((b & 0xF0) == 0xE0) {
                u8_cp_ = b & 0x0F;
                u8_need_ = 2;
            } else if ((b & 0xF8) == 0xF0) {
                u8_cp_ = b & 0x07;
                u8_need_ = 3;
            } else {
                print(0xFFFD);
            }
        }
    }
    bool changed = changed_;
    changed_ = false;
    std::string replies;
    replies.swap(replies_);
    unlock();
    if (!replies.empty() && on_reply) on_reply(replies.data(), replies.size());
    if (changed && on_change) on_change();
}

void Vt::byte(uint8_t c)
{
    if (c < 0x20 || c == 0x7f) {
        control(c);
        return;
    }
    switch (st_) {
        case St::Ground:
            print(c);
            break;
        case St::Esc:
            escDispatch(c);
            break;
        case St::EscInter:
            if (esc_inter_ == '(') g0_graphics_ = (c == '0');
            else if (esc_inter_ == ')') g1_graphics_ = (c == '0');
            st_ = St::Ground;
            break;
        case St::Csi:
            if (c >= '0' && c <= '9') {
                if (nparams_ == 0) nparams_ = 1;
                int& p = params_[nparams_ - 1];
                if (p < 10000) p = p * 10 + (c - '0');
                param_open_ = true;
            } else if (c == ';' || c == ':') {
                if (nparams_ == 0) nparams_ = 1;
                if (nparams_ < kMaxParams) params_[nparams_++] = 0;
            } else if (c >= '<' && c <= '?') {
                priv_ = c;
            } else if (c >= 0x20 && c <= 0x2F) {
                inter_ = c;
            } else if (c >= 0x40 && c <= 0x7E) {
                st_ = St::Ground;
                csiDispatch(c);
            }
            break;
        default:
            st_ = St::Ground;
            break;
    }
}

void Vt::control(uint8_t c)
{
    switch (c) {
        case 0x07:
            if (on_bell) on_bell();
            break;
        case 0x08:
            if (cx_ > 0) cx_--;
            wrap_pending_ = false;
            changed_ = true;
            break;
        case 0x09:
            tab(1);
            break;
        case 0x0A:
        case 0x0B:
        case 0x0C:
            lineFeed();
            if (lnm_) cx_ = 0;
            break;
        case 0x0D:
            cx_ = 0;
            wrap_pending_ = false;
            changed_ = true;
            break;
        case 0x0E:
            gl_ = 1;
            break;
        case 0x0F:
            gl_ = 0;
            break;
        case 0x18:
        case 0x1A:
            st_ = St::Ground;
            break;
        case 0x1B:
            st_ = St::Esc;
            esc_inter_ = 0;
            break;
        default:
            break;
    }
}

void Vt::fixWide(int x, int y)
{
    Cell& c = at(x, y);
    if (c.width == 0 && x > 0) {
        at(x - 1, y) = Cell{' ', at(x - 1, y).attr, 1};
    } else if (c.width == 2 && x + 1 < cols_) {
        at(x + 1, y) = Cell{' ', at(x + 1, y).attr, 1};
    }
}

void Vt::print(uint32_t cp)
{
    if (cp >= 0x5f && cp <= 0x7e && (gl_ == 0 ? g0_graphics_ : g1_graphics_)) cp = kDecGraphics[cp - 0x5f];
    int w = charWidth(cp);
    if (w == 0) return;

    if (wrap_pending_) {
        if (autowrap_) {
            cx_ = 0;
            lineFeed();
        }
        wrap_pending_ = false;
    }
    if (w == 2 && cx_ >= cols_ - 1) {
        if (!autowrap_) return;
        fixWide(cx_, cy_);
        at(cx_, cy_) = blank();
        dirtyRow(cy_);
        cx_ = 0;
        lineFeed();
    }
    if (insert_) insertChars(w);

    uint8_t a = attr_ | (dark_bg_ ? kAttrDarkBg : 0);
    fixWide(cx_, cy_);
    if (w == 2) fixWide(cx_ + 1, cy_);
    at(cx_, cy_) = Cell{cp, a, static_cast<uint8_t>(w == 2 ? 2 : 1)};
    if (w == 2) at(cx_ + 1, cy_) = Cell{' ', a, 0};
    dirtyRow(cy_);
    last_char_ = cp;
    cx_ += w;
    if (cx_ >= cols_) {
        cx_ = cols_ - 1;
        wrap_pending_ = true;
    }
    changed_ = true;
}

void Vt::lineFeed()
{
    if (cy_ == bot_) {
        scrollUp(top_, bot_, 1);
    } else if (cy_ < rows_ - 1) {
        cy_++;
    }
    wrap_pending_ = false;
    changed_ = true;
}

void Vt::reverseIndex()
{
    if (cy_ == top_) {
        scrollDown(top_, bot_, 1);
    } else if (cy_ > 0) {
        cy_--;
    }
    wrap_pending_ = false;
    changed_ = true;
}

void Vt::scrollUp(int top, int bot, int n)
{
    n = std::min(n, bot - top + 1);
    if (n <= 0) return;
    auto first = buf_.begin() + top * cols_;
    std::move(first + n * cols_, buf_.begin() + (bot + 1) * cols_, first);
    std::fill(buf_.begin() + (bot - n + 1) * cols_, buf_.begin() + (bot + 1) * cols_, blank());
    dirtyRange(top, bot);
    changed_ = true;
}

void Vt::scrollDown(int top, int bot, int n)
{
    n = std::min(n, bot - top + 1);
    if (n <= 0) return;
    auto first = buf_.begin() + top * cols_;
    auto last = buf_.begin() + (bot + 1) * cols_;
    std::move_backward(first, last - n * cols_, last);
    std::fill(first, first + n * cols_, blank());
    dirtyRange(top, bot);
    changed_ = true;
}

void Vt::eraseCells(int y, int x0, int x1)
{
    x0 = std::max(0, x0);
    x1 = std::min(cols_ - 1, x1);
    if (x0 > x1) return;
    fixWide(x0, y);
    fixWide(x1, y);
    for (int x = x0; x <= x1; ++x) at(x, y) = blank();
    dirtyRow(y);
    changed_ = true;
}

void Vt::eraseDisplay(int mode)
{
    if (mode == 0) {
        eraseCells(cy_, cx_, cols_ - 1);
        for (int y = cy_ + 1; y < rows_; ++y) eraseCells(y, 0, cols_ - 1);
    } else if (mode == 1) {
        for (int y = 0; y < cy_; ++y) eraseCells(y, 0, cols_ - 1);
        eraseCells(cy_, 0, cx_);
    } else {
        for (int y = 0; y < rows_; ++y) eraseCells(y, 0, cols_ - 1);
    }
}

void Vt::eraseLine(int mode)
{
    if (mode == 0) eraseCells(cy_, cx_, cols_ - 1);
    else if (mode == 1) eraseCells(cy_, 0, cx_);
    else eraseCells(cy_, 0, cols_ - 1);
}

void Vt::insertChars(int n)
{
    n = std::min(n, cols_ - cx_);
    if (n <= 0) return;
    fixWide(cx_, cy_);
    auto row = buf_.begin() + cy_ * cols_;
    std::move_backward(row + cx_, row + cols_ - n, row + cols_);
    std::fill(row + cx_, row + cx_ + n, blank());
    if (at(cols_ - 1, cy_).width == 2) at(cols_ - 1, cy_) = blank();
    dirtyRow(cy_);
    changed_ = true;
}

void Vt::deleteChars(int n)
{
    n = std::min(n, cols_ - cx_);
    if (n <= 0) return;
    fixWide(cx_, cy_);
    fixWide(std::min(cols_ - 1, cx_ + n - 1), cy_);
    auto row = buf_.begin() + cy_ * cols_;
    std::move(row + cx_ + n, row + cols_, row + cx_);
    std::fill(row + cols_ - n, row + cols_, blank());
    if (at(cx_, cy_).width == 0) at(cx_, cy_) = blank();
    dirtyRow(cy_);
    changed_ = true;
}

void Vt::setCursor(int x, int y)
{
    if (origin_) {
        y = std::clamp(y + top_, top_, bot_);
    } else {
        y = std::clamp(y, 0, rows_ - 1);
    }
    cx_ = std::clamp(x, 0, cols_ - 1);
    cy_ = y;
    wrap_pending_ = false;
    changed_ = true;
}

void Vt::cursorUp(int n)
{
    int limit = (cy_ >= top_) ? top_ : 0;
    cy_ = std::max(limit, cy_ - n);
    wrap_pending_ = false;
    changed_ = true;
}

void Vt::cursorDown(int n)
{
    int limit = (cy_ <= bot_) ? bot_ : rows_ - 1;
    cy_ = std::min(limit, cy_ + n);
    wrap_pending_ = false;
    changed_ = true;
}

void Vt::tab(int n)
{
    while (n-- > 0 && cx_ < cols_ - 1) {
        do {
            cx_++;
        } while (cx_ < cols_ - 1 && !tabs_[cx_]);
    }
    wrap_pending_ = false;
    changed_ = true;
}

void Vt::backTab(int n)
{
    while (n-- > 0 && cx_ > 0) {
        do {
            cx_--;
        } while (cx_ > 0 && !tabs_[cx_]);
    }
    wrap_pending_ = false;
    changed_ = true;
}

void Vt::saveCursor()
{
    Saved& s = alt_active_ ? saved_alt_ : saved_main_;
    s.x = cx_;
    s.y = cy_;
    s.attr = attr_;
    s.dark = dark_bg_;
    s.origin = origin_;
    s.g0 = g0_graphics_;
    s.g1 = g1_graphics_;
    s.gl = gl_;
}

void Vt::restoreCursor()
{
    const Saved& s = alt_active_ ? saved_alt_ : saved_main_;
    cx_ = std::clamp(s.x, 0, cols_ - 1);
    cy_ = std::clamp(s.y, 0, rows_ - 1);
    attr_ = s.attr;
    dark_bg_ = s.dark;
    origin_ = s.origin;
    g0_graphics_ = s.g0;
    g1_graphics_ = s.g1;
    gl_ = s.gl;
    wrap_pending_ = false;
    changed_ = true;
}

void Vt::reply(const char* s) { replies_ += s; }

void Vt::setAlt(bool on, bool clear)
{
    if (on == alt_active_) return;
    if (on) {
        main_saved_ = buf_;
        if (clear) std::fill(buf_.begin(), buf_.end(), Cell{' ', 0, 1});
    } else {
        if (main_saved_.size() == buf_.size()) buf_.swap(main_saved_);
        main_saved_.clear();
    }
    alt_active_ = on;
    std::fill(dirty_.begin(), dirty_.end(), 1);
    changed_ = true;
}

void Vt::setPrivateModes(bool on)
{
    int n = std::max(nparams_, 1);
    for (int i = 0; i < n; ++i) {
        switch (param0(i)) {
            case 1: app_cursor_ = on; break;
            case 6:
                origin_ = on;
                setCursor(0, 0);
                break;
            case 7: autowrap_ = on; break;
            case 25:
                cursor_visible_ = on;
                changed_ = true;
                break;
            case 47:
            case 1047:
                setAlt(on, on);
                break;
            case 1048:
                if (on) saveCursor();
                else restoreCursor();
                break;
            case 1049:
                if (on) {
                    saveCursor();
                    setAlt(true, true);
                } else {
                    setAlt(false, false);
                    restoreCursor();
                }
                break;
            default:
                break;  // mouse modes, bracketed paste, blink ... ignored
        }
    }
}

void Vt::sgr()
{
    if (nparams_ == 0) {
        attr_ = 0;
        dark_bg_ = false;
        return;
    }
    for (int i = 0; i < nparams_; ++i) {
        int p = params_[i];
        switch (p) {
            case 0:
                attr_ = 0;
                dark_bg_ = false;
                break;
            case 1: attr_ |= kAttrBold; break;
            case 4: attr_ |= kAttrUnderline; break;
            case 7: attr_ |= kAttrInverse; break;
            case 22: attr_ &= ~kAttrBold; break;
            case 24: attr_ &= ~kAttrUnderline; break;
            case 27: attr_ &= ~kAttrInverse; break;
            case 49: dark_bg_ = false; break;
            case 38:  // extended foreground: skip its arguments
                if (i + 1 < nparams_ && params_[i + 1] == 5) i += 2;
                else if (i + 1 < nparams_ && params_[i + 1] == 2) i += 4;
                break;
            case 48:
                if (i + 2 < nparams_ && params_[i + 1] == 5) {
                    dark_bg_ = darkIndex(params_[i + 2]);
                    i += 2;
                } else if (i + 4 < nparams_ && params_[i + 1] == 2) {
                    dark_bg_ = darkRgb(params_[i + 2], params_[i + 3], params_[i + 4]);
                    i += 4;
                }
                break;
            default:
                if (p >= 40 && p <= 47) dark_bg_ = darkIndex(p - 40);
                else if (p >= 100 && p <= 107) dark_bg_ = darkIndex(p - 100 + 8);
                break;  // foreground colours and other styles are ignored on e-paper
        }
    }
}

void Vt::escDispatch(uint8_t c)
{
    st_ = St::Ground;
    switch (c) {
        case '[':
            st_ = St::Csi;
            nparams_ = 0;
            std::fill(std::begin(params_), std::end(params_), 0);
            param_open_ = false;
            priv_ = inter_ = 0;
            break;
        case ']':
            st_ = St::Osc;
            osc_.clear();
            break;
        case 'P':
        case 'X':
        case '^':
        case '_':
            st_ = St::Str;
            break;
        case '(':
        case ')':
        case '*':
        case '+':
        case '#':
        case '%':
            st_ = St::EscInter;
            esc_inter_ = c;
            break;
        case '7': saveCursor(); break;
        case '8': restoreCursor(); break;
        case 'D': lineFeed(); break;
        case 'E':
            cx_ = 0;
            lineFeed();
            break;
        case 'M': reverseIndex(); break;
        case 'H':
            if (cx_ < cols_) tabs_[cx_] = 1;
            break;
        case 'c': reset(); break;
        default: break;  // keypad modes, ST and others ignored
    }
}

void Vt::oscDispatch()
{
    // "0;title" or "2;title" sets the window title (shown in the status bar)
    if (osc_.size() > 2 && (osc_[0] == '0' || osc_[0] == '2') && osc_[1] == ';') {
        title_ = osc_.substr(2);
        changed_ = true;
    }
    osc_.clear();
}

void Vt::csiDispatch(uint8_t f)
{
    if (inter_ != 0) {
        if (inter_ == '!' && f == 'p') {  // DECSTR soft reset
            attr_ = 0;
            dark_bg_ = false;
            insert_ = origin_ = app_cursor_ = false;
            autowrap_ = cursor_visible_ = true;
            top_ = 0;
            bot_ = rows_ - 1;
            changed_ = true;
        }
        return;
    }
    if (priv_ == '?') {
        if (f == 'h' || f == 'l') setPrivateModes(f == 'h');
        else if (f == 'J') eraseDisplay(param0(0));
        else if (f == 'K') eraseLine(param0(0));
        return;
    }
    if (priv_ == '>') {
        if (f == 'c') reply("\x1b[>0;95;0c");
        return;
    }
    if (priv_) return;

    const int n = param(0, 1);
    switch (f) {
        case '@': insertChars(n); break;
        case 'A': cursorUp(n); break;
        case 'B':
        case 'e': cursorDown(n); break;
        case 'C':
        case 'a':
            cx_ = std::min(cols_ - 1, cx_ + n);
            wrap_pending_ = false;
            changed_ = true;
            break;
        case 'D':
            cx_ = std::max(0, std::min(cx_, cols_ - 1) - n);
            wrap_pending_ = false;
            changed_ = true;
            break;
        case 'E':
            cursorDown(n);
            cx_ = 0;
            break;
        case 'F':
            cursorUp(n);
            cx_ = 0;
            break;
        case 'G':
        case '`':
            cx_ = std::clamp(n - 1, 0, cols_ - 1);
            wrap_pending_ = false;
            changed_ = true;
            break;
        case 'H':
        case 'f': setCursor(param(1, 1) - 1, param(0, 1) - 1); break;
        case 'I': tab(n); break;
        case 'J': eraseDisplay(param0(0)); break;
        case 'K': eraseLine(param0(0)); break;
        case 'L':
            if (cy_ >= top_ && cy_ <= bot_) {
                scrollDown(cy_, bot_, n);
                cx_ = 0;
            }
            break;
        case 'M':
            if (cy_ >= top_ && cy_ <= bot_) {
                scrollUp(cy_, bot_, n);
                cx_ = 0;
            }
            break;
        case 'P': deleteChars(n); break;
        case 'S': scrollUp(top_, bot_, n); break;
        case 'T': scrollDown(top_, bot_, n); break;
        case 'X': eraseCells(cy_, cx_, cx_ + n - 1); break;
        case 'Z': backTab(n); break;
        case 'b':
            for (int i = 0; i < std::min(n, cols_ * rows_); ++i) print(last_char_);
            break;
        case 'c':
            if (param0(0) == 0) reply("\x1b[?1;2c");
            break;
        case 'd': setCursor(cx_, n - 1); break;
        case 'g':
            if (param0(0) == 0 && cx_ < cols_) tabs_[cx_] = 0;
            else if (param0(0) == 3) std::fill(tabs_.begin(), tabs_.end(), 0);
            break;
        case 'h':
        case 'l':
            for (int i = 0; i < std::max(nparams_, 1); ++i) {
                if (param0(i) == 4) insert_ = (f == 'h');
                else if (param0(i) == 20) lnm_ = (f == 'h');
            }
            break;
        case 'm': sgr(); break;
        case 'n':
            if (param0(0) == 5) {
                reply("\x1b[0n");
            } else if (param0(0) == 6) {
                char buf[48];
                int row = origin_ ? cy_ - top_ + 1 : cy_ + 1;
                snprintf(buf, sizeof(buf), "\x1b[%d;%dR", row, cx_ + 1);
                reply(buf);
            }
            break;
        case 'r': {
            int t = param(0, 1) - 1;
            int b = param(1, rows_) - 1;
            if (t < b && b < rows_) {
                top_ = t;
                bot_ = b;
            } else {
                top_ = 0;
                bot_ = rows_ - 1;
            }
            setCursor(0, 0);
            break;
        }
        case 's': saveCursor(); break;
        case 'u': restoreCursor(); break;
        default: break;
    }
}

}  // namespace term
