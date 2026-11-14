
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLineEdit,
    QFileDialog,
    QScrollArea,
    QStackedWidget,
    QCheckBox,
    QSpinBox,
)


class SettingsPage(QWidget):

    save_requested = Signal(dict)

    def __init__(self, settings):
        super().__init__()

        self.settings = settings.copy()

        self.setObjectName("content")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(35, 28, 35, 25)
        root_layout.setSpacing(20)

        title = QLabel("Настройки")
        title.setObjectName("page_title")

        description = QLabel(
            "Управление параметрами и поведением LectureAI."
        )
        description.setObjectName("description")

        root_layout.addWidget(title)
        root_layout.addWidget(description)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Боковая навигация.
        sidebar = QFrame()
        sidebar.setObjectName("panel")
        sidebar.setFixedWidth(220)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 18, 12, 18)
        sidebar_layout.setSpacing(7)

        sidebar_title = QLabel("РАЗДЕЛЫ")
        sidebar_title.setObjectName("section_label")
        sidebar_layout.addWidget(sidebar_title)

        self.navigation_buttons = {}

        sections = [
            ("Основные", True),
            ("Запись", True),
            ("Искусственный интеллект", False),
            ("Конспекты", False),
            ("Хранилище", True),
            ("Обновления", False),
        ]

        for name, available in sections:
            button = QPushButton(name)
            button.setObjectName("settings_nav_button")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setEnabled(available)

            if available:
                button.clicked.connect(
                    lambda checked=False, section=name:
                    self.show_section(section)
                )

            self.navigation_buttons[name] = button
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        content_layout.addWidget(sidebar)

        # Рабочая область.
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        content_layout_inner = QVBoxLayout(content_widget)
        content_layout_inner.setContentsMargins(0, 0, 0, 0)
        content_layout_inner.setSpacing(15)

        self.section_stack = QStackedWidget()
        self.section_stack.setObjectName("settings_stack")

        self._build_general_section()
        self._build_recording_section()
        self._build_storage_section()

        content_layout_inner.addWidget(self.section_stack)

        self.status_label = QLabel("")
        self.status_label.setObjectName("description")
        self.status_label.setWordWrap(True)

        self.save_button = QPushButton("Сохранить настройки")
        self.save_button.setObjectName("save_settings_button")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save_settings)

        content_layout_inner.addWidget(self.status_label)
        content_layout_inner.addWidget(self.save_button)
        content_layout_inner.addStretch()

        self.scroll_area.setWidget(content_widget)

        content_layout.addWidget(self.scroll_area, 1)
        root_layout.addLayout(content_layout)

        self.show_section("Основные")

    def _create_panel(self, title_text, description_text):
        panel = QFrame()
        panel.setObjectName("panel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        title = QLabel(title_text)
        title.setObjectName("page_title")

        description = QLabel(description_text)
        description.setObjectName("description")
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(15)

        return panel, layout

    def _build_general_section(self):
        panel, layout = self._create_panel(
            "Основные",
            "Общие параметры запуска приложения."
        )

        self.autostart_checkbox = QCheckBox(
            "Запускать LectureAI вместе с Windows"
        )

        self.autostart_checkbox.setChecked(
            self.settings.get("auto_start", False)
        )

        self.autostart_checkbox.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        autostart_description = QLabel(
            "Приложение будет запускаться автоматически "
            "после входа в Windows под текущим пользователем."
        )
        autostart_description.setObjectName("description")
        autostart_description.setWordWrap(True)

        layout.addWidget(self.autostart_checkbox)
        layout.addWidget(autostart_description)

        layout.addStretch()
        self.section_stack.addWidget(panel)

    def _build_recording_section(self):
        panel, layout = self._create_panel(
            "Запись",
            "Параметры сохранения аудио и захвата экрана."
        )

        # Контрольные сегменты аудио.
        checkpoint_label = QLabel("ИНТЕРВАЛ СОХРАНЕНИЯ АУДИО")
        checkpoint_label.setObjectName("section_label")

        checkpoint_description = QLabel(
            "Как часто AudioRecorder должен закрывать текущий "
            "аудиофайл и создавать следующий."
        )
        checkpoint_description.setObjectName("description")
        checkpoint_description.setWordWrap(True)

        self.checkpoint_spin = QSpinBox()
        self.checkpoint_spin.setRange(10, 300)
        self.checkpoint_spin.setSingleStep(10)
        self.checkpoint_spin.setSuffix(" сек.")
        self.checkpoint_spin.setValue(
            self.settings.get("checkpoint_seconds", 30)
        )

        layout.addWidget(checkpoint_label)
        layout.addWidget(checkpoint_description)
        layout.addWidget(self.checkpoint_spin)

        layout.addSpacing(20)

        # Интервал захвата экрана.
        screen_interval_label = QLabel(
            "ИНТЕРВАЛ ЗАХВАТА ЭКРАНА"
        )
        screen_interval_label.setObjectName("section_label")

        screen_interval_description = QLabel(
            "Минимальное время между сохраняемыми кадрами. "
            "Это не частота видеозаписи."
        )
        screen_interval_description.setObjectName("description")
        screen_interval_description.setWordWrap(True)

        self.screen_interval_spin = QSpinBox()
        self.screen_interval_spin.setRange(1, 60)
        self.screen_interval_spin.setSingleStep(1)
        self.screen_interval_spin.setSuffix(" сек.")
        self.screen_interval_spin.setValue(
            self.settings.get("screen_sample_interval", 5)
        )

        layout.addWidget(screen_interval_label)
        layout.addWidget(screen_interval_description)
        layout.addWidget(self.screen_interval_spin)

        layout.addSpacing(20)

        # Включение захвата экрана.
        self.capture_screen_checkbox = QCheckBox(
            "Сохранять кадры с экрана во время лекции"
        )

        self.capture_screen_checkbox.setChecked(
            self.settings.get("capture_screen", True)
        )

        self.capture_screen_checkbox.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        capture_description = QLabel(
            "Если выключено, LectureAI будет записывать только аудио. "
            "Эта настройка не влияет на аудиозапись."
        )
        capture_description.setObjectName("description")
        capture_description.setWordWrap(True)

        layout.addWidget(self.capture_screen_checkbox)
        layout.addWidget(capture_description)

        layout.addStretch()
        self.section_stack.addWidget(panel)

    def _build_storage_section(self):
        panel, layout = self._create_panel(
            "Хранилище",
            "Настройка расположения пользовательских файлов."
        )

        # Папка конспектов.
        lectures_label = QLabel("ПАПКА КОНСПЕКТОВ")
        lectures_label.setObjectName("section_label")

        lectures_description = QLabel(
            "Место хранения готовых DOCX-конспектов "
            "и материалов лекций."
        )
        lectures_description.setObjectName("description")
        lectures_description.setWordWrap(True)

        lectures_row = QHBoxLayout()
        lectures_row.setSpacing(10)

        self.lectures_input = QLineEdit()
        self.lectures_input.setObjectName("settings_path")
        self.lectures_input.setMinimumHeight(40)
        self.lectures_input.setText(
            self.settings.get("lectures_directory", "")
        )

        lectures_browse = QPushButton("Выбрать")
        lectures_browse.setObjectName("browse_button")
        lectures_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        lectures_browse.clicked.connect(
            lambda: self.select_directory(self.lectures_input)
        )

        lectures_row.addWidget(self.lectures_input)
        lectures_row.addWidget(lectures_browse)

        # Папка моделей.
        models_label = QLabel("ПАПКА AI-МОДЕЛЕЙ")
        models_label.setObjectName("section_label")

        models_description = QLabel(
            "Место хранения языковых, речевых "
            "и вспомогательных моделей."
        )
        models_description.setObjectName("description")
        models_description.setWordWrap(True)

        models_row = QHBoxLayout()
        models_row.setSpacing(10)

        self.models_input = QLineEdit()
        self.models_input.setObjectName("settings_path")
        self.models_input.setMinimumHeight(40)
        self.models_input.setText(
            self.settings.get("models_directory", "")
        )

        models_browse = QPushButton("Выбрать")
        models_browse.setObjectName("browse_button")
        models_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        models_browse.clicked.connect(
            lambda: self.select_directory(self.models_input)
        )

        models_row.addWidget(self.models_input)
        models_row.addWidget(models_browse)

        layout.addWidget(lectures_label)
        layout.addWidget(lectures_description)
        layout.addLayout(lectures_row)

        layout.addSpacing(15)

        layout.addWidget(models_label)
        layout.addWidget(models_description)
        layout.addLayout(models_row)

        layout.addStretch()
        self.section_stack.addWidget(panel)

    def show_section(self, section):
        sections = {
            "Основные": 0,
            "Запись": 1,
            "Хранилище": 2,
        }

        if section not in sections:
            return

        self.section_stack.setCurrentIndex(sections[section])

        for name, button in self.navigation_buttons.items():
            active = name == section

            button.setObjectName(
                "settings_nav_active"
                if active
                else "settings_nav_button"
            )

            button.style().unpolish(button)
            button.style().polish(button)

    def select_directory(self, line_edit):
        current_path = line_edit.text().strip()

        if not Path(current_path).is_dir():
            current_path = str(Path.home())

        directory = QFileDialog.getExistingDirectory(
            self,
            "Выбрать папку",
            current_path,
        )

        if directory:
            line_edit.setText(directory)
            self.status_label.clear()

    def save_settings(self):
        lectures_directory = self.lectures_input.text().strip()
        models_directory = self.models_input.text().strip()

        if not lectures_directory or not models_directory:
            self.set_status("Необходимо указать обе папки.")
            self.show_section("Хранилище")
            return

        lectures_path = Path(lectures_directory).expanduser()
        models_path = Path(models_directory).expanduser()

        if not lectures_path.is_dir():
            self.set_status(
                "Указанная папка конспектов не существует."
            )
            self.show_section("Хранилище")
            return

        if not models_path.is_dir():
            self.set_status(
                "Указанная папка моделей не существует."
            )
            self.show_section("Хранилище")
            return

        settings = {
            "lectures_directory": str(lectures_path.resolve()),
            "models_directory": str(models_path.resolve()),

            "auto_start": self.autostart_checkbox.isChecked(),

            "checkpoint_seconds": self.checkpoint_spin.value(),
            "screen_sample_interval": self.screen_interval_spin.value(),
            "capture_screen": self.capture_screen_checkbox.isChecked(),
        }

        self.save_requested.emit(settings)

    def set_status(self, text):
        self.status_label.setText(text)
