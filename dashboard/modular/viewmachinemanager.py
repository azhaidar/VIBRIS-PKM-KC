# viewmachinemanager.py
# Overlay INTERNAL (bukan QDialog/window terpisah) untuk pilih, tambah,
# hapus mesin aktif. Grid 3 kolom. State awal: hanya 1 mesin default,
# list preset jenis mesin diambil dari config.MACHINE_PRESETS. Tombol
# "+Tambah" ganti grid ke mode pilih preset, tombol "Selesai" kembali
# atau tutup overlay (balik ke main.py via on_close callback).

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QPushButton,
                              QLabel, QHBoxLayout, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt
import config
import styles


class ViewMachineManager(QWidget):
    """Overlay internal (bukan window terpisah) untuk pilih/hapus/tambah mesin."""

    def __init__(self, machines, on_select, on_close):
        super().__init__()
        self.machines = machines
        self.on_select = on_select
        self.on_close = on_close
        self.showing_presets = False

        self.setStyleSheet(f"background-color:{config.COL_BG_MAIN};")

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        header = QHBoxLayout()
        self.title_label = QLabel("Kelola Mesin")
        self.title_label.setStyleSheet(f"color:{config.COL_TEXT_LIGHT}; font-weight:bold; font-size:11px;")
        header.addWidget(self.title_label)
        header.addStretch()

        close_btn = QPushButton("Selesai")
        close_btn.setStyleSheet(f"background-color:{config.COL_ACCENT}; color:white; font-size:9px; padding:3px 8px;")
        close_btn.clicked.connect(self._handle_close)
        header.addWidget(close_btn)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(6)
        scroll.setWidget(self.grid_container)
        root.addWidget(scroll, 1)

        self._render_machine_grid()

    def _handle_close(self):
        if self.showing_presets:
            self.showing_presets = False
            self._render_machine_grid()
        else:
            self.on_close()

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _render_machine_grid(self):
        self.title_label.setText("Kelola Mesin")
        self._clear_grid()
        cols = 3
        for i, m in enumerate(self.machines):
            card = self._build_machine_card(m)
            self.grid_layout.addWidget(card, i // cols, i % cols)

        add_card = QPushButton("+ Tambah")
        add_card.setFixedHeight(70)
        add_card.setStyleSheet(styles.machine_card_style())
        add_card.clicked.connect(self._show_presets)
        idx = len(self.machines)
        self.grid_layout.addWidget(add_card, idx // cols, idx % cols)

    def _build_machine_card(self, machine):
        card = QWidget()
        card.setFixedHeight(70)
        card.setStyleSheet(styles.machine_card_style())
        lay = QVBoxLayout(card)
        lay.setContentsMargins(4, 4, 4, 4)

        lbl = QPushButton(machine["label"])
        lbl.setStyleSheet(f"border:none; color:{config.COL_TEXT_DARK}; font-size:9px; font-weight:bold; text-align:left;")
        lbl.clicked.connect(lambda _, m=machine: self.on_select(m))
        lay.addWidget(lbl)

        del_btn = QPushButton("Hapus")
        del_btn.setStyleSheet(f"background-color:{config.COL_BAD}; color:white; font-size:8px; padding:2px;")
        del_btn.clicked.connect(lambda _, m=machine: self._confirm_delete(m))
        lay.addWidget(del_btn)
        return card

    def _confirm_delete(self, machine):
        if len(self.machines) <= 1:
            QMessageBox.warning(self, "Tidak Bisa Dihapus", "Minimal harus ada satu mesin aktif.")
            return
        reply = QMessageBox.question(
            self, "Konfirmasi Hapus",
            f"Hapus mesin '{machine['label']}'? Riwayat log terkait tetap tersimpan.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.machines.remove(machine)
            self._render_machine_grid()

    def _show_presets(self):
        self.showing_presets = True
        self.title_label.setText("Pilih Jenis Mesin")
        self._clear_grid()
        cols = 3
        for i, preset in enumerate(config.MACHINE_PRESETS):
            btn = QPushButton(preset["label"])
            btn.setFixedHeight(70)
            btn.setStyleSheet(styles.machine_card_style())
            btn.clicked.connect(lambda _, p=preset: self._add_machine(p))
            self.grid_layout.addWidget(btn, i // cols, i % cols)

    def _add_machine(self, preset):
        new_machine = dict(preset)
        new_machine["id"] = f"{preset['id']}_{len(self.machines)}"
        self.machines.append(new_machine)
        self.showing_presets = False
        self._render_machine_grid()