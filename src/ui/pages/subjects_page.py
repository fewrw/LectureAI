from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QScrollArea, QGridLayout, QFrame
)

from ui.components.subject_card import SubjectCard


class SubjectsPage(QWidget):
    add_requested = Signal()
    subject_selected = Signal(int)
    rename_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self):
        super().__init__()
        self.setObjectName("content")
        self.subjects = []
        self.selected_subject = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 28, 35, 25)
        layout.setSpacing(20)

        header = QHBoxLayout()

        title = QLabel("Мои предметы")
        title.setObjectName("page_title")

        self.total_label = QLabel("0 ПРЕДМЕТОВ")
        self.total_label.setObjectName("section_label")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.total_label)
        layout.addLayout(header)

        description = QLabel(
            "Управление учебными дисциплинами и лекциями."
        )
        description.setObjectName("description")
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("subject_search")
        self.search_input.setPlaceholderText("Поиск предмета...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.refresh_cards)

        add_button = QPushButton("+  Добавить предмет")
        add_button.setObjectName("add_subject_button")
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_button.clicked.connect(self.add_requested.emit)

        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(add_button)
        layout.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("subject_scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(2, 2, 2, 2)
        self.grid.setSpacing(15)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def set_subjects(self, subjects, selected_subject):
        self.subjects = list(subjects)
        self.selected_subject = selected_subject
        self.refresh_cards()

    def refresh_cards(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        search_text = self.search_input.text().strip().casefold()
        visible = [
            (index, name)
            for index, name in enumerate(self.subjects)
            if search_text in name.casefold()
        ]

        self.total_label.setText(f"{len(self.subjects)} ПРЕДМЕТОВ")

        if not visible:
            message = (
                "Предметы не найдены."
                if search_text
                else "Пока нет предметов.\\nДобавь первый предмет."
            )
            empty = QLabel(message)
            empty.setObjectName("empty_subjects")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid.addWidget(empty, 0, 0, 1, 2)
            return

        for position, (index, name) in enumerate(visible):
            card = SubjectCard()
            card.setObjectName(
                "subject_card_selected"
                if self.selected_subject == index
                else "subject_card"
            )
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.clicked.connect(
                lambda i=index: self.subject_selected.emit(i)
            )

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(12)

            title = QLabel(name)
            title.setObjectName("subject_card_title")
            title.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )
            card_layout.addWidget(title)

            subtitle = QLabel("Учебный предмет")
            subtitle.setObjectName("subject_card_description")
            subtitle.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )
            card_layout.addWidget(subtitle)

            if self.selected_subject == index:
                separator = QFrame()
                separator.setObjectName("subject_separator")
                separator.setFixedHeight(1)
                separator.setAttribute(
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents
                )
                card_layout.addWidget(separator)

                actions = QHBoxLayout()
                actions.setSpacing(8)

                rename_button = QPushButton("Переименовать")
                rename_button.setObjectName("rename_subject_button")
                rename_button.setCursor(Qt.CursorShape.PointingHandCursor)
                rename_button.clicked.connect(
                    lambda checked=False, i=index:
                    self.rename_requested.emit(i)
                )

                delete_button = QPushButton("Удалить")
                delete_button.setObjectName("delete_subject_button")
                delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
                delete_button.clicked.connect(
                    lambda checked=False, i=index:
                    self.delete_requested.emit(i)
                )

                actions.addWidget(rename_button)
                actions.addWidget(delete_button)
                card_layout.addLayout(actions)

            self.grid.addWidget(card, position // 2, position % 2)
