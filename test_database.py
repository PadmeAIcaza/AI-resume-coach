import json
import tempfile
import unittest
from pathlib import Path

from database import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_directory.name) / "test.sqlite3")
        self.database.initialize()

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_saves_resume_analysis_and_job_description(self):
        analysis_id = self.database.save_resume_analysis("resume", "job", {"match_score": 82})
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT ra.id, ra.analysis_json, jd.content
                   FROM resume_analyses AS ra
                   JOIN job_descriptions AS jd ON jd.id = ra.job_description_id"""
            ).fetchone()
        self.assertEqual(row["id"], analysis_id)
        self.assertEqual(row["content"], "job")
        self.assertEqual(json.loads(row["analysis_json"])["match_score"], 82)

    def test_saves_questions_answer_and_feedback_relationships(self):
        question = {
            "question": "Tell me about a project.",
            "category": "Behavioral",
            "focus": "Communication",
        }
        question_ids = self.database.save_interview_questions("resume", "job", [question])
        answer_id, feedback_id = self.database.save_answer_and_feedback(
            "resume", "job", question["question"], "My answer", {"clarity": {"score": 4}})
        with self.database.connect() as connection:
            answer = connection.execute(
                "SELECT * FROM user_answers WHERE id = ?", (answer_id,)
            ).fetchone()
            feedback = connection.execute(
                "SELECT * FROM ai_feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
        self.assertEqual(answer["interview_question_id"], question_ids[0])
        self.assertEqual(answer["answer_text"], "My answer")
        self.assertEqual(feedback["user_answer_id"], answer_id)
        self.assertEqual(json.loads(feedback["feedback_json"])["clarity"]["score"], 4)


if __name__ == "__main__":
    unittest.main()
