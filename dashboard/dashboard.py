import sys, json, serial, csv
from collections import deque
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
from PyQt5.QtCore import Qt

SERIAL_PORT = 'COM5'   # ganti sesuai Device Manager
BAUD_RATE = 115200
BUFFER_LEN = 100


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deteksi Dini Mesin Rotasi")
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet("background-color: #cfcfcf;")
#fdfdffffffffffffffffffffffffffffffffffffffffffff
        main_layout = QHBoxLayout()

        # ================= LEFT: STACKED PER MODE =================
        self.left_stack = QStackedWidget()

        # --- Halaman Raw: 4 grafik ---
        raw_page = QWidget()
        raw_grid = QGridLayout(raw_page)
        self.graphs = []
        titles = ["Vibration", "Sound", "Temperature", "Current"]
        for i in range(4):
            graph = pg.PlotWidget()
            graph.setBackground('k')
            graph.setTitle(titles[i])
            graph.showGrid(x=True, y=True)
            curve = graph.plot(pen='r')
            self.graphs.append((graph, curve))
            raw_grid.addWidget(graph, i // 2, i % 2)

        # --- Halaman Recording: list riwayat ---
        rec_page = QWidget()
        rec_layout = QVBoxLayout(rec_page)
        rec_title = QLabel("Recording & Saves")
        rec_title.setStyleSheet("font-size:18px; font-weight:bold;")
        rec_layout.addWidget(rec_title)
        self.rec_list_display = QLabel("Belum ada rekaman.")
        self.rec_list_display.setStyleSheet("font-size:13px;")
        rec_layout.addWidget(self.rec_list_display)
        rec_layout.addStretch()

        # --- Halaman Processed: angka RPM+D2 besar ---
        proc_page = QWidget()
        proc_layout = QVBoxLayout(proc_page)
        proc_layout.setAlignment(Qt.AlignCenter)
        self.proc_rpm_big = QLabel("RPM: --")
        self.proc_rpm_big.setStyleSheet("font-size:36px; font-weight:bold;")
        self.proc_rpm_big.setAlignment(Qt.AlignCenter)
        self.proc_d2_big = QLabel("D2: --")
        self.proc_d2_big.setStyleSheet("font-size:28px;")
        self.proc_d2_big.setAlignment(Qt.AlignCenter)
        proc_layout.addWidget(self.proc_rpm_big)
        proc_layout.addWidget(self.proc_d2_big)

        # --- Halaman Summary: status besar ---
        sum_page = QWidget()
        sum_layout = QVBoxLayout(sum_page)
        sum_layout.setAlignment(Qt.AlignCenter)
        self.sum_status_big = QLabel("STATUS: --")
        self.sum_status_big.setStyleSheet("font-size:40px; font-weight:bold;")
        self.sum_status_big.setAlignment(Qt.AlignCenter)
        sum_layout.addWidget(self.sum_status_big)

        self.left_stack.addWidget(raw_page)    # index 0
        self.left_stack.addWidget(rec_page)    # index 1
        self.left_stack.addWidget(proc_page)   # index 2
        self.left_stack.addWidget(sum_page)    # index 3

        main_layout.addWidget(self.left_stack, 2)


        # ================= RIGHT PANEL =================
        right_layout = QVBoxLayout()

        title = QLabel("Save 1 : Electric Fan")
        title.setStyleSheet("font-size:16px; font-weight:bold;")
        right_layout.addWidget(title)

        self.values = QLabel()
        self.values.setStyleSheet("font-size:14px;")
        right_layout.addWidget(self.values)

        self.content = QLabel("Pilih Menu...")
        self.content.setStyleSheet("font-size:13px;")
        self.content.setWordWrap(True)
        right_layout.addWidget(self.content)

        btn_layout = QGridLayout()
        self.btn_rec = QPushButton("Recording & Saves")
        self.btn_raw = QPushButton("Raw Reading")
        self.btn_proc = QPushButton("Processed Reading")
        self.btn_sum = QPushButton("Summary")

        buttons = [self.btn_rec, self.btn_raw, self.btn_proc, self.btn_sum]
        for i, btn in enumerate(buttons):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4a6fa5; color: white;
                    padding: 8px; font-size: 12px;
                }
                QPushButton:hover { background-color: #ffb347; }
            """)
            btn_layout.addWidget(btn, i // 2, i % 2)

        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout, 1)
        self.setLayout(main_layout)

        self.btn_rec.clicked.connect(self.toggle_recording)
        self.btn_raw.clicked.connect(self.show_raw)
        self.btn_proc.clicked.connect(self.show_processed)
        self.btn_sum.clicked.connect(self.show_summary)

        # ===== BUFFER DATA UNTUK GRAFIK (real, bukan random) =====
        self.data_vib = deque([0]*BUFFER_LEN, maxlen=BUFFER_LEN)
        self.data_sound = deque([0]*BUFFER_LEN, maxlen=BUFFER_LEN)
        self.data_temp = deque([0]*BUFFER_LEN, maxlen=BUFFER_LEN)
        self.data_current = deque([0]*BUFFER_LEN, maxlen=BUFFER_LEN)

        # ===== STATE TERBARU (dipakai semua halaman) =====
        self.latest = {"rms_v": 0, "rms_a": 0, "cur": 0, "temp": 0,
                        "rpm": 0, "d2": 0, "status": "UNKNOWN"}

        # ===== RECORDING =====
        self.recording = False
        self.csv_file = None
        self.csv_writer = None

        # ===== SERIAL =====
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print("[INFO] Serial connected")
        except Exception as e:
            self.ser = None
            print(f"[WARNING] Serial gagal: {e}")

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(200)

    # ===== BACA SERIAL + UPDATE SEMUA =====
    def update_all(self):
        if self.ser is None:
            return
        try:
            line = self.ser.readline().decode(errors='ignore').strip()
            if not line.startswith("{"):
                return
            data = json.loads(line)
        except Exception as e:
            print("[PARSE ERROR]", e)
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

        # update buffer grafik
        self.data_vib.append(self.latest["rms_v"])
        self.data_sound.append(self.latest["rms_a"])
        self.data_temp.append(self.latest["temp"])
        self.data_current.append(self.latest["cur"])

        buffers = [self.data_vib, self.data_sound, self.data_temp, self.data_current]
        for (graph, curve), buf in zip(self.graphs, buffers):
            curve.setData(list(buf))

        # update nilai kanan (real, bukan random)
        self.values.setText(
            f"Vibration : {self.latest['rms_v']:.4f} m/s²\n"
            f"Sound     : {self.latest['rms_a']:.1f}\n"
            f"Temp      : {self.latest['temp']:.1f} °C\n"
            f"Current   : {self.latest['cur']:.4f} A\n"
            f"RPM       : {self.latest['rpm']:.1f}\n"
            f"D2        : {self.latest['d2']:.2f}"
        )

        # kalau sedang merekam, tulis ke CSV
        if self.recording and self.csv_writer:
            self.csv_writer.writerow([
                datetime.now().isoformat(),
                self.latest["rms_v"], self.latest["rms_a"], self.latest["cur"],
                self.latest["temp"], self.latest["rpm"], self.latest["d2"],
                self.latest["status"]
            ])
            self.csv_file.flush()

    # ===== RECORDING TOGGLE (klik tombol "Recording & Saves") =====
    def toggle_recording(self):
        if not self.recording:
            filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.csv_file = open(filename, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(['timestamp', 'rms_v', 'rms_a', 'cur', 'temp', 'rpm', 'd2', 'status'])
            self.recording = True
            self.content.setText(f"Sedang merekam ke:\n{filename}")
            self.rec_list_display.setText(f"● MEREKAM\nFile: {filename}")
        else:
            self.recording = False
            if self.csv_file:
                self.csv_file.close()
            self.content.setText("Rekaman disimpan.")
            self.rec_list_display.setText("Rekaman disimpan.")
        self.left_stack.setCurrentIndex(1)

    def show_raw(self):
        self.left_stack.setCurrentIndex(0)
        self.content.setText("[Raw Reading]\nMenampilkan grafik real-time.")

    def show_processed(self):
        self.left_stack.setCurrentIndex(2)
        self.proc_rpm_big.setText(f"RPM: {self.latest['rpm']:.1f}")
        self.proc_d2_big.setText(f"D2: {self.latest['d2']:.2f} (Threshold: 9.49)")
        self.content.setText("[Processed Reading]\nRPM & D2 hasil olahan Mahalanobis.")

    def show_summary(self):
        self.left_stack.setCurrentIndex(3)
        status = self.latest['status']
        self.sum_status_big.setText(f"STATUS: {status}")
        color = {"Normal": "green", "Waspada": "orange", "Bahaya": "red"}.get(status, "black")
        self.sum_status_big.setStyleSheet(f"font-size:40px; font-weight:bold; color:{color};")
        self.content.setText(f"[Summary]\nStatus: {status}")
                
    # ===== MENU LAIN (real data, bukan teks statis) =====
    def show_raw(self):
        self.content.setText(
            "[Raw Reading]\n\n"
            f"Getaran : {self.latest['rms_v']:.4f} m/s²\n"
            f"Suara   : {self.latest['rms_a']:.1f}\n"
            f"Arus    : {self.latest['cur']:.4f} A\n"
            f"Suhu    : {self.latest['temp']:.1f} °C"
        )

    def show_processed(self):
        self.content.setText(
            "[Processed Reading]\n\n"
            f"RPM Estimasi : {self.latest['rpm']:.1f}\n"
            f"Mahalanobis D2 : {self.latest['d2']:.2f}\n"
            f"(Threshold Normal: 9.49 | Bahaya: 13.28)"
        )

    def show_summary(self):
        status = self.latest['status']
        self.content.setText(
            "[Summary]\n\n"
            f"Status Keseluruhan : {status}\n"
            f"RPM : {self.latest['rpm']:.1f}\n"
            f"D2  : {self.latest['d2']:.2f}"
        )
        color = {"Normal": "green", "Waspada": "orange", "Bahaya": "red"}.get(status, "black")
        self.content.setStyleSheet(f"font-size:13px; color:{color}; font-weight:bold;")

    def closeEvent(self, event):
        if self.csv_file:
            self.csv_file.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Dashboard()
    win.show()
    sys.exit(app.exec_())