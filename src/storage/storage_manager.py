
import shutil
from pathlib import Path


class StorageManager:

    def __init__(self, paths):
        self.paths = paths

    @staticmethod
    def _format_size(size):
        units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
        value = float(size)

        for unit in units:
            if value < 1024 or unit == "ТБ":
                return f"{value:.1f} {unit}"
            value /= 1024

        return f"{value:.1f} ТБ"

    def _scan_path(self, path, seen_files):
        path = Path(path)

        if not path.exists():
            return 0, 0, 0

        if path.is_file():
            try:
                resolved = path.resolve()

                if resolved in seen_files:
                    return 0, 0, 0

                seen_files.add(resolved)
                return path.stat().st_size, 1, 0

            except OSError:
                return 0, 0, 1

        total_size = 0
        file_count = 0
        errors = 0

        try:
            entries = list(path.iterdir())
        except OSError:
            return 0, 0, 1

        for entry in entries:
            try:
                if entry.is_symlink():
                    continue

                if entry.is_dir():
                    size, files, failed = self._scan_path(
                        entry,
                        seen_files
                    )
                elif entry.is_file():
                    resolved = entry.resolve()

                    if resolved in seen_files:
                        continue

                    seen_files.add(resolved)

                    size = entry.stat().st_size
                    files = 1
                    failed = 0
                else:
                    continue

                total_size += size
                file_count += files
                errors += failed

            except OSError:
                errors += 1

        return total_size, file_count, errors

    def get_storage_info(self):
        locations = [
            {
                "name": "Конспекты",
                "path": self.paths.lectures_directory,
            },
            {
                "name": "AI-модели",
                "path": self.paths.models_directory,
            },
            {
                "name": "База данных и предметы",
                "path": self.paths.storage,
            },
            {
                "name": "Журналы приложения",
                "path": self.paths.logs,
            },
            {
                "name": "Настройки приложения",
                "path": self.paths.settings_file,
            },
        ]

        seen_files = set()
        total_size = 0
        total_files = 0
        total_errors = 0

        for location in locations:
            path = Path(location["path"])

            size, files, errors = self._scan_path(
                path,
                seen_files
            )

            location["size_bytes"] = size
            location["size_text"] = self._format_size(size)
            location["file_count"] = files
            location["exists"] = path.exists()
            location["errors"] = errors

            total_size += size
            total_files += files
            total_errors += errors

        # Определяем свободное место на диске
        disk_path = Path(self.paths.root)

        try:
            disk_usage = shutil.disk_usage(disk_path)
            free_space = disk_usage.free
            total_disk_space = disk_usage.total
        except OSError:
            free_space = None
            total_disk_space = None

        return {
            "locations": locations,
            "total_size": total_size,
            "total_size_text": self._format_size(total_size),
            "total_files": total_files,
            "total_errors": total_errors,
            "free_space": free_space,
            "free_space_text": (
                self._format_size(free_space)
                if free_space is not None
                else "Недоступно"
            ),
            "total_disk_space": total_disk_space,
            "total_disk_space_text": (
                self._format_size(total_disk_space)
                if total_disk_space is not None
                else "Недоступно"
            ),
        }
