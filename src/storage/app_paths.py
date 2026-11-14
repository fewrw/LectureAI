
import os
import shutil
from pathlib import Path


class AppPaths:

    def __init__(self):
        local_app_data = os.getenv("LOCALAPPDATA")

        if local_app_data:
            base_path = Path(local_app_data)
        else:
            base_path = Path.home() / "AppData" / "Local"

        self.root = base_path / "LectureAI"

        # Внутренние данные приложения
        self.storage = self.root / "storage"
        self.logs = self.root / "logs"

        # Папки по умолчанию
        self.lectures = self.root / "lectures"
        self.models = self.root / "models"

        # Файлы настроек и базы данных
        self.settings_file = self.root / "settings.json"
        self.subjects_file = self.storage / "subjects.json"
        self.database_file = self.storage / "lectures.db"

        self._create_directories()
        self._migrate_legacy_data()

    def _create_directories(self):
        directories = [
            self.root,
            self.storage,
            self.logs,
            self.lectures,
            self.models,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _migrate_legacy_data(self):
        """
        Переносит старые пользовательские данные
        из папки проекта в LocalAppData.

        Старые файлы не удаляются.
        """

        project_root = Path(__file__).resolve().parents[2]
        old_storage = project_root / "src" / "storage"

        old_subjects = old_storage / "subjects.json"
        old_database = old_storage / "lectures.db"

        if old_subjects.exists() and not self.subjects_file.exists():
            shutil.copy2(
                old_subjects,
                self.subjects_file,
            )

        if old_database.exists() and not self.database_file.exists():
            shutil.copy2(
                old_database,
                self.database_file,
            )
