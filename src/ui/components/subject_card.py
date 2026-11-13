from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame


class SubjectCard(QFrame):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)
