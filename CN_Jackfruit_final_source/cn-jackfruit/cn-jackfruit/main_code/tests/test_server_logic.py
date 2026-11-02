import csv
import tempfile
import time
import unittest
from pathlib import Path

from server import ExamService


class ExamServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = ExamService(30, Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def register(self, client_id="student-1", name="Student 1"):
        return self.service.handle(
            {"type": "HELLO", "client_id": client_id, "name": name}, None
        )

    def test_hello_and_exam_delivery(self):
        welcome, status = self.register()
        self.assertEqual(status, "ok")
        self.assertEqual(welcome["type"], "WELCOME")
        exam, status = self.service.handle({"type": "GET_EXAM"}, "student-1")
        self.assertEqual(status, "ok")
        self.assertEqual(exam["type"], "EXAM")
        self.assertTrue(exam["questions"])
        self.assertGreater(exam["remaining_seconds"], 0)
        self.assertTrue(all("answer" not in question for question in exam["questions"]))

    def test_ping_works_for_registered_client(self):
        self.register()
        response, status = self.service.handle({"type": "PING"}, "student-1")
        self.assertEqual(status, "ok")
        self.assertEqual(response["type"], "PONG")

    def test_ping_requires_registration(self):
        response, status = self.service.handle({"type": "PING"}, None)
        self.assertEqual(status, "rejected")
        self.assertEqual(response["type"], "ERROR")

    def test_duplicate_client_id_is_rejected(self):
        self.register()
        response, status = self.register()
        self.assertEqual(status, "rejected")
        self.assertEqual(response["type"], "ERROR")

    def test_server_rejects_submission_after_deadline(self):
        service = ExamService(1, Path(self.temp_dir.name) / "expired")
        service.handle({"type": "HELLO", "client_id": "late-student", "name": "Late Student"}, None)
        service.handle({"type": "GET_EXAM"}, "late-student")
        time.sleep(1.05)
        result, status = service.handle({"type": "SUBMIT", "answers": {}}, "late-student")
        self.assertEqual(status, "time_expired")
        self.assertTrue(result["expired"])
        self.assertEqual(result["score"], 0)

    def test_duplicate_submission_is_rejected(self):
        self.register("student-2", "Student 2")
        self.service.handle({"type": "GET_EXAM"}, "student-2")
        result, status = self.service.handle({"type": "SUBMIT", "answers": {}}, "student-2")
        self.assertEqual(status, "submitted")
        response, status = self.service.handle({"type": "SUBMIT", "answers": {}}, "student-2")
        self.assertEqual(status, "rejected")
        self.assertEqual(response["type"], "ERROR")

    def test_server_result_is_saved_to_csv(self):
        self.register()
        self.service.handle({"type": "GET_EXAM"}, "student-1")
        result, _ = self.service.handle({"type": "SUBMIT", "answers": {}}, "student-1")
        self.service.record_result(result, ("127.0.0.1", 51000))
        with self.service.results_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["student_name"], "Student 1")
        self.assertEqual(rows[0]["score"], "0")
        self.assertEqual(rows[0]["total"], str(len(result["correct_answers"])))


if __name__ == "__main__":
    unittest.main()
