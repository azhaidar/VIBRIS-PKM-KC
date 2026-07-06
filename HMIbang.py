import sys
import random
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer
import pyqtgraph as pg


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deteksi Dini Mesin Rotasi")
        self.setGeometry(100, 100, 1000, 600)

        # Background abu-abu
        self.setStyleSheet("background-color: #cfcfcf;")

        main_layout = QHBoxLayout()

        # ================= LEFT (GRAPH) =================
        left_layout = QGridLayout()

        self.graphs = []
        titles = ["Vibration", "Sound", "Temperature", "Current"]

        for i in range(4):
            graph = pg.PlotWidget()
            graph.setBackground('k')
            graph.setTitle(titles[i])
            graph.showGrid(x=True, y=True)
            curve = graph.plot(pen='r')

            self.graphs.append((graph, curve))
            left_layout.addWidget(graph, i // 2, i % 2)

        main_layout.addLayout(left_layout, 2)

        # ================= RIGHT PANEL =================
        right_layout = QVBoxLayout()

        # ===== TITLE =====
        title = QLabel("Save 1 : Electric Fan")
        title.setStyleSheet("font-size:16px; font-weight:bold;")
        right_layout.addWidget(title)

        # ===== NILAI (VALUES) =====
        self.values = QLabel()
        self.values.setStyleSheet("font-size:14px;")
        right_layout.addWidget(self.values)

        # ===== MENU INFO =====
        self.content = QLabel("Pilih Menu...")
        self.content.setStyleSheet("font-size:13px;")
        right_layout.addWidget(self.content)

        # ===== BUTTON (2x2 DI BAWAH) =====
        btn_layout = QGridLayout()

        self.btn_rec = QPushButton("Recording & Saves")
        self.btn_raw = QPushButton("Raw Reading")
        self.btn_proc = QPushButton("Processed Reading")
        self.btn_sum = QPushButton("Summary")

        buttons = [self.btn_rec, self.btn_raw,
                   self.btn_proc, self.btn_sum]

        for i, btn in enumerate(buttons):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4a6fa5;
                    color: white;
                    padding: 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #ffb347;
                }
            """)
            btn_layout.addWidget(btn, i // 2, i % 2)

        right_layout.addLayout(btn_layout)

        main_layout.addLayout(right_layout, 1)

        self.setLayout(main_layout)

        # ===== BUTTON ACTION =====
        self.btn_rec.clicked.connect(self.show_recording)
        self.btn_raw.clicked.connect(self.show_raw)
        self.btn_proc.clicked.connect(self.show_processed)
        self.btn_sum.clicked.connect(self.show_summary)

        # ===== DATA =====
        self.data = [0]*100

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(200)

    # ===== UPDATE =====
    def update_all(self):
        self.data = self.data[1:] + [random.randint(0, 100)]

        # update graph
        for graph, curve in self.graphs:
            curve.setData(self.data)

        # update nilai kanan
        vib = round(random.uniform(0.01, 0.05), 3)
        sound = random.randint(50, 70)
        temp = random.randint(80, 120)
        current = round(random.uniform(0.1, 0.5), 2)

        self.values.setText(f"""
Vibration : {vib} m/s²
Sound     : {sound} Hz
Temp      : {temp} °C
Current   : {current} A
        """)

    # ===== MENU =====
    def show_recording(self):
        self.content.setText("""
[Recording & Saves]

Save 1 : Electric Fan
Save 2 : Servo Motor
Save 3 : Drill

History:
- 30/12/2025
- 01/01/2026
        """)

    def show_raw(self):
        self.content.setText("""
[Raw Reading]

Menampilkan data sensor mentah realtime
        """)

    def show_processed(self):
        self.content.setText("""
[Processed Reading]

Data dibandingkan dengan nilai normal
        """)

    def show_summary(self):
        self.content.setText("""
[Summary]

Vibration : WARNING
Sound     : NORMAL
Temp      : HIGH
Current   : NORMAL
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Dashboard()
    win.show()
    sys.exit(app.exec_())