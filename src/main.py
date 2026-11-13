import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QStackedWidget,
    QInputDialog,
    QMessageBox,
    QLineEdit,
    QScrollArea,
    QGridLayout,
)


# -------------------------
# SUBJECT CARD
# -------------------------

class SubjectCard(QFrame):

    clicked = Signal()

    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(event)


# -------------------------
# MAIN WINDOW
# -------------------------

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.data_path = (
            Path(__file__).resolve().parent
            / "storage"
            / "subjects.json"
        )

        self.subjects = []
        self.selected_subject = None

        self.load_data()

        self.setWindowTitle("LectureAI")
        self.resize(1200, 800)
        self.setMinimumSize(950, 650)

        self.setup_ui()
        self.apply_styles()

    # -------------------------
    # MAIN WINDOW
    # -------------------------

    def setup_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # SIDEBAR

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 28, 20, 20)
        sidebar_layout.setSpacing(12)

        logo = QLabel("LECTURE<span>AI</span>")
        logo.setObjectName("logo")
        sidebar_layout.addWidget(logo)

        sidebar_layout.addSpacing(35)

        section = QLabel("WORKSPACE")
        section.setObjectName("section_label")
        sidebar_layout.addWidget(section)

        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")

        self.buttons = {}

        navigation = [
            ("Главная", 0),
            ("Предметы", 1),
            ("История", 2),
            ("Настройки", 3),
        ]

        for name, index in navigation:

            button = QPushButton(name)
            button.setObjectName("nav_button")
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            button.clicked.connect(
                lambda checked=False, i=index: self.change_page(i)
            )

            sidebar_layout.addWidget(button)
            self.buttons[index] = button

        sidebar_layout.addStretch()

        version = QLabel("LECTUREAI  •  VERSION 0.1")
        version.setObjectName("version")
        sidebar_layout.addWidget(version)

        # PAGES

        self.pages.addWidget(self.create_home_page())
        self.pages.addWidget(self.create_subjects_page())

        self.pages.addWidget(
            self.create_placeholder(
                "История",
                "Здесь будут находиться сохранённые конспекты."
            )
        )

        self.pages.addWidget(
            self.create_placeholder(
                "Настройки",
                "Здесь будут настройки приложения и AI-моделей."
            )
        )

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)

        self.change_page(0)

    # -------------------------
    # HOME PAGE
    # -------------------------

    def create_home_page(self):

        page = QWidget()
        page.setObjectName("content")

        layout = QVBoxLayout(page)
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

        # WELCOME

        welcome = QFrame()
        welcome.setObjectName("welcome")

        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.setContentsMargins(28, 25, 28, 25)

        welcome_title = QLabel("Твои лекции. Твои знания.")
        welcome_title.setObjectName("welcome_title")

        description = QLabel(
            "LectureAI превращает записи занятий "
            "в структурированные конспекты."
        )
        description.setObjectName("description")
        description.setWordWrap(True)

        start_button = QPushButton("Начать конспектирование")
        start_button.setObjectName("start_button")
        start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        start_button.clicked.connect(self.start_recording)

        welcome_layout.addWidget(welcome_title)
        welcome_layout.addWidget(description)
        welcome_layout.addSpacing(10)
        welcome_layout.addWidget(start_button, 0)

        layout.addWidget(welcome)

        # STATISTICS

        cards = QHBoxLayout()
        cards.setSpacing(15)

        cards.addWidget(
            self.create_card(
                "ПРЕДМЕТЫ",
                "0",
                "Созданных предметов"
            )
        )

        cards.addWidget(
            self.create_card(
                "КОНСПЕКТЫ",
                "0",
                "Сохранённых лекций"
            )
        )

        cards.addWidget(
            self.create_card(
                "AI ENGINE",
                "Не подключён",
                "Локальная модель"
            )
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
            "Здесь будут отображаться последние конспекты."
        )
        recent_text.setObjectName("description")

        recent_layout.addWidget(recent_text)
        layout.addWidget(recent)

        layout.addStretch()

        footer = QLabel(
            "Система готова к работе  •  Все данные хранятся локально"
        )
        footer.setObjectName("footer")

        layout.addWidget(footer)

        return page

    # -------------------------
    # SUBJECTS PAGE
    # -------------------------

    def create_subjects_page(self):

        page = QWidget()
        page.setObjectName("content")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(35, 28, 35, 25)
        layout.setSpacing(20)

        # HEADER

        header = QHBoxLayout()

        title = QLabel("Мои предметы")
        title.setObjectName("page_title")

        self.subject_total_label = QLabel("0 ПРЕДМЕТОВ")
        self.subject_total_label.setObjectName("section_label")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.subject_total_label)

        layout.addLayout(header)

        description = QLabel(
            "Управление учебными дисциплинами и лекциями."
        )
        description.setObjectName("description")

        layout.addWidget(description)

        # SEARCH AND ADD BUTTON

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.subject_search = QLineEdit()
        self.subject_search.setObjectName("subject_search")
        self.subject_search.setPlaceholderText("Поиск предмета...")
        self.subject_search.setClearButtonEnabled(True)

        self.subject_search.textChanged.connect(
            self.refresh_subject_cards
        )

        add_button = QPushButton("+  Добавить предмет")
        add_button.setObjectName("add_subject_button")
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_button.clicked.connect(self.add_subject)

        toolbar.addWidget(self.subject_search, 1)
        toolbar.addWidget(add_button)

        layout.addLayout(toolbar)

        # SCROLL AREA

        self.subject_scroll = QScrollArea()
        self.subject_scroll.setObjectName("subject_scroll")
        self.subject_scroll.setWidgetResizable(True)
        self.subject_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.subject_container = QWidget()

        self.subject_grid = QGridLayout(self.subject_container)
        self.subject_grid.setContentsMargins(2, 2, 2, 2)
        self.subject_grid.setSpacing(15)

        self.subject_grid.setColumnStretch(0, 1)
        self.subject_grid.setColumnStretch(1, 1)

        self.subject_scroll.setWidget(self.subject_container)

        layout.addWidget(self.subject_scroll)

        self.refresh_subject_cards()

        return page

    # -------------------------
    # SUBJECT CARDS
    # -------------------------

    def refresh_subject_cards(self):

        # Удаляем старые карточки

        while self.subject_grid.count():

            item = self.subject_grid.takeAt(0)
            widget = item.widget()

            if widget:
                widget.deleteLater()

        search_text = self.subject_search.text().strip().lower()

        visible_subjects = []

        for index, name in enumerate(self.subjects):

            if search_text in name.lower():
                visible_subjects.append((index, name))

        # Счётчик

        count = len(self.subjects)

        self.subject_total_label.setText(
            f"{count} ПРЕДМЕТОВ"
        )

        if hasattr(self, "subject_count_value"):
            self.subject_count_value.setText(str(count))

        # Пустое состояние

        if not visible_subjects:

            empty = QLabel(
                "Предметы не найдены."
                if search_text
                else "Пока нет предметов.\nДобавь первый предмет."
            )

            empty.setObjectName("empty_subjects")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.subject_grid.addWidget(empty, 0, 0, 1, 2)
            return

        # Создаём карточки

        for position, (index, name) in enumerate(visible_subjects):

            card = SubjectCard()

            card.setObjectName(
                "subject_card_selected"
                if self.selected_subject == index
                else "subject_card"
            )

            card.setCursor(Qt.CursorShape.PointingHandCursor)

            card.clicked.connect(
                lambda i=index: self.select_subject(i)
            )

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(12)

            # Название

            card_title = QLabel(name)
            card_title.setObjectName("subject_card_title")
            card_title.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )

            card_layout.addWidget(card_title)

            # Описание

            card_description = QLabel("Учебный предмет")
            card_description.setObjectName("subject_card_description")
            card_description.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )

            card_layout.addWidget(card_description)

            # Действия для выбранного предмета

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
                rename_button.setCursor(
                    Qt.CursorShape.PointingHandCursor
                )

                rename_button.clicked.connect(
                    lambda checked=False, i=index: self.rename_subject(i)
                )

                delete_button = QPushButton("Удалить")
                delete_button.setObjectName("delete_subject_button")
                delete_button.setCursor(
                    Qt.CursorShape.PointingHandCursor
                )

                delete_button.clicked.connect(
                    lambda checked=False, i=index: self.delete_subject(i)
                )

                actions.addWidget(rename_button)
                actions.addWidget(delete_button)

                card_layout.addLayout(actions)

            row = position // 2
            column = position % 2

            self.subject_grid.addWidget(card, row, column)

    # -------------------------
    # DATA STORAGE
    # -------------------------

    def load_data(self):

        if not self.data_path.exists():
            return

        try:
            data = json.loads(
                self.data_path.read_text(encoding="utf-8")
            )

            if not isinstance(data, dict):
                return

            subjects = data.get("subjects", [])

            if not isinstance(subjects, list):
                return

            self.subjects = [
                name.strip()
                for name in subjects
                if isinstance(name, str) and name.strip()
            ]

            selected = data.get("selected_subject")

            if (
                isinstance(selected, int)
                and not isinstance(selected, bool)
                and 0 <= selected < len(self.subjects)
            ):
                self.selected_subject = selected

        except (json.JSONDecodeError, OSError):
            self.subjects = []
            self.selected_subject = None

    def save_data(self):

        self.data_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        data = {
            "subjects": self.subjects,
            "selected_subject": self.selected_subject
        }

        self.data_path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=4
            ),
            encoding="utf-8"
        )

    # -------------------------
    # SUBJECT MANAGEMENT
    # -------------------------

    def select_subject(self, index):

        if self.selected_subject == index:
            self.selected_subject = None
        else:
            self.selected_subject = index

        self.save_data()
        self.refresh_subject_cards()

    def add_subject(self):

        name, accepted = QInputDialog.getText(
            self,
            "Новый предмет",
            "Введите название предмета:"
        )

        if not accepted or not name.strip():
            return

        name = name.strip()

        for subject in self.subjects:

            if subject.lower() == name.lower():

                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Такой предмет уже существует."
                )
                return

        self.subjects.append(name)
        self.selected_subject = len(self.subjects) - 1

        self.save_data()

        self.subject_search.clear()
        self.refresh_subject_cards()

    def rename_subject(self, index):

        old_name = self.subjects[index]

        new_name, accepted = QInputDialog.getText(
            self,
            "Переименование предмета",
            "Введите новое название:",
            text=old_name
        )

        if not accepted or not new_name.strip():
            return

        new_name = new_name.strip()

        for other_index, subject in enumerate(self.subjects):

            if (
                other_index != index
                and subject.lower() == new_name.lower()
            ):

                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Такой предмет уже существует."
                )
                return

        self.subjects[index] = new_name

        self.save_data()
        self.refresh_subject_cards()

    def delete_subject(self, index):

        name = self.subjects[index]

        answer = QMessageBox.question(
            self,
            "Удаление предмета",
            f"Удалить предмет «{name}»?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer == QMessageBox.StandardButton.Yes:

            self.subjects.pop(index)
            self.selected_subject = None

            self.save_data()
            self.refresh_subject_cards()

    # -------------------------
    # PLACEHOLDER PAGES
    # -------------------------

    def create_placeholder(self, title_text, description_text):

        page = QWidget()
        page.setObjectName("content")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(35, 28, 35, 25)

        title = QLabel(title_text)
        title.setObjectName("page_title")

        panel = QFrame()
        panel.setObjectName("panel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(25, 25, 25, 25)

        description = QLabel(description_text)
        description.setObjectName("description")

        panel_layout.addWidget(description)

        layout.addWidget(title)
        layout.addSpacing(20)
        layout.addWidget(panel)
        layout.addStretch()

        return page

    # -------------------------
    # STATISTICS CARD
    # -------------------------

    def create_card(self, heading, value, description):

        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(135)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(9)

        title = QLabel(heading)
        title.setObjectName("card_heading")

        number = QLabel(value)
        number.setObjectName("card_value")

        subtitle = QLabel(description)
        subtitle.setObjectName("card_description")

        if heading == "ПРЕДМЕТЫ":
            self.subject_count_value = number

        layout.addWidget(title)
        layout.addWidget(number)
        layout.addWidget(subtitle)
        layout.addStretch()

        return card

    # -------------------------
    # NAVIGATION
    # -------------------------

    def change_page(self, index):

        self.pages.setCurrentIndex(index)

        for button_index, button in self.buttons.items():

            if button_index == index:
                button.setObjectName("active_nav")
            else:
                button.setObjectName("nav_button")

            button.style().unpolish(button)
            button.style().polish(button)

    # -------------------------
    # RECORDING
    # -------------------------

    def start_recording(self):

        self.statusBar().showMessage(
            "Модуль конспектирования пока не подключён.",
            4000
        )

    # -------------------------
    # STYLES
    # -------------------------

    def apply_styles(self):

        style_path = (
            Path(__file__).resolve().parent
            / "ui"
            / "styles"
            / "style.qss"
        )

        self.setStyleSheet(
            style_path.read_text(encoding="utf-8")
        )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())