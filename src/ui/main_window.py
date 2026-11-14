
import sys
import subprocess
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
from storage.app_paths import AppPaths
from storage.settings_repository import SettingsRepository

from ui.pages.home_page import HomePage
from ui.pages.subjects_page import SubjectsPage
from ui.pages.recording_page import RecordingPage
from ui.pages.history_page import HistoryPage
from ui.pages.settings_page import SettingsPage
from ui.pages.storage_page import StoragePage


class MainWindow(QMainWindow):

    AUTOSTART_NAME = "LectureAI"

    def __init__(self):
        super().__init__()

        self.source_root = Path(__file__).resolve().parents[1]

        # Пути пользовательских данных.
        self.paths = AppPaths()

        # Настройки приложения.
        self.settings_repository = SettingsRepository(
            self.paths.settings_file,
            defaults={
                "lectures_directory": str(self.paths.lectures),
                "models_directory": str(self.paths.models),

                "auto_start": False,

                "checkpoint_seconds": 30,
                "screen_sample_interval": 5,
                "capture_screen": True,
            }
        )

        self.settings = self.settings_repository.load()

        # Активные пользовательские папки.
        self._apply_settings_paths()

        # Хранилища.
        self.repository = SubjectRepository(
            self.paths.subjects_file
        )

        self.lecture_repository = LectureRepository(
            self.paths.database_file
        )

        self.subjects, self.selected_subject = self.repository.load()

        # Создание интерфейса.
        self.setup_ui()
        self.apply_styles()
        self.refresh_all_pages()

        self.setWindowTitle("LectureAI")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

    # --------------------------------------------------
    # ПУТИ И НАСТРОЙКИ
    # --------------------------------------------------

    def _apply_settings_paths(self):
        """Применяет сохранённые пользовательские пути."""

        self.lectures_directory = Path(
            self.settings.get(
                "lectures_directory",
                str(self.paths.lectures)
            )
        )

        self.models_directory = Path(
            self.settings.get(
                "models_directory",
                str(self.paths.models)
            )
        )

        self.paths.lectures_directory = self.lectures_directory
        self.paths.models_directory = self.models_directory

    def _set_windows_autostart(self, enabled):
        """
        Включает или отключает автозапуск LectureAI
        для текущего пользователя Windows.
        """

        if sys.platform != "win32":
            raise OSError(
                "Автозапуск поддерживается только в Windows."
            )

        import winreg

        registry_path = (
            r"Software\Microsoft\Windows\CurrentVersion\Run"
        )

        # Определяем команду запуска.
        if getattr(sys, "frozen", False):
            # Собранная версия приложения.
            executable = Path(sys.executable).resolve()

            command = subprocess.list2cmdline([
                str(executable)
            ])

        else:
            # Режим разработки.
            script = Path(sys.argv[0]).resolve()
            python_executable = Path(sys.executable).resolve()

            # pythonw.exe запускает приложение без консольного окна.
            pythonw = python_executable.with_name("pythonw.exe")

            if pythonw.exists():
                python_executable = pythonw

            command = subprocess.list2cmdline([
                str(python_executable),
                str(script),
            ])

        if enabled:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                registry_path,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:

                winreg.SetValueEx(
                    key,
                    self.AUTOSTART_NAME,
                    0,
                    winreg.REG_SZ,
                    command,
                )

        else:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    registry_path,
                    0,
                    winreg.KEY_SET_VALUE,
                ) as key:

                    winreg.DeleteValue(
                        key,
                        self.AUTOSTART_NAME,
                    )

            except FileNotFoundError:
                # Значение уже отсутствует.
                pass

    # --------------------------------------------------
    # ИНТЕРФЕЙС
    # --------------------------------------------------

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Боковая панель.
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

        # Основная область.
        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")
        self.buttons = {}

        navigation = [
            ("Главная", 0),
            ("Предметы", 1),
            ("Конспектирование", 2),
            ("История", 3),
            ("Настройки", 4),
            ("Хранилище", 5),
        ]

        for name, index in navigation:
            button = QPushButton(name)
            button.setObjectName("nav_button")
            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            button.clicked.connect(
                lambda checked=False, i=index:
                self.change_page(i)
            )

            sidebar_layout.addWidget(button)
            self.buttons[index] = button

        sidebar_layout.addStretch()

        version = QLabel("LECTUREAI  •  VERSION 0.2")
        version.setObjectName("version")
        sidebar_layout.addWidget(version)

        # Создание страниц.
        self.home_page = HomePage()
        self.subjects_page = SubjectsPage()
        self.recording_page = RecordingPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage(self.settings)
        self.storage_page = StoragePage(self.paths)

        # Добавление страниц.
        self.pages.addWidget(self.home_page)
        self.pages.addWidget(self.subjects_page)
        self.pages.addWidget(self.recording_page)
        self.pages.addWidget(self.history_page)
        self.pages.addWidget(self.settings_page)
        self.pages.addWidget(self.storage_page)

        # Сигналы главной страницы.
        self.home_page.start_button.clicked.connect(
            lambda: self.change_page(2)
        )

        # Сигналы предметов.
        self.subjects_page.add_requested.connect(
            self.add_subject
        )

        self.subjects_page.subject_selected.connect(
            self.select_subject
        )

        self.subjects_page.rename_requested.connect(
            self.rename_subject
        )

        self.subjects_page.delete_requested.connect(
            self.delete_subject
        )

        # Сигналы записи.
        self.recording_page.start_requested.connect(
            self.start_recording
        )

        # Сигналы истории.
        self.history_page.filters_changed.connect(
            self.refresh_history
        )

        self.history_page.delete_requested.connect(
            self.delete_lecture
        )

        # Сигналы настроек.
        self.settings_page.save_requested.connect(
            self.save_settings
        )

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)

        self.change_page(0)

    # --------------------------------------------------
    # СОХРАНЕНИЕ НАСТРОЕК
    # --------------------------------------------------

    def save_settings(self, settings):
        try:
            lectures_directory = Path(
                settings["lectures_directory"]
            ).expanduser().resolve()

            models_directory = Path(
                settings["models_directory"]
            ).expanduser().resolve()

            if not lectures_directory.is_dir():
                self.settings_page.set_status(
                    "Папка конспектов больше не существует."
                )
                return

            if not models_directory.is_dir():
                self.settings_page.set_status(
                    "Папка моделей больше не существует."
                )
                return

            new_settings = {
                "lectures_directory": str(lectures_directory),
                "models_directory": str(models_directory),

                "auto_start": settings["auto_start"],

                "checkpoint_seconds": settings["checkpoint_seconds"],
                "screen_sample_interval": settings["screen_sample_interval"],
                "capture_screen": settings["capture_screen"],
            }

            # Сначала обновляем автозапуск.
            previous_auto_start = self.settings.get(
                "auto_start",
                False
            )

            self._set_windows_autostart(
                new_settings["auto_start"]
            )

            try:
                self.settings_repository.save(new_settings)

            except Exception:
                # Если сохранение настроек не удалось,
                # пытаемся вернуть прежний автозапуск.
                try:
                    self._set_windows_autostart(
                        previous_auto_start
                    )
                except Exception:
                    pass

                raise

            self.settings = new_settings

            self._apply_settings_paths()

            # Обновляем настройки самой страницы.
            self.settings_page.settings = new_settings.copy()

            self.settings_page.set_status(
                "Настройки успешно сохранены."
            )

            self.storage_page.refresh()

        except (OSError, KeyError, TypeError, ValueError) as error:
            QMessageBox.critical(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить настройки:\n{error}"
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Произошла непредвиденная ошибка:\n{error}"
            )

    # --------------------------------------------------
    # ОБНОВЛЕНИЕ СТРАНИЦ
    # --------------------------------------------------

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

    # --------------------------------------------------
    # ПРЕДМЕТЫ
    # --------------------------------------------------

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

    # --------------------------------------------------
    # ИСТОРИЯ
    # --------------------------------------------------

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

    # --------------------------------------------------
    # ЗАПИСЬ
    # --------------------------------------------------

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
            "Модуль захвата пока не подключён. "
            "Лекция не создана."
        )

    # --------------------------------------------------
    # НАВИГАЦИЯ
    # --------------------------------------------------

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

        elif index == 5:
            self.storage_page.refresh()

        for button_index, button in self.buttons.items():
            button.setObjectName(
                "active_nav"
                if button_index == index
                else "nav_button"
            )

            button.style().unpolish(button)
            button.style().polish(button)

    # --------------------------------------------------
    # СТИЛИ
    # --------------------------------------------------

    def apply_styles(self):
        style_path = (
            self.source_root / "ui" / "styles" / "style.qss"
        )

        if style_path.exists():
            self.setStyleSheet(
                style_path.read_text(encoding="utf-8")
            )
