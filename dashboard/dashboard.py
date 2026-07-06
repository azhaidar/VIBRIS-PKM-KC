import sys
import os
import json
import csv
from collections import deque
from datetime import datetime

try:
    import serial
except ImportError:
    serial = None

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QGridLayout, QStackedWidget, QFrame, QListWidget
)
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg

# ===================== KONFIGURASI =====================
SERIAL_PORT = 'COM5'      # ganti sesuai Device Manager / /dev/ttyUSB0
BAUD_RATE = 115200
BUFFER_LEN = 50           # Dikurangi dari 100 ke 50 agar grafik lebih rapat & jelas di layar kecil
LOG_DIR = "logs"
MACHINE_LABEL = "Electric Fan"

# ===================== PALET WARNA HMI =====================
COL_BG_MAIN = "#1a1c1e"      # Dibuat lebih gelap agar kontras LCD TFT lebih tajam
COL_PANEL = "#2d3135"        # Panel mode gelap agar teks terang menonjol
COL_PANEL_DARK = "#111315"   # Header & Sidebar gelap pekat
COL_ACCENT = "#007acc"       # Biru industri terang untuk indikator touch aktif
COL_ACCENT_HOVER = "#0098ff"
COL_TEXT_LIGHT = "#ffffff"
COL_TEXT_MUTED = "#aaaaaa"
COL_TEXT_DARK = "#1c1c1c"
COL_OK = "#28a745"
COL_WARN = "#ffc107"
COL_BAD = "#dc3545"

