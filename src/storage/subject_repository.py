import json
from pathlib import Path


class SubjectRepository:
    """Отвечает только за чтение и сохранение списка предметов."""

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def load(self):
        if not self.file_path.exists():
            return [], None

        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))

            if not isinstance(data, dict):
                return [], None

            raw_subjects = data.get("subjects", [])
            if not isinstance(raw_subjects, list):
                return [], None

            subjects = [
                item.strip()
                for item in raw_subjects
                if isinstance(item, str) and item.strip()
            ]

            selected = data.get("selected_subject")
            if (
                not isinstance(selected, int)
                or isinstance(selected, bool)
                or not 0 <= selected < len(subjects)
            ):
                selected = None

            return subjects, selected

        except (json.JSONDecodeError, OSError):
            # Повреждённый файл не перезаписываем автоматически.
            return [], None

    def save(self, subjects, selected_subject):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "subjects": subjects,
            "selected_subject": selected_subject,
        }

        temporary_path = self.file_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
        temporary_path.replace(self.file_path)
