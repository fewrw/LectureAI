
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
)

from storage.subject_repository import SubjectRepository
from storage.lecture_repository import LectureRepository

from ui.pages.home_page import HomePage
from ui.pages.subjects_page import SubjectsPage
from ui.pages.recording_page import RecordingPage
from ui.pages.history_page import HistoryPage
from ui.pages.placeholder_page import create_placeholder_page


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.source_root = Path(__file__).resolve().parents[1]

        self.repository = SubjectRepository(
            self.source_root / "storage" / "subjects.json"
        )

        self.lecture_repository = LectureRepository(
            self.source_root / "storage" / "lectures.db"
        )

        self.subjects, self.selected_subject = self.repository.load()

        self.setWindowTitle("LectureAI")
        self.resize(1200, 800)
        self.setMinimumSize(950, 650)

        self.setup_ui()
        self.apply_styles()
        self.refresh_all_pages()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

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
            ("Конспектирование", 2),
            ("История", 3),
            ("Настройки", 4),
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

        version = QLabel("LECTUREAI  •  VERSION 0.2")
        version.setObjectName("version")
        sidebar_layout.addWidget(version)

        self.home_page = HomePage()
        self.subjects_page = SubjectsPage()
        self.recording_page = RecordingPage()
        self.history_page = HistoryPage()

        self.pages.addWidget(self.home_page)       # 0
        self.pages.addWidget(self.subjects_page)   # 1
        self.pages.addWidget(self.recording_page)  # 2
        self.pages.addWidget(self.history_page)    # 3

        self.pages.addWidget(
            create_placeholder_page(
                "Настройки",
                "Здесь будут настройки приложения и AI-моделей."
            )
        )  # 4

        self.home_page.start_button.clicked.connect(
            lambda: self.change_page(2)
        )

        self.subjects_page.add_requested.connect(self.add_subject)
        self.subjects_page.subject_selected.connect(self.select_subject)
        self.subjects_page.rename_requested.connect(self.rename_subject)
        self.subjects_page.delete_requested.connect(self.delete_subject)

        self.recording_page.start_requested.connect(self.start_recording)

        self.history_page.filters_changed.connect(
            self.refresh_history
        )
        self.history_page.delete_requested.connect(
            self.delete_lecture
        )

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)

        self.change_page(0)

    def refresh_all_pages(self):
        self.subjects_page.set_subjects(
            self.subjects,
            self.selected_subject
        )

        self.recording_page.set_subjects(
            self.subjects,
            self.selected_subject
        )

        lecture_count = self.lecture_repository.get_counts()["total"]

        self.home_page.update_stats(
            len(self.subjects),
            lecture_count
        )

        self.refresh_history()

    def refresh_history(self):
        self.history_page.set_filter_subjects(
            self.lecture_repository.get_subjects()
        )

        filters = self.history_page.get_filters()

        lectures = self.lecture_repository.list_lectures(
            search_text=filters["search_text"],
            subject=filters["subject"]
        )

        self.history_page.set_lectures(lectures)

    def save_data(self):
        self.repository.save(
            self.subjects,
            self.selected_subject
        )

    def select_subject(self, index):
        if self.selected_subject == index:
            self.selected_subject = None
        else:
            self.selected_subject = index

        self.save_data()
        self.refresh_all_pages()

    def add_subject(self):
        name, accepted = QInputDialog.getText(
            self,
            "Новый предмет",
            "Введите название предмета:"
        )

        if not accepted or not name.strip():
            return

        name = name.strip()

        if any(
            item.casefold() == name.casefold()
            for item in self.subjects
        ):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Такой предмет уже существует."
            )
            return

        self.subjects.append(name)
        self.selected_subject = len(self.subjects) - 1

        self.save_data()
        self.subjects_page.search_input.clear()
        self.refresh_all_pages()

    def rename_subject(self, index):
        if not 0 <= index < len(self.subjects):
            return

        old_name = self.subjects[index]

        new_name, accepted = QInputDialog.getText(
            self,
            "Переименование предмета",
            "Введите новое название:",
            text=old_name,
        )

        if not accepted or not new_name.strip():
            return

        new_name = new_name.strip()

        for other_index, subject in enumerate(self.subjects):
            if (
                other_index != index
                and subject.casefold() == new_name.casefold()
            ):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Такой предмет уже существует."
                )
                return

        self.subjects[index] = new_name

        self.lecture_repository.rename_subject(
            old_name,
            new_name
        )

        self.save_data()
        self.refresh_all_pages()

    def delete_subject(self, index):
        if not 0 <= index < len(self.subjects):
            return

        name = self.subjects[index]

        answer = QMessageBox.question(
            self,
            "Удаление предмета",
            (
                f"Удалить предмет «{name}»?\n\n"
                "Сохранённые лекции останутся в истории "
                "с прежним названием предмета."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.subjects.pop(index)

        if self.selected_subject == index:
            self.selected_subject = None
        elif (
            self.selected_subject is not None
            and self.selected_subject > index
        ):
            self.selected_subject -= 1

        self.save_data()
        self.refresh_all_pages()

    def delete_lecture(self, lecture_id):
        answer = QMessageBox.question(
            self,
            "Удаление лекции",
            "Удалить этот конспект без возможности восстановления?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.lecture_repository.delete_lecture(lecture_id)
        self.refresh_all_pages()

    def start_recording(self, subject, lecture_name):
        if not subject:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Сначала создай учебный предмет."
            )
            return

        if not lecture_name:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Введи название лекции."
            )
            return

        self.recording_page.set_status(
            "Модуль захвата пока не подключён. Лекция не создана."
        )

    def change_page(self, index):
        if not 0 <= index < self.pages.count():
            return

        self.pages.setCurrentIndex(index)

        if index == 2:
            self.recording_page.set_subjects(
                self.subjects,
                self.selected_subject
            )

        elif index == 3:
            self.refresh_history()

        for button_index, button in self.buttons.items():
            button.setObjectName(
                "active_nav" if button_index == index else "nav_button"
            )
            button.style().unpolish(button)
            button.style().polish(button)

    def apply_styles(self):
        style_path = (
            self.source_root / "ui" / "styles" / "style.qss"
        )

        if style_path.exists():
            self.setStyleSheet(
                style_path.read_text(encoding="utf-8")
            )
