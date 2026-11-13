from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QScrollArea,
    QLineEdit, QComboBox
)


class LectureHistoryCard(QFrame):

    delete_requested = Signal(int)

    def __init__(self, lecture):
        super().__init__()

        self.lecture_id = lecture["id"]

        self.setObjectName("panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()

        title = QLabel(lecture["title"])
        title.setObjectName("subject_card_title")
        title.setWordWrap(True)

        delete_button = QPushButton("Удалить")
        delete_button.setObjectName("delete_subject_button")
        delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_button.clicked.connect(
            lambda: self.delete_requested.emit(self.lecture_id)
        )

        header.addWidget(title, 1)
        header.addWidget(delete_button)

        layout.addLayout(header)

        subject = QLabel(lecture["subject"])
        subject.setObjectName("subject_card_description")
        layout.addWidget(subject)

        date = QLabel(lecture["created_at"].replace("T", " "))
        date.setObjectName("card_description")
        layout.addWidget(date)

        status = QLabel(self._status_text(lecture["status"]))
        status.setObjectName("description")
        layout.addWidget(status)

        if lecture.get("summary"):
            summary = QLabel(lecture["summary"])
            summary.setObjectName("description")
            summary.setWordWrap(True)
            layout.addWidget(summary)

    @staticmethod
    def _status_text(status):
        statuses = {
            "draft": "Черновик",
            "processing": "Обработка",
            "completed": "Завершено",
            "failed": "Ошибка"
        }

        return statuses.get(status, status)


class HistoryPage(QWidget):

    delete_requested = Signal(int)
    filters_changed = Signal()

    def __init__(self):
        super().__init__()

        self.setObjectName("content")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 28, 35, 25)
        layout.setSpacing(20)

        header = QHBoxLayout()

        title = QLabel("История лекций")
        title.setObjectName("page_title")

        self.total_label = QLabel("0 ЛЕКЦИЙ")
        self.total_label.setObjectName("section_label")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.total_label)

        layout.addLayout(header)

        description = QLabel(
            "Все сохранённые конспекты в одном месте."
        )
        description.setObjectName("description")

        layout.addWidget(description)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("subject_search")
        self.search_input.setPlaceholderText("Поиск лекции...")
        self.search_input.setClearButtonEnabled(True)

        self.subject_filter = QComboBox()
        self.subject_filter.setMinimumHeight(40)
        self.subject_filter.addItem("Все предметы")

        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.subject_filter)

        layout.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()

        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(2, 2, 2, 2)
        self.cards_layout.setSpacing(12)

        self.cards_layout.addStretch()

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        self.search_input.textChanged.connect(
            self.filters_changed.emit
        )

        self.subject_filter.currentTextChanged.connect(
            self.filters_changed.emit
        )

    def set_filter_subjects(self, subjects):
        current = self.subject_filter.currentText()

        self.subject_filter.blockSignals(True)

        self.subject_filter.clear()
        self.subject_filter.addItem("Все предметы")
        self.subject_filter.addItems(subjects)

        index = self.subject_filter.findText(current)

        if index >= 0:
            self.subject_filter.setCurrentIndex(index)

        self.subject_filter.blockSignals(False)

    def get_filters(self):
        subject = self.subject_filter.currentText()

        if subject == "Все предметы":
            subject = None

        return {
            "search_text": self.search_input.text(),
            "subject": subject
        }

    def set_lectures(self, lectures):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.total_label.setText(
            f"{len(lectures)} ЛЕКЦИЙ"
        )

        if not lectures:
            empty = QLabel(
                "Лекции пока не найдены."
            )
            empty.setObjectName("empty_subjects")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.cards_layout.insertWidget(0, empty)
            return

        for lecture in lectures:
            card = LectureHistoryCard(lecture)

            card.delete_requested.connect(
                self.delete_requested.emit
            )

            self.cards_layout.insertWidget(
                self.cards_layout.count() - 1,
                card
            )