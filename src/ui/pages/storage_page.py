
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QMessageBox,
)

from storage.storage_manager import StorageManager


class StoragePage(QWidget):

    def __init__(self, paths):
        super().__init__()

        self.paths = paths
        self.manager = StorageManager(paths)

        self.setObjectName("content")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 28, 35, 25)
        layout.setSpacing(20)

        title = QLabel("Хранилище")
        title.setObjectName("page_title")

        description = QLabel(
            "Просмотр пользовательских данных и занятого пространства."
        )
        description.setObjectName("description")

        layout.addWidget(title)
        layout.addWidget(description)

        # Общая информация
        summary = QFrame()
        summary.setObjectName("panel")

        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(25, 20, 25, 20)
        summary_layout.setSpacing(10)

        summary_title = QLabel("ОБЩЕЕ ИСПОЛЬЗОВАНИЕ")
        summary_title.setObjectName("section_label")

        self.total_size_label = QLabel("Занято: —")
        self.total_size_label.setObjectName("page_title")

        self.files_count_label = QLabel("Файлов: —")
        self.files_count_label.setObjectName("description")

        self.disk_space_label = QLabel("Свободно на диске: —")
        self.disk_space_label.setObjectName("description")

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.total_size_label)
        summary_layout.addWidget(self.files_count_label)
        summary_layout.addWidget(self.disk_space_label)

        layout.addWidget(summary)

        # Список расположений
        locations_title = QLabel("РАСПОЛОЖЕНИЕ ДАННЫХ")
        locations_title.setObjectName("section_label")

        layout.addWidget(locations_title)

        self.locations_layout = QVBoxLayout()
        self.locations_layout.setSpacing(10)

        layout.addLayout(self.locations_layout)

        # Нижняя панель
        bottom = QHBoxLayout()

        self.status_label = QLabel("")
        self.status_label.setObjectName("description")
        self.status_label.setWordWrap(True)

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("save_settings_button")
        self.refresh_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.refresh_button.clicked.connect(self.refresh)

        bottom.addWidget(self.status_label, 1)
        bottom.addWidget(self.refresh_button)

        layout.addLayout(bottom)
        layout.addStretch()

        self.refresh()

    def _clear_locations(self):
        while self.locations_layout.count():
            item = self.locations_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def _create_location_card(self, location):
        card = QFrame()
        card.setObjectName("panel")

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(18, 15, 18, 15)
        card_layout.setSpacing(15)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        name = QLabel(location["name"])
        name.setObjectName("section_label")

        path = QLabel(str(location["path"]))
        path.setObjectName("description")
        path.setWordWrap(True)
        path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        details = QLabel(
            f'{location["size_text"]}  •  '
            f'{location["file_count"]} файлов'
        )
        details.setObjectName("description")

        if not location["exists"]:
            details.setText("Папка или файл пока не существуют.")

        elif location["errors"]:
            details.setText(
                f'{location["size_text"]}  •  '
                f'{location["file_count"]} файлов  •  '
                f'Ошибок доступа: {location["errors"]}'
            )

        info_layout.addWidget(name)
        info_layout.addWidget(path)
        info_layout.addWidget(details)

        open_button = QPushButton("Открыть")
        open_button.setObjectName("browse_button")
        open_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        open_button.setEnabled(location["exists"])

        open_button.clicked.connect(
            lambda checked=False, p=location["path"]: self.open_folder(p)
        )

        card_layout.addLayout(info_layout, 1)
        card_layout.addWidget(open_button)

        self.locations_layout.addWidget(card)

    def open_folder(self, path):
        path = Path(path)

        if not path.exists():
            QMessageBox.warning(
                self,                                                                                                   
                "Путь недоступен",
                f"Файл или папка не найдены:\n{path}"
            )
            return

        target = path if path.is_dir() else path.parent

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(target.resolve()))
        )

    def refresh(self):
        try:
            info = self.manager.get_storage_info()

            self.total_size_label.setText(
                f'Занято: {info["total_size_text"]}'
            )

            self.files_count_label.setText(
                f'Файлов: {info["total_files"]}'
            )

            self.disk_space_label.setText(
                f'Свободно на диске: {info["free_space_text"]} '
                f'из {info["total_disk_space_text"]}'
            )

            self._clear_locations()

            for location in info["locations"]:
                self._create_location_card(location)

            if info["total_errors"]:
                self.status_label.setText(
                    f'Не удалось прочитать некоторые элементы: '
                    f'{info["total_errors"]}.'
                )
            else:
                self.status_label.setText(
                    "Информация обновлена."
                )

        except Exception as error:
            self.status_label.setText(
                f"Ошибка чтения хранилища: {error}"
            )
