import sqlite3
from pathlib import Path


class LectureRepository:

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._initialize_database()

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS lectures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (
                        strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
                    ),
                    status TEXT NOT NULL DEFAULT 'draft',
                    document_path TEXT,
                    duration_seconds INTEGER,
                    summary TEXT
                )
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_lectures_created_at
                ON lectures(created_at)
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_lectures_subject
                ON lectures(subject)
            """)

    def list_lectures(self, search_text="", subject=None):
        query = """
            SELECT *
            FROM lectures
            WHERE 1 = 1
        """

        parameters = []

        if search_text.strip():
            query += """
                AND (
                    title LIKE ?
                    OR subject LIKE ?
                )
            """

            search = f"%{search_text.strip()}%"
            parameters.extend([search, search])

        if subject:
            query += " AND subject = ?"
            parameters.append(subject)

        query += " ORDER BY created_at DESC, id DESC"

        with self._connect() as connection:
            rows = connection.execute(
                query,
                parameters
            ).fetchall()

        return [dict(row) for row in rows]

    def get_counts(self):
        with self._connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM lectures"
            ).fetchone()[0]

            completed = connection.execute(
                "SELECT COUNT(*) FROM lectures WHERE status = 'completed'"
            ).fetchone()[0]

        return {
            "total": total,
            "completed": completed
        }

    def get_subjects(self):
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT DISTINCT subject
                FROM lectures
                ORDER BY subject COLLATE NOCASE
            """).fetchall()

        return [row["subject"] for row in rows]

    def get_lecture(self, lecture_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM lectures WHERE id = ?",
                (lecture_id,)
            ).fetchone()

        return dict(row) if row else None

    def delete_lecture(self, lecture_id):
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM lectures WHERE id = ?",
                (lecture_id,)
            )

        return cursor.rowcount > 0

    def rename_subject(self, old_name, new_name):
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE lectures
                SET subject = ?
                WHERE subject = ?
                """,
                (new_name, old_name)
            )

        return cursor.rowcount