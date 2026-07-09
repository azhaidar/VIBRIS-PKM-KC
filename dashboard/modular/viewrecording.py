import os
import csv
from datetime import datetime
from collections import deque

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                              QPushButton, QComboBox, QLabel, QMessageBox, QSlider)
from PyQt5.QtCore import Qt
import pyqtgraph as pg

import config
import styles

TITLES = ["Vibration", "Sound", "Current", "Temp"]
PENS = ['r', 'y', 'c', '#ff8c00']
KEYS = ["rms_v", "rms_a", "cur", "temp"]
CSV_FIELDS = ["seq", "timestamp", "machine", "rms_v", "rms_a", "cur", "temp", "rpm", "d2", "status", "event"]


class ViewRecording(QWidget):
    def __init__(self, open_processed_cb):
        super().__init__()
        self.open_processed_cb = open_processed_cb

        self.current_machine_label = "Kipas Angin"
        self.recording = False
        self.csv_file = None
        self.csv_writer = None
        self.csv_path = None
        self.seq = 0
        self.mark_next_event = False

        # buffer untuk live plotting
        self.live_buffers = [deque(maxlen=config.BUFFER_LEN) for _ in range(4)]

        # data playback yang dimuat penuh dari file
        self.playback_data = None  # dict of lists per key
        self.selected_playback_path = None

        root = QVBoxLayout(self)
        root.setContentsMargins(3, 3, 3, 3)
        root.setSpacing(3)

        # ---------------- HEAD ----------------
        self.head_label = QLabel("Recording & Playback — Standby")
        self.head_label.setStyleSheet(f"color:{config.COL_TEXT_LIGHT}; font-size:9px; font-weight:bold;")
        root.addWidget(self.head_label)

        # ---------------- CONTENT (split) ----------------
        content = QHBoxLayout()
        content.setSpacing(3)

        # kiri: list file
        self.file_list = QListWidget()
        self.file_list.setFixedWidth(120)
        self.file_list.setStyleSheet("background-color:white; color:black; font-size:8px;")
        self.file_list.itemClicked.connect(self._on_file_selected)
        content.addWidget(self.file_list)

        # kanan: area grafik (kosong sampai ada data)
        self.graph_container = QVBoxLayout()
        self.graph_widgets = []
        self.graph_curves = []
        self._build_graphs()

        self.scrub_line = None
        self.scrub_slider = QSlider(Qt.Horizontal)
        self.scrub_slider.setEnabled(False)
        self.scrub_slider.valueChanged.connect(self._on_scrub)

        right_col = QVBoxLayout()
        self.graph_holder = QWidget()
        self.graph_holder.setLayout(self.graph_container)
        right_col.addWidget(self.graph_holder, 1)
        right_col.addWidget(self.scrub_slider)

        content.addLayout(right_col, 1)
        root.addLayout(content, 1)

        self._set_graphs_visible(False)

        # tombol Processed di bawah grafik-nilai
        self.processed_btn = QPushButton("Lihat Processed →")
        self.processed_btn.setEnabled(False)
        self.processed_btn.setStyleSheet(f"background-color:{config.COL_ACCENT}; color:white; font-size:9px; padding:3px;")
        self.processed_btn.clicked.connect(self._open_processed)
        root.addWidget(self.processed_btn)

        # ---------------- BOTTOM ----------------
        bottom = QHBoxLayout()
        bottom.setSpacing(3)

        self.tag_combo = QComboBox()
        self.tag_combo.addItems(config.RECORD_TAGS)
        self.tag_combo.setStyleSheet("font-size:8px;")
        bottom.addWidget(self.tag_combo)

        self.record_btn = QPushButton("● REKAM")
        self.record_btn.setStyleSheet(f"background-color:{config.COL_OK}; color:white; font-size:8px; padding:3px;")
        self.record_btn.clicked.connect(self._toggle_record)
        bottom.addWidget(self.record_btn)

        self.mark_btn = QPushButton("Tandai")
        self.mark_btn.setEnabled(False)
        self.mark_btn.setStyleSheet(f"background-color:{config.COL_WARN}; color:white; font-size:8px; padding:3px;")
        self.mark_btn.clicked.connect(self._mark_event)
        bottom.addWidget(self.mark_btn)

        self.delete_btn = QPushButton("Hapus")
        self.delete_btn.setStyleSheet(f"background-color:{config.COL_BAD}; color:white; font-size:8px; padding:3px;")
        self.delete_btn.clicked.connect(self._delete_selected)
        bottom.addWidget(self.delete_btn)

        root.addLayout(bottom)

        self._refresh_file_list()

    # ---------------- GRAPH BUILD ----------------
    def _build_graphs(self):
        grid_row = QHBoxLayout()
        grid_row2 = QHBoxLayout()
        for i in range(4):
            graph = pg.PlotWidget()
            graph.setBackground('#0d1f1a')
            graph.setTitle(TITLES[i], color="#dddddd", size="7pt")
            graph.showGrid(x=True, y=True, alpha=0.2)
            graph.getAxis('left').setStyle(showValues=True)
            curve = graph.plot(pen=pg.mkPen(PENS[i], width=1.5))
            self.graph_widgets.append(graph)
            self.graph_curves.append(curve)
            (grid_row if i < 2 else grid_row2).addWidget(graph)
        self.graph_container.addLayout(grid_row)
        self.graph_container.addLayout(grid_row2)

    def _set_graphs_visible(self, visible):
        self.graph_holder.setVisible(visible)
        self.scrub_slider.setVisible(visible)

    # ---------------- MACHINE CONTEXT ----------------
    def set_machine_label(self, label):
        self.current_machine_label = label

    # ---------------- LIVE RECORDING ----------------
    def _toggle_record(self):
        if not self.recording:
            self._start_record()
        else:
            self._stop_record()

    def _start_record(self):
        clean_name = self.current_machine_label.replace(" ", "")
        tag = self.tag_combo.currentText()
        now = datetime.now()
        fname = f"{clean_name}_{tag}_{now.strftime('%m%d')}_{now.strftime('%H%M%S')}.csv"
        self.csv_path = os.path.join(config.LOG_DIR, fname)
        self.csv_file = open(self.csv_path, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(CSV_FIELDS)
        self.seq = 0
        self.recording = True

        for b in self.live_buffers:
            b.clear()
        self.playback_data = None
        self._set_graphs_visible(True)
        self.scrub_slider.setEnabled(False)

        self.record_btn.setText("■ BERHENTI")
        self.record_btn.setStyleSheet(f"background-color:{config.COL_BAD}; color:white; font-size:8px; padding:3px;")
        self.mark_btn.setEnabled(True)
        self.head_label.setText(f"Recording & Playback — ● Merekam: {fname}")

    def _stop_record(self):
        self.recording = False
        if self.csv_file:
            self.csv_file.close()
        self.record_btn.setText("● REKAM")
        self.record_btn.setStyleSheet(f"background-color:{config.COL_OK}; color:white; font-size:8px; padding:3px;")
        self.mark_btn.setEnabled(False)
        self.head_label.setText("Recording & Playback — Standby")
        self._refresh_file_list()
        self.processed_btn.setEnabled(True)
        self.selected_playback_path = self.csv_path

    def _mark_event(self):
        self.mark_next_event = True

    def update_live(self, latest):
        if not self.recording:
            return
        self.seq += 1
        event_flag = "MARK" if self.mark_next_event else ""
        self.mark_next_event = False

        self.csv_writer.writerow([
            self.seq, datetime.now().isoformat(), self.current_machine_label,
            latest.get("rms_v", 0), latest.get("rms_a", 0), latest.get("cur", 0),
            latest.get("temp", 0), latest.get("rpm", 0), latest.get("d2", 0),
            latest.get("status", "UNKNOWN"), event_flag
        ])
        self.csv_file.flush()

        for i, key in enumerate(KEYS):
            self.live_buffers[i].append(latest.get(key, 0))
            self.graph_curves[i].setData(list(self.live_buffers[i]))

    # ---------------- FILE LIST ----------------
    def _refresh_file_list(self):
        self.file_list.clear()
        if os.path.isdir(config.LOG_DIR):
            for f in sorted(os.listdir(config.LOG_DIR), reverse=True):
                if f.endswith(".csv"):
                    self.file_list.addItem(f)

    def _delete_selected(self):
        item = self.file_list.currentItem()
        if not item:
            return
        if self.recording and self.csv_path and os.path.basename(self.csv_path) == item.text():
            QMessageBox.warning(self, "Tidak Bisa Dihapus", "File sedang direkam, hentikan rekaman dulu.")
            return
        reply = QMessageBox.question(
            self, "Konfirmasi Hapus", f"Hapus berkas '{item.text()}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            path = os.path.join(config.LOG_DIR, item.text())
            try:
                os.remove(path)
            except Exception as e:
                QMessageBox.critical(self, "Gagal Hapus", str(e))
            self._refresh_file_list()
            self._set_graphs_visible(False)
            self.processed_btn.setEnabled(False)

    # ---------------- PLAYBACK ----------------
    def _on_file_selected(self, item):
        if self.recording:
            return
        path = os.path.join(config.LOG_DIR, item.text())
        self._load_playback(path)

    def _load_playback(self, path):
        data = {k: [] for k in KEYS}
        try:
            with open(path, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for k in KEYS:
                        try:
                            data[k].append(float(row.get(k, 0)))
                        except (ValueError, TypeError):
                            data[k].append(0.0)
        except Exception as e:
            QMessageBox.critical(self, "Gagal Baca File", str(e))
            return

        if not data[KEYS[0]]:
            QMessageBox.information(self, "Kosong", "Berkas ini tidak berisi data.")
            return

        self.playback_data = data
        self.selected_playback_path = path
        self._set_graphs_visible(True)

        for i, key in enumerate(KEYS):
            self.graph_curves[i].setData(data[key])

        n = len(data[KEYS[0]])
        self.scrub_slider.setEnabled(True)
        self.scrub_slider.setMinimum(0)
        self.scrub_slider.setMaximum(n - 1)
        self.scrub_slider.setValue(n - 1)

        for gw in self.graph_widgets:
            if self.scrub_line is None:
                pass
        self._ensure_scrub_lines()

        self.head_label.setText(f"Recording & Playback — {os.path.basename(path)}")
        self.processed_btn.setEnabled(True)

    def _ensure_scrub_lines(self):
        self.scrub_lines = []
        for gw in self.graph_widgets:
            line = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('#ffffff', width=1))
            gw.addItem(line)
            self.scrub_lines.append(line)

    def _on_scrub(self, value):
        if not self.playback_data:
            return
        if hasattr(self, "scrub_lines"):
            for line in self.scrub_lines:
                line.setPos(value)

    def _open_processed(self):
        if self.selected_playback_path:
            self.open_processed_cb(self.selected_playback_path)