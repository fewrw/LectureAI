
import tempfile
import unittest
from pathlib import Path

from storage.lecture_repository import LectureRepository


class TestLectureRepository(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        database_path = Path(self.temp_dir.name) / "lectures.db"

        self.repository = LectureRepository(database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_get_lecture(self):
        lecture_id = self.repository.create_lecture(
            "Mathematics",
            "Linear algebra"
        )

        lecture = self.repository.get_lecture(lecture_id)

        self.assertIsNotNone(lecture)
        self.assertEqual(lecture["title"], "Linear algebra")
        self.assertEqual(lecture["subject"], "Mathematics")
        self.assertEqual(lecture["status"], "draft")
        self.assertIsNotNone(lecture["created_at"])

    def test_search_by_title(self):
        self.repository.create_lecture(
            "Mathematics",
            "Linear algebra"
        )

        self.repository.create_lecture(
            "Physics",
            "Newton laws"
        )

        results = self.repository.list_lectures(
            search_text="algebra"
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Linear algebra")

    def test_search_by_subject(self):
        self.repository.create_lecture(
            "Mathematics",
            "Linear algebra"
        )

        self.repository.create_lecture(
            "Physics",
            "Newton laws"
        )

        results = self.repository.list_lectures(
            search_text="Physics"
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["subject"], "Physics")

    def test_filter_by_subject(self):
        self.repository.create_lecture(
            "Mathematics",
            "Linear algebra"
        )

        self.repository.create_lecture(
            "Physics",
            "Newton laws"
        )

        results = self.repository.list_lectures(
            subject="Mathematics"
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["subject"], "Mathematics")

    def test_rename_subject(self):
        self.repository.create_lecture(
            "Mathematics",
            "Linear algebra"
        )

        self.repository.create_lecture(
            "Mathematics",
            "Calculus"
        )

        changed = self.repository.rename_subject(
            "Mathematics",
            "Advanced Mathematics"
        )

        self.assertEqual(changed, 2)

        lectures = self.repository.list_lectures()

        for lecture in lectures:
            self.assertEqual(
                lecture["subject"],
                "Advanced Mathematics"
            )

    def test_delete_lecture(self):
        lecture_id = self.repository.create_lecture(
            "Physics",
            "Newton laws"
        )

        deleted = self.repository.delete_lecture(lecture_id)

        self.assertTrue(deleted)
        self.assertIsNone(
            self.repository.get_lecture(lecture_id)
        )

        # Повторное удаление должно вернуть False.
        self.assertFalse(
            self.repository.delete_lecture(lecture_id)
        )

    def test_get_counts(self):
        self.repository.create_lecture(
            "Mathematics",
            "Linear algebra"
        )

        self.repository.create_lecture(
            "Physics",
            "Newton laws",
            status="completed"
        )

        counts = self.repository.get_counts()

        self.assertEqual(counts["total"], 2)
        self.assertEqual(counts["completed"], 1)

    def test_get_subjects(self):
        self.repository.create_lecture(
            "Mathematics",
            "Linear algebra"
        )

        self.repository.create_lecture(
            "Physics",
            "Newton laws"
        )

        subjects = self.repository.get_subjects()

        self.assertEqual(
            set(subjects),
            {"Mathematics", "Physics"}
        )


if __name__ == "__main__":
    unittest.main()
