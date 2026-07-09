
# config.py
# Satu-satunya sumber konstanta: warna tema, port serial, path folder
# log, daftar preset mesin, daftar tag rekaman. Semua file lain WAJIB
# import warna/konstanta dari sini, jangan hardcode warna di file lain.
# Kalau mau ganti tema/port/preset mesin, cukup edit di sini sajaya.

import os

SERIAL_PORT = 'COM5'
BAUD_RATE = 115200
BUFFER_LEN = 100
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
FEATURE_STALENESS_MS = 2000

COL_BG_MAIN = "#c9d6e2"
COL_HEADER = "#f5c518"
COL_PANEL = "#0fa3a3"
COL_PANEL_LIGHT = "#e8f7f7"
COL_PANEL_DARK = "#1c1e22"
COL_STATUSBAR = "#111315"
COL_TEXT_LIGHT = "#f2f2f2"
COL_TEXT_DARK = "#1c1c1c"
COL_OK = "#2e7d32"
COL_WARN = "#e08e00"
COL_BAD = "#bdb3b3"
COL_ACCENT = "#2a6f97"

STATUS_COLOR = {"Normal": COL_OK, "Waspada": COL_WARN, "Bahaya": COL_BAD, "UNKNOWN": COL_TEXT_DARK}

MACHINE_PRESETS = [
    {"id": "motor_induksi_1f", "label": "Motor Induksi 1 Fasa"},
    {"id": "motor_induksi_3f", "label": "Motor Induksi 3 Fasa Async"},
    {"id": "blower", "label": "Blower Industri"},
    {"id": "kompresor", "label": "Kompresor"},
]

RECORD_TAGS = ["Before", "After", "Test", "Baseline"]

DEFAULT_MACHINE = {"id": "kipas_default", "label": "Kipas Angin"}