import tempfile
import time
import unittest
from pathlib import Path

from server import ExamService


class ExamServiceTests(unittest.TestCase):
    def make_service(self, duration=30):
        self.temp_dir = tempfile.TemporaryDirectory()
        return ExamService(duration, Path(self.temp_dir.name))

    def tearDown(self):
        if hasattr(self, "temp_dir"):
            self.temp_dir.cleanup()

    def test_hello_and_exam_delivery(self):
        service = self.make_service()
        welcome, status = service.handle({"type": "HELLO", "client_id": "student-1", "name": "Student 1"}, None)
        self.assertEqual(status, "ok")
        self.assertEqual(welcome["type"], "WELCOME")
        exam, status = service.handle({"type": "GET_EXAM"}, "student-1")
        self.assertEqual(status, "ok")
        self.assertEqual(exam["type"], "EXAM")
        self.assertTrue(exam["questions"])
        self.assertTrue(all("answer" not in question for question in exam["questions"]))

    def test_server_rejects_submission_after_deadline(self):
        service = self.make_service(duration=1)
        service.handle({"type": "HELLO", "client_id": "late-student", "name": "Late Student"}, None)
        service.handle({"type": "GET_EXAM"}, "late-student")
        time.sleep(1.05)
        result, status = service.handle({"type": "SUBMIT", "answers": {}}, "late-student")
        self.assertEqual(status, "time_expired")
        self.assertTrue(result["expired"])
        self.assertEqual(result["score"], 0)

    def test_duplicate_submission_is_rejected(self):
        service = self.make_service()
        service.handle({"type": "HELLO", "client_id": "student-2", "name": "Student 2"}, None)
        service.handle({"type": "GET_EXAM"}, "student-2")
        result, status = service.handle({"type": "SUBMIT", "answers": {}}, "student-2")
        self.assertEqual(status, "submitted")
        response, status = service.handle({"type": "SUBMIT", "answers": {}}, "student-2")
        self.assertEqual(status, "rejected")
        self.assertEqual(response["type"], "ERROR")


if __name__ == "__main__":
    unittest.main()
