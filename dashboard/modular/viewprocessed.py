import os
import csv
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QListWidget, QListWidgetItem, QScrollArea)
from PyQt5.QtCore import Qt
import pyqtgraph as pg

import config
import styles


class ViewProcessed(QWidget):
    def __init__(self):
        super().__init__()
        self.rows = []

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # ---------------- HEAD: nama file ----------------
        self.title_label = QLabel("Processed — (belum ada file dipilih)")
        self.title_label.setStyleSheet(f"color:{config.COL_TEXT_LIGHT}; font-size:9px; font-weight:bold;")
        self.title_label.setWordWrap(True)
        root.addWidget(self.title_label)

        # ---------------- GRAFIK RPM & D2 ----------------
        graphs_row = QHBoxLayout()

        self.rpm_graph = pg.PlotWidget()
        self.rpm_graph.setBackground('#0d1f1a')
        self.rpm_graph.setTitle("RPM Estimasi", color="#dddddd", size="7pt")
        self.rpm_graph.showGrid(x=True, y=True, alpha=0.2)
        self.rpm_curve = self.rpm_graph.plot(pen=pg.mkPen('#4fd1ff', width=1.5))
        graphs_row.addWidget(self.rpm_graph)

        self.d2_graph = pg.PlotWidget()
        self.d2_graph.setBackground('#0d1f1a')
        self.d2_graph.setTitle("Mahalanobis D²", color="#dddddd", size="7pt")
        self.d2_graph.showGrid(x=True, y=True, alpha=0.2)
        self.d2_curve = self.d2_graph.plot(pen=pg.mkPen('#ff6b6b', width=1.5))
        self.d2_line_95 = pg.InfiniteLine(pos=9.49, angle=0, pen=pg.mkPen('#e08e00', style=Qt.DashLine))
        self.d2_line_99 = pg.InfiniteLine(pos=13.28, angle=0, pen=pg.mkPen('#c62828', style=Qt.DashLine))
        self.d2_graph.addItem(self.d2_line_95)
        self.d2_graph.addItem(self.d2_line_99)
        graphs_row.addWidget(self.d2_graph)

        root.addLayout(graphs_row, 2)

        # ---------------- TIMELINE KEJADIAN ----------------
        timeline_label = QLabel("Timeline Kejadian Anomali:")
        timeline_label.setStyleSheet(f"color:{config.COL_TEXT_LIGHT}; font-size:8px; font-weight:bold;")
        root.addWidget(timeline_label)

        self.timeline_list = QListWidget()
        self.timeline_list.setFixedHeight(60)
        self.timeline_list.setStyleSheet("background-color:white; color:black; font-size:8px;")
        root.addWidget(self.timeline_list)

        # ---------------- RINGKASAN ----------------
        self.summary_label = QLabel("Ringkasan: —")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(styles.value_box_style() + f"color:{config.COL_TEXT_DARK}; font-size:8px;")
        root.addWidget(self.summary_label)

    # ---------------- LOAD FILE ----------------
    def load_file(self, filepath):
        self.rows = []
        try:
            with open(filepath, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.rows.append(row)
        except Exception as e:
            self.title_label.setText(f"Processed — GAGAL BACA FILE ({e})")
            return

        self.title_label.setText(f"Processed — {os.path.basename(filepath)}")

        if not self.rows:
            self.summary_label.setText("Ringkasan: berkas kosong, tidak ada data untuk diproses.")
            self.rpm_curve.setData([])
            self.d2_curve.setData([])
            self.timeline_list.clear()
            return

        self._render_graphs()
        self._render_timeline()
        self._render_summary()

    def _safe_float(self, row, key, default=0.0):
        try:
            return float(row.get(key, default))
        except (ValueError, TypeError):
            return default

    def _render_graphs(self):
        rpm_series = [self._safe_float(r, "rpm") for r in self.rows]
        d2_series = [self._safe_float(r, "d2") for r in self.rows]
        self.rpm_curve.setData(rpm_series)
        self.d2_curve.setData(d2_series)

    def _render_timeline(self):
        self.timeline_list.clear()
        prev_status = "Normal"
        for r in self.rows:
            status = r.get("status", "Normal")
            ts = r.get("timestamp", "")
            d2 = self._safe_float(r, "d2")
            event_flag = r.get("event", "")

            # transisi masuk ke Waspada/Bahaya
            if status in ("Waspada", "Bahaya") and status != prev_status:
                item = QListWidgetItem(f"[{ts}] → {status} (D²={d2:.2f})")
                if status == "Bahaya":
                    item.setForeground(Qt.red)
                else:
                    item.setForeground(Qt.darkYellow)
                self.timeline_list.addItem(item)

            # kejadian manual ditandai operator
            if event_flag == "MARK":
                item = QListWidgetItem(f"[{ts}] ● Ditandai operator")
                self.timeline_list.addItem(item)

            prev_status = status

        if self.timeline_list.count() == 0:
            self.timeline_list.addItem("Tidak ada kejadian anomali sepanjang sesi ini.")

    def _render_summary(self):
        d2_values = [self._safe_float(r, "d2") for r in self.rows]
        rpm_values = [self._safe_float(r, "rpm") for r in self.rows]
        statuses = [r.get("status", "Normal") for r in self.rows]

        max_d2 = max(d2_values) if d2_values else 0
        avg_rpm = sum(rpm_values) / len(rpm_values) if rpm_values else 0

        worst_status = "Normal"
        if "Bahaya" in statuses:
            worst_status = "Bahaya"
        elif "Waspada" in statuses:
            worst_status = "Waspada"

        n_waspada = statuses.count("Waspada")
        n_bahaya = statuses.count("Bahaya")

        flatline_warn = ""
        sensor_keys = {"rms_v": "Getaran", "rms_a": "Suara", "cur": "Arus", "temp": "Suhu"}
        for key, name in sensor_keys.items():
            vals = [self._safe_float(r, key) for r in self.rows]
            if vals and max(vals) - min(vals) < 1e-4:
                flatline_warn += f" ⚠ {name} tidak berubah sama sekali (cek sensor)."

        text = (f"Sesi: {len(self.rows)} sample | RPM rata-rata: {avg_rpm:.1f} | "
                f"D² max: {max_d2:.2f} | Kondisi terparah: {worst_status} | "
                f"Waspada: {n_waspada}x, Bahaya: {n_bahaya}x.{flatline_warn}")
        self.summary_label.setText(text)