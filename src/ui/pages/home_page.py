from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt


class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("content")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 28, 35, 25)
        layout.setSpacing(25)

        header = QHBoxLayout()

        title = QLabel("Главная")
        title.setObjectName("page_title")

        status = QLabel("●  LOCAL SYSTEM")
        status.setObjectName("system_status")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(status)
        layout.addLayout(header)

        welcome = QFrame()
        welcome.setObjectName("welcome")
        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.setContentsMargins(28, 25, 28, 25)

        welcome_title = QLabel("Твои лекции. Твои знания.")
        welcome_title.setObjectName("welcome_title")

        description = QLabel(
            "LectureAI превращает занятия в структурированные конспекты."
        )
        description.setObjectName("description")
        description.setWordWrap(True)

        self.start_button = QPushButton("Начать конспектирование")
        self.start_button.setObjectName("start_button")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)

        welcome_layout.addWidget(welcome_title)
        welcome_layout.addWidget(description)
        welcome_layout.addSpacing(10)
        welcome_layout.addWidget(self.start_button, 0)
        layout.addWidget(welcome)

        cards = QHBoxLayout()
        cards.setSpacing(15)

        self.subject_value = self._create_card(
            cards, "ПРЕДМЕТЫ", "0", "Созданных предметов"
        )
        self.lecture_value = self._create_card(
            cards, "КОНСПЕКТЫ", "0", "Сохранённых лекций"
        )
        self.engine_value = self._create_card(
            cards, "AI ENGINE", "Не подключён", "Локальная модель"
        )
        layout.addLayout(cards)

        recent_title = QLabel("БЫСТРЫЙ ДОСТУП")
        recent_title.setObjectName("section_label")
        layout.addWidget(recent_title)

        recent = QFrame()
        recent.setObjectName("panel")
        recent_layout = QVBoxLayout(recent)
        recent_layout.setContentsMargins(20, 20, 20, 20)

        recent_text = QLabel(
            "Последние конспекты появятся здесь после подключения истории."
        )
        recent_text.setObjectName("description")
        recent_layout.addWidget(recent_text)
        layout.addWidget(recent)

        layout.addStretch()

        footer = QLabel(
            "Локальная обработка  •  Данные остаются на этом устройстве"
        )
        footer.setObjectName("footer")
        layout.addWidget(footer)

    @staticmethod
    def _create_card(parent_layout, heading, value, description):
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(135)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(9)

        title = QLabel(heading)
        title.setObjectName("card_heading")

        number = QLabel(value)
        number.setObjectName("card_value")

        subtitle = QLabel(description)
        subtitle.setObjectName("card_description")

        card_layout.addWidget(title)
        card_layout.addWidget(number)
        card_layout.addWidget(subtitle)
        card_layout.addStretch()

        parent_layout.addWidget(card)
        return number

    def update_stats(self, subject_count, lecture_count=0):
        self.subject_value.setText(str(subject_count))
        self.lecture_value.setText(str(lecture_count))