STATUS_COLOR = {"Normal": COL_OK, "Waspada": COL_WARN, "Bahaya": COL_BAD}


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HMI - Condition Monitoring")
        
        # Kunci ukuran mutlak agar PAS & tidak terpotong di layar TFT 480x320
        self.setFixedSize(480, 320)
        self.setStyleSheet(f"background-color: {COL_BG_MAIN}; color: {COL_TEXT_LIGHT};")

        os.makedirs(LOG_DIR, exist_ok=True)

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)  # Margin dipersempit agar memaksimalkan ruang layar
        root.setSpacing(4)

        # ================= HEADER BAR =================
        root.addWidget(self._build_header())

        # ================= MAIN BODY Layout =================
        # Layout diubah: Stack konten di ATAS, Menu Navigasi di BAWAH agar mudah disentuh jempol
        self.left_stack = self._build_left_stack()
        root.addWidget(self.left_stack, 1)

        root.addWidget(self._build_bottom_navigation())

        # ===== BUFFER DATA GRAFIK =====
        self.data_vib = deque([0] * BUFFER_LEN, maxlen=BUFFER_LEN)
        self.data_sound = deque([0] * BUFFER_LEN, maxlen=BUFFER_LEN)
        self.data_temp = deque([0] * BUFFER_LEN, maxlen=BUFFER_LEN)
        self.data_current = deque([0] * BUFFER_LEN, maxlen=BUFFER_LEN)

        # ===== STATE TERBARU =====
        self.latest = {"rms_v": 0, "rms_a": 0, "cur": 0, "temp": 0,
                        "rpm": 0, "d2": 0, "status": "UNKNOWN"}

        # ===== RECORDING =====
        self.recording = False
        self.csv_file = None
        self.csv_writer = None
        self.csv_filename = None

        # ===== SERIAL =====
        self.ser = None
        if serial is not None:
            try:
                self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
                print("[INFO] Serial connected")
            except Exception as e:
                print(f"[WARNING] Serial gagal: {e}")
        
        self._set_connection_indicator(self.ser is not None)

        # ===== TIMERS =====
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(200)

        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        # Tampilkan mode default
        self.set_mode(0)

    # ================================================================
    #  BAGIAN PEMBANGUN UI (DIOPTIMALKAN UNTUK 480x320)
    # ================================================================
    def _build_header(self):
        header = QFrame()
        header.setStyleSheet(f"background-color: {COL_PANEL_DARK}; border-radius: 4px; max-height: 28px;")
        h = QHBoxLayout(header)
        h.setContentsMargins(8, 2, 8, 2)

        title = QLabel(f"VIBRIS HMI | {MACHINE_LABEL}")
        title.setStyleSheet(f"color: {COL_TEXT_LIGHT}; font-size: 11px; font-weight: bold;")
        h.addWidget(title)
        h.addStretch()

        self.clock_label = QLabel("--:--:--")
        self.clock_label.setStyleSheet(f"color: {COL_TEXT_MUTED}; font-size: 10px;")
        h.addWidget(self.clock_label)

        h.addSpacing(10)

        self.conn_dot = QLabel("●")
        self.conn_dot.setStyleSheet(f"color: {COL_BAD}; font-size: 12px;")
        h.addWidget(self.conn_dot)
        
        self.conn_text = QLabel("OFFLINE")
        self.conn_text.setStyleSheet(f"color: {COL_TEXT_LIGHT}; font-size: 10px; font-weight: bold;")
        h.addWidget(self.conn_text)

        return header

    def _build_left_stack(self):
        stack = QStackedWidget()
        stack.setStyleSheet(f"background-color: {COL_PANEL}; border-radius: 4px;")
        stack.addWidget(self._page_raw())         # index 0
        stack.addWidget(self._page_recording())   # index 1
        stack.addWidget(self._page_processed())   # index 2
        stack.addWidget(self._page_summary())     # index 3
        return stack

    def _page_raw(self):
        page = QWidget()
        grid = QGridLayout(page)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(4)
        self.graphs = []
        
        titles = ["Vibration (m/s²)", "Sound", "Temp (°C)", "Current (A)"]
        pens = ['r', 'y', '#ff8c00', 'c']
        
        for i in range(4):
            graph = pg.PlotWidget()
            graph.setBackground('#000000')
            # Sembunyikan label sumbu untuk menghemat space yang sangat sempit di TFT 320p
            graph.getAxis('left').setStyle(showValues=False)
            graph.getAxis('bottom').setStyle(showValues=False)
            graph.setTitle(titles[i], color="#ffffff", size="8pt")
            graph.showGrid(x=True, y=True, alpha=0.2)
            
            curve = graph.plot(pen=pg.mkPen(pens[i], width=1.5))
            self.graphs.append((graph, curve))
            grid.addWidget(graph, i // 2, i % 2)
        return page

    def _page_recording(self):
        page = QWidget()
        layout = QHBoxLayout(page)  # Menggunakan split horizontal agar pas di rasio 480x320
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        left_side = QVBoxLayout()
        rec_title = QLabel("RECORDING LOGS")
        rec_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COL_TEXT_LIGHT};")
        left_side.addWidget(rec_title)

        self.rec_status_label = QLabel("● IDLE")
        self.rec_status_label.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {COL_BAD};")
        left_side.addWidget(self.rec_status_label)

        self.rec_toggle_btn = QPushButton("START RECORD")
        self.rec_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COL_ACCENT}; color: white; font-weight: bold;
                padding: 8px; font-size: 11px; border-radius: 4px; min-height: 35px;
            }}
            QPushButton:hover {{ background-color: {COL_ACCENT_HOVER}; }}
        """)
        self.rec_toggle_btn.clicked.connect(self.toggle_recording)
        left_side.addWidget(self.rec_toggle_btn)
        left_side.addStretch()
        
        layout.addLayout(left_side, 1)

        right_side = QVBoxLayout()
        right_side.addWidget(QLabel("History Files:", styleSheet="font-size: 10px; color: #ccc;"))
        self.rec_list = QListWidget()
        self.rec_list.setStyleSheet(f"background-color: #1a1c1e; color: white; font-size: 9px; border-radius: 4px;")
        right_side.addWidget(self.rec_list)
        
        layout.addLayout(right_side, 1)
        self._refresh_log_list()
        return page

    def _page_processed(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)

        header = QLabel("STATISTICAL SELF-BASELINE ( TinyML )")
        header.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COL_TEXT_MUTED};")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Panel Nilai Utama dibuat besar dan sangat kontras
        self.proc_rpm_big = QLabel("RPM: --")
        self.proc_rpm_big.setStyleSheet(f"font-size: 28px; font-weight: bold; color: #00aaff;")
        self.proc_rpm_big.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.proc_rpm_big)

        self.proc_d2_big = QLabel("D²: --")
        self.proc_d2_big.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COL_TEXT_LIGHT};")
        self.proc_d2_big.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.proc_d2_big)

        self.proc_threshold = QLabel("Limit Normal D² < 9.49  |  Bahaya > 13.28")
        self.proc_threshold.setStyleSheet("font-size: 10px; color: #ffaa00;")
        self.proc_threshold.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.proc_threshold)

        return page

    def _page_summary(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignCenter)

        self.sum_status_big = QLabel("STATUS: UNKNOWN")
        self.sum_status_big.setStyleSheet("font-size: 26px; font-weight: bold; color: white;")
        self.sum_status_big.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sum_status_big)

        self.sum_detail = QLabel("Menunggu sinkronisasi data sensor...")
        self.sum_detail.setStyleSheet(f"font-size: 11px; color: {COL_TEXT_LIGHT};")
        self.sum_detail.setAlignment(Qt.AlignCenter)
        self.sum_detail.setWordWrap(True)
        layout.addWidget(self.sum_detail)

        return page

    def _build_bottom_navigation(self):
        # Dipindah ke bagian bawah (Bottom Bar Layout) untuk menyesuaikan rasio layar lebar 3:2 TFT
        nav_frame = QFrame()
        nav_frame.setStyleSheet(f"background-color: {COL_PANEL_DARK}; border-radius: 4px; max-height: 55px;")
        nav = QHBoxLayout(nav_frame)
        nav.setContentsMargins(4, 4, 4, 4)
        nav.setSpacing(4)

        self.mode_buttons = []
        labels = ["Raw\nPlot", "Log\nRecord", "Process\nTinyML", "System\nSummary"]
        
        for i, label in enumerate(labels):
            btn = QPushButton(label)
            # Dibuat tinggi minimum 45px agar finger-friendly di layar sentuh resistif 3.5"
            btn.setMinimumHeight(45) 
            btn.clicked.connect(lambda _, idx=i: self.set_mode(idx))
            nav.addWidget(btn)
            self.mode_buttons.append(btn)

        return nav_frame

    # ================================================================
    #  NAVIGASI & HIGHLIGHT TOMBOL INTERAKTIF
    # ================================================================
    def set_mode(self, index):
        self.left_stack.setCurrentIndex(index)
        self._highlight_active_button(index)

        if index == 0:
            self._render_raw()
        elif index == 1:
            self._refresh_log_list()
        elif index == 2:
            self._render_processed()
        elif index == 3:
            self._render_summary()

    def _highlight_active_button(self, active_index):
        for i, btn in enumerate(self.mode_buttons):
            if i == active_index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COL_ACCENT};
                        color: white; font-size: 10px; font-weight: bold;
                        border: 2px solid #00aaff; border-radius: 4px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #3a3f44; color: {COL_TEXT_LIGHT};
                        font-size: 10px; border: 1px solid #54595e; border-radius: 4px;
                    }}
                """)

    def _render_raw(self):
        pass

    def _render_processed(self):
        self.proc_rpm_big.setText(f"RPM: {self.latest['rpm']:.1f}")
        self.proc_d2_big.setText(f"D²: {self.latest['d2']:.2f}")

    def _render_summary(self):
        status = self.latest['status']
        color = STATUS_COLOR.get(status, COL_TEXT_LIGHT)
        self.sum_status_big.setText(f"STATUS: {status}")
        self.sum_status_big.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color};")
        
        if status == "Normal":
            self.sum_detail.setText(f"Mesin stabil pada {self.latest['rpm']:.1f} RPM.\nJarak Mahalanobis D² aman ({self.latest['d2']:.2f}).")
        elif status == "Waspada":
            self.sum_detail.setText(f"Deteksi deviasi awal! D² meningkat ke {self.latest['d2']:.2f}.\nPeriksa komponen bearing segera.")
        elif status == "Bahaya":
            self.sum_detail.setText(f"ANOMALI KRITIS! D² = {self.latest['d2']:.2f}.\nMatikan mesin untuk mencegah kerusakan fatal.")
        else:
            self.sum_detail.setText(f"Menghubungkan ke core analitik mesin...")

    # ================================================================
    #  SERIAL DATA PARSING
    # ================================================================
    def _set_connection_indicator(self, connected):
        if connected:
            self.conn_dot.setStyleSheet(f"color: {COL_OK}; font-size: 12px;")
            self.conn_text.setText("ONLINE")
            self.conn_text.setStyleSheet(f"color: {COL_OK}; font-size: 10px; font-weight: bold;")
        else:
            self.conn_dot.setStyleSheet(f"color: {COL_BAD}; font-size: 12px;")
            self.conn_text.setText("OFFLINE")
            self.conn_text.setStyleSheet(f"color: {COL_BAD}; font-size: 10px; font-weight: bold;")

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    def update_all(self):
        if self.ser is None:
            return
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode(errors='ignore').strip()
                if not line.startswith("{"):
                    return
                data = json.loads(line)
                self._set_connection_indicator(True)
            else:
                return
        except Exception as e:
            return

        self.latest = {
            "rms_v": data.get("rms_v", 0),
            "rms_a": data.get("rms_a", 0),
            "cur": data.get("cur", 0),
            "temp": data.get("temp", 0),
            "rpm": data.get("rpm", 0),
            "d2": data.get("d2", 0),
            "status": data.get("status", "UNKNOWN"),
        }

        self.data_vib.append(self.latest["rms_v"])
        self.data_sound.append(self.latest["rms_a"])
        self.data_temp.append(self.latest["temp"])
        self.data_current.append(self.latest["cur"])

        buffers = [self.data_vib, self.data_sound, self.data_temp, self.data_current]
        for (graph, curve), buf in zip(self.graphs, buffers):
            curve.setData(list(buf))

        # Refresh halaman aktif real-time
        active = self.left_stack.currentIndex()
        if active == 2:
            self._render_processed()
        elif active == 3:
            self._render_summary()

        if self.recording and self.csv_writer:
            self.csv_writer.writerow([
                datetime.now().isoformat(),
                self.latest["rms_v"], self.latest["rms_a"], self.latest["cur"],
                self.latest["temp"], self.latest["rpm"], self.latest["d2"],
                self.latest["status"]
            ])
            self.csv_file.flush()

    # ================================================================
    #  LOG LOGGING MANAGEMENT
    # ================================================================
    def toggle_recording(self):
        if not self.recording:
            filename = os.path.join(LOG_DIR, f"rec_{datetime.now().strftime('%m%d_%H%M%S')}.csv")
            self.csv_file = open(filename, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(['timestamp', 'rms_v', 'rms_a', 'cur', 'temp', 'rpm', 'd2', 'status'])
            self.csv_filename = filename
            self.recording = True
            self.rec_status_label.setText(f"● LOGGING...")
            self.rec_status_label.setStyleSheet(f"font-size:10px; font-weight:bold; color:{COL_OK};")
            self.rec_toggle_btn.setText("STOP RECORD")
            self.rec_toggle_btn.setStyleSheet(f"background-color: {COL_BAD}; color: white; font-weight: bold; min-height: 35px; border-radius: 4px;")
        else:
            self.recording = False
            if self.csv_file:
                self.csv_file.close()
            self.rec_status_label.setText(f"● SAVED")
            self.rec_status_label.setStyleSheet(f"font-size:10px; font-weight:bold; color:{COL_TEXT_MUTED};")
            self.rec_toggle_btn.setText("START RECORD")
            self.rec_toggle_btn.setStyleSheet(f"background-color: {COL_ACCENT}; color: white; font-weight: bold; min-height: 35px; border-radius: 4px;")
            self._refresh_log_list()

    def _refresh_log_list(self):
        if not hasattr(self, "rec_list"):
            return
        self.rec_list.clear()
        if os.path.isdir(LOG_DIR):
            for f in sorted(os.listdir(LOG_DIR), reverse=True):
                if f.endswith(".csv"):
                    self.rec_list.addItem(f)

    def closeEvent(self, event):
        if self.csv_file:
            self.csv_file.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Tips Layar Sentuh LCD TFT Resistif SPI Raspberry Pi:
    # Buka baris di bawah ini jika ingin menyembunyikan cursor panah mouse saat dijalankan tanpa mouse/keyboard
    # app.setOverrideCursor(Qt.BlankCursor)
    
    win = Dashboard()
    win.show()
    sys.exit(app.exec_())
