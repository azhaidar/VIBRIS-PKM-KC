# styles.py
# Kumpulan fungsi stylesheet Qt (return string CSS-like) dipakai semua
# view. Pisah dari config.py karena isinya bukan nilai mentah, tapi
# kombinasi/format style siap pakai. Kalau mau ubah tampilan visual
# tanpa ubah logic widget, cukup edit fungsi di sini.

# styles.py
import config as cfg


def header_style():
    return f"background-color:{cfg.COL_HEADER}; border-bottom:2px solid #b89a0a;"


def bottom_nav_style():
    return f"background-color:{cfg.COL_STATUSBAR};"


def nav_btn_style(active):
    if active:
        return (f"background-color:{cfg.COL_HEADER}; color:{cfg.COL_TEXT_DARK}; "
                f"font-weight:bold; font-size:11px; border-radius:3px; border:none;")
    return (f"background-color:#2a4c4c; color:{cfg.COL_TEXT_LIGHT}; "
            f"font-weight:bold; font-size:11px; border-radius:3px; border:none;")


def panel_style():
    return f"background-color:{cfg.COL_PANEL}; border-radius:4px;"


def status_box_style(status):
    color = cfg.STATUS_COLOR.get(status, cfg.COL_TEXT_DARK)
    return f"background-color:white; border:3px solid {color}; border-radius:6px;"


def debug_panel_style():
    return f"background-color:#0b0f10; color:#38f27a; font-family:'Consolas',monospace; font-size:8px;"


def value_box_style():
    return "background-color:#c9f2c9; border-radius:4px; padding:4px;"


def machine_card_style(active=False):
    border = f"2px solid {cfg.COL_ACCENT}" if active else "1px solid #999"
    return f"background-color:white; border:{border}; border-radius:5px;"