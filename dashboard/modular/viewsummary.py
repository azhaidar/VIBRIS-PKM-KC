from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
import config
import styles


class ViewSummary(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        self.box = QWidget()
        self.box.setStyleSheet(styles.status_box_style("UNKNOWN"))
        box_layout = QVBoxLayout(self.box)
        box_layout.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel("STATUS: --")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"font-size:22px; font-weight:bold; color:{config.COL_TEXT_DARK};")
        box_layout.addWidget(self.status_label)

        self.detail_label = QLabel("RPM: --   D²: --")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setStyleSheet(f"font-size:11px; font-family:Consolas; color:{config.COL_TEXT_DARK};")
        box_layout.addWidget(self.detail_label)

        layout.addWidget(self.box)

    def update_data(self, latest):
        status = latest.get("status", "UNKNOWN")
        self.box.setStyleSheet(styles.status_box_style(status))
        self.status_label.setText(f"STATUS: {status}")
        self.detail_label.setText(f"RPM: {latest.get('rpm', 0):.1f}   D²: {latest.get('d2', 0):.2f}")