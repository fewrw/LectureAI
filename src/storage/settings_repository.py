
import json
from pathlib import Path


class SettingsRepository:

    def __init__(self, file_path: Path, defaults: dict):
        self.file_path = Path(file_path)
        self.defaults = defaults.copy()

    def load(self):
        if not self.file_path.exists():
            return self.defaults.copy()

        try:
            data = json.loads(
                self.file_path.read_text(encoding="utf-8")
            )

            if not isinstance(data, dict):
                return self.defaults.copy()

            settings = self.defaults.copy()

            for key, default_value in self.defaults.items():
                if key not in data:
                    continue

                value = data[key]

                # bool проверяем отдельно, потому что bool
                # является подклассом int в Python.
                if isinstance(default_value, bool):
                    if isinstance(value, bool):
                        settings[key] = value

                elif isinstance(default_value, int):
                    if isinstance(value, int) and not isinstance(value, bool):
                        settings[key] = value

                elif isinstance(default_value, float):
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        settings[key] = float(value)

                elif isinstance(default_value, str):
                    if isinstance(value, str) and value.strip():
                        settings[key] = value

            return settings

        except (json.JSONDecodeError, OSError):
            return self.defaults.copy()

    def save(self, settings):
        if not isinstance(settings, dict):
            raise TypeError("Настройки должны быть словарём")

        validated_settings = self.defaults.copy()

        for key, default_value in self.defaults.items():
            if key not in settings:
                continue

            value = settings[key]

            if isinstance(default_value, bool):
                if isinstance(value, bool):
                    validated_settings[key] = value

            elif isinstance(default_value, int):
                if isinstance(value, int) and not isinstance(value, bool):
                    validated_settings[key] = value

            elif isinstance(default_value, float):
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    validated_settings[key] = float(value)

            elif isinstance(default_value, str):
                if isinstance(value, str) and value.strip():
                    validated_settings[key] = value

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        temporary_path = self.file_path.with_suffix(".tmp")

        temporary_path.write_text(
            json.dumps(
                validated_settings,
                ensure_ascii=False,
                indent=4
            ),
            encoding="utf-8"
        )

        temporary_path.replace(self.file_path)
