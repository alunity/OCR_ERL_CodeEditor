from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QPlainTextEdit, QGraphicsDropShadowEffect
from ui.components import InputTextBox, Terminal
from ui.styles import GLOBAL_STYLES
import interpreter


# Subclass QMainWindow to customize your application's main window
class CodeEditor(QWidget):
    TEMP_FILENAME: str = "t.txt"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.textbox_layout = QHBoxLayout()
        self.text_edit = InputTextBox(self)
        self.textbox_layout.addWidget(self.text_edit)
        self.layout.addLayout(self.textbox_layout)
        self.terminal = Terminal()
        self.textbox_layout.addWidget(self.terminal)
        self.btn_layout = QHBoxLayout()
        self.btn_layout.addStretch(0)
        self.run_btn = QPushButton(self)
        self.run_btn.setFixedWidth(50)
        self.run_btn.setFixedHeight(50)
        self.run_btn.clicked.connect(self.on_run_btn_click)
        self.run_btn.setIcon(QtGui.QIcon("ui\play.png"))
        self.terminal.on_run_start = lambda: self.run_btn.setIcon(QtGui.QIcon("ui\stop.png"))
        self.terminal.on_run_end = lambda: self.run_btn.setIcon(QtGui.QIcon("ui\play.png"))
        self.set_shadow(self.run_btn)
        self.set_shadow(self.text_edit)
        self.set_shadow(self.terminal)
        self.btn_layout.addWidget(self.run_btn)
        self.btn_layout.addStretch()
        self.layout.addLayout(self.btn_layout)
        self.setStyleSheet(GLOBAL_STYLES)

    def set_shadow(self, widget: QWidget):
        drop_shadow = QGraphicsDropShadowEffect()
        drop_shadow.setColor(QtGui.QColor("#ddd"))
        drop_shadow.setXOffset(0)
        drop_shadow.setYOffset(5)
        drop_shadow.setBlurRadius(15)
        widget.setGraphicsEffect(drop_shadow)

    def on_run_btn_click(self):
        if not self.terminal.is_running:
            self.run_code_input()
        else:
            self.terminal.stop_running()

    def run_code_input(self):
        with open(CodeEditor.TEMP_FILENAME, "w") as file:
            file.write(self.text_edit.text)
        self.terminal.clear()
        self.terminal.setFocus()
        self.terminal.run(interpreter.__file__, "t.txt")