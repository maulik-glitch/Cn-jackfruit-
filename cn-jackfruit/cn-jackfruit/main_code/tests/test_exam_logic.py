import unittest

from exam_data import QUESTIONS, grade_answers, public_questions


class ExamLogicTests(unittest.TestCase):
    def test_public_questions_do_not_expose_answer_key(self):
        public = public_questions()
        self.assertEqual(len(public), len(QUESTIONS))
        self.assertTrue(all("answer" not in question for question in public))

    def test_grade_all_correct_answers(self):
        answers = {question["id"]: question["answer"] for question in QUESTIONS}
        result = grade_answers(answers)
        self.assertEqual(result["score"], len(QUESTIONS))
        self.assertEqual(result["percentage"], 100.0)

    def test_grade_empty_submission(self):
        result = grade_answers({})
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["total"], len(QUESTIONS))
        self.assertEqual(result["percentage"], 0.0)

    def test_answers_are_case_insensitive(self):
        answers = {question["id"].lower(): question["answer"].lower() for question in QUESTIONS}
        result = grade_answers(answers)
        self.assertEqual(result["score"], len(QUESTIONS))


if __name__ == "__main__":
    unittest.main()
