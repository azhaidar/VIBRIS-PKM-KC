# viewraw.py
# Halaman "Raw": kiri = 4 grafik mini live, kanan = 6 kartu digit
# (Vib, Snd, Cur, Temp, RPM, D2) tersusun vertikal (nama di atas,
# nilai di bawah). Tiap kartu berwarna aksen sesuai sensornya kalau
# nilainya masih berubah (aktif), berubah abu-abu kalau nilai diam
# beberapa siklus (dicurigai sensor mati/tidak terbaca). Angka besar
# diformat singkat (K/M/B/T) supaya kartu tidak pernah rusak layoutnya.
# Dipanggil oleh main.py lewat update_data(latest_dict).

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from collections import deque
import config

GRAPH_TITLES = ["Vibration", "Sound", "Current", "Temp"]
GRAPH_KEYS = ["rms_v", "rms_a", "cur", "temp"]
GRAPH_PENS = ['#d64545', '#c9a227', '#2a6f97', '#e08e00']

# 6 kartu: label tampil, key data, warna aksen saat aktif
CARD_DEFS = [
    ("VIBRASI", "rms_v", "#d64545"),
    ("SUARA",   "rms_a", "#c9a227"),
    ("ARUS",    "cur",   "#2a6f97"),
    ("SUHU",    "temp",  "#e08e00"),
    ("RPM",     "rpm",   "#6a4fd6"),
    ("D²",      "d2",    "#2e7d32"),
]

STALE_LIMIT = 6  # jumlah siklus nilai diam sebelum dianggap tidak aktif


def format_compact(value):
    """Format angka supaya tetap ringkas walau nilainya sangat besar."""
    try:
        v = float(value)
    except (ValueError, TypeError):
        return "--"
    av = abs(v)
    if av >= 1e12:
        return f"{v/1e12:.2f}T"
    if av >= 1e9:
        return f"{v/1e9:.2f}B"
    if av >= 1e6:
        return f"{v/1e6:.2f}M"
    if av >= 1e3:
        return f"{v/1e3:.2f}K"
    return f"{v:.3f}"


class StatCard(QWidget):
    def __init__(self, label, accent_color):
        super().__init__()
        self.accent_color = accent_color
        self.setFixedHeight(64)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        self.name_label = QLabel(label)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet(f"color:{config.COL_TEXT_LIGHT}; font-size:8px; font-weight:bold; border:none;")
        layout.addWidget(self.name_label)

        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(f"color:{config.COL_TEXT_LIGHT}; font-size:12px; font-weight:bold; font-family:Consolas; border:none;")
        layout.addWidget(self.value_label)

        self._set_active(False)

    def set_value(self, value, active):
        self.value_label.setText(format_compact(value))
        self._set_active(active)

    def _set_active(self, active):
        bg = self.accent_color if active else "#8a8a8a"
        self.setStyleSheet(f"background-color:{bg}; border-radius:5px;")


class ViewRaw(QWidget):
    def __init__(self):
        super().__init__()
        root = QHBoxLayout(self)
        root.setContentsMargins(3, 3, 3, 3)
        root.setSpacing(4)

        # ---------------- KIRI: 4 grafik mini ----------------
        graph_col = QGridLayout()
        graph_col.setSpacing(3)
        self.buffers = [deque([0] * config.BUFFER_LEN, maxlen=config.BUFFER_LEN) for _ in range(4)]
        self.plots = []

        for i in range(4):
            graph = pg.PlotWidget()
            graph.setMaximumHeight(120)
            graph.setBackground(config.COL_PANEL_LIGHT)
            graph.setTitle(GRAPH_TITLES[i], color=config.COL_TEXT_DARK, size="7pt")
            graph.showGrid(x=True, y=True, alpha=0.15)
            graph.getAxis('left').setStyle(showValues=True)
            graph.getAxis('bottom').setStyle(showValues=False)
            curve = graph.plot(pen=pg.mkPen(GRAPH_PENS[i], width=1.5))
            self.plots.append(curve)
            graph_col.addWidget(graph, i // 2, i % 2)

        graph_widget = QWidget()
        graph_widget.setLayout(graph_col)
        root.addWidget(graph_widget, 3)

        # ---------------- KANAN: 6 kartu digit ----------------
        card_grid = QGridLayout()
        card_grid.setSpacing(4)
        self.cards = {}
        self.last_values = {}
        self.stale_counter = {}

        for idx, (label, key, color) in enumerate(CARD_DEFS):
            card = StatCard(label, color)
            self.cards[key] = card
            self.last_values[key] = None
            self.stale_counter[key] = 0
            card_grid.addWidget(card, idx // 2, idx % 2)

        card_widget = QWidget()
        card_widget.setLayout(card_grid)
        root.addWidget(card_widget, 2)

    def update_data(self, latest):
        for i, key in enumerate(GRAPH_KEYS):
            self.buffers[i].append(latest.get(key, 0))
            self.plots[i].setData(list(self.buffers[i]))

        for label, key, color in CARD_DEFS:
            value = latest.get(key, 0)
            prev = self.last_values[key]

            if prev is not None and value == prev:
                self.stale_counter[key] += 1
            else:
                self.stale_counter[key] = 0
            self.last_values[key] = value

            is_active = self.stale_counter[key] < STALE_LIMIT
            self.cards[key].set_value(value, is_active)