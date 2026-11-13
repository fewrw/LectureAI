from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QFrame,
    QComboBox, QLineEdit
)


class RecordingPage(QWidget):
    start_requested = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setObjectName("content")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 28, 35, 25)
        layout.setSpacing(20)

        title = QLabel("Новое конспектирование")
        title.setObjectName("page_title")

        description = QLabel(
            "Выбери предмет и укажи тему лекции."
        )
        description.setObjectName("description")

        layout.addWidget(title)
        layout.addWidget(description)

        panel = QFrame()
        panel.setObjectName("panel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(25, 25, 25, 25)
        panel_layout.setSpacing(15)

        subject_label = QLabel("УЧЕБНЫЙ ПРЕДМЕТ")
        subject_label.setObjectName("section_label")

        self.subject_combo = QComboBox()
        self.subject_combo.setMinimumHeight(40)

        lecture_label = QLabel("ТЕМА ЛЕКЦИИ")
        lecture_label.setObjectName("section_label")

        self.lecture_input = QLineEdit()
        self.lecture_input.setPlaceholderText(
            "Например: Введение в машинное обучение"
        )
        self.lecture_input.setMinimumHeight(40)

        self.status_label = QLabel("Ожидание запуска")
        self.status_label.setObjectName("description")

        self.start_button = QPushButton("Начать конспектирование")
        self.start_button.setObjectName("start_button")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self._emit_start)

        panel_layout.addWidget(subject_label)
        panel_layout.addWidget(self.subject_combo)
        panel_layout.addSpacing(5)
        panel_layout.addWidget(lecture_label)
        panel_layout.addWidget(self.lecture_input)
        panel_layout.addSpacing(10)
        panel_layout.addWidget(self.status_label)
        panel_layout.addWidget(self.start_button)

        layout.addWidget(panel)
        layout.addStretch()

    def set_subjects(self, subjects, selected_subject):
        current_text = self.subject_combo.currentText()

        self.subject_combo.clear()
        self.subject_combo.addItems(subjects)

        if (
            selected_subject is not None
            and 0 <= selected_subject < len(subjects)
        ):
            self.subject_combo.setCurrentIndex(selected_subject)
        elif current_text in subjects:
            self.subject_combo.setCurrentText(current_text)

    def _emit_start(self):
        self.start_requested.emit(
            self.subject_combo.currentText(),
            self.lecture_input.text().strip(),
        )

    def set_status(self, text):
        self.status_label.setText(text)
