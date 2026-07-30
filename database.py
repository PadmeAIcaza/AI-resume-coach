import json
import sqlite3 # imports Python's SQLite built-in library
from contextlib import contextmanager # let us create our own with blocks
from pathlib import Path
from typing import Any, Iterable, Iterator # any data type, anything you can loop over, "one at a time" thing

# Python stores all SQL commands inside a multi-line string
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS job_descriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS resume_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_description_id INTEGER NOT NULL,
    resume_text TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS interview_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_description_id INTEGER NOT NULL,
    resume_text TEXT NOT NULL,
    question TEXT NOT NULL,
    category TEXT NOT NULL,
    focus TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS practiced_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interview_question_id INTEGER NOT NULL UNIQUE,
    practiced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_question_id) REFERENCES interview_questions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS user_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interview_question_id INTEGER,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_question_id) REFERENCES interview_questions(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS ai_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_answer_id INTEGER NOT NULL,
    feedback_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_answer_id) REFERENCES user_answers(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_resume_analyses_job ON resume_analyses(job_description_id);
CREATE INDEX IF NOT EXISTS idx_interview_questions_job ON interview_questions(job_description_id);
CREATE INDEX IF NOT EXISTS idx_practiced_questions_question ON practiced_questions(interview_question_id);
CREATE INDEX IF NOT EXISTS idx_user_answers_question ON user_answers(interview_question_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_answer ON ai_feedback(user_answer_id);
"""
# indexes help retrieval queries run much faster because that way SQLite doesnt have to scan the whole table

class Database:
    TABLES = (
        "job_descriptions",
        "resume_analyses",
        "interview_questions",
        "practiced_questions",
        "user_answers",
        "ai_feedback",
    )

    def __init__(self, path: str | Path):
        self.path = Path(path)

    # open a connection to the database, let the rest of the program use it, then close it afterward
    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        # parents=True -> if several folders are missing, python creates all missing folders.
        # exists_ok=True guarantees that the folder for the database exists before trying to create the database file
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path) # opens the SQLite databse. if it doesnt exist, SQLite creates it. The returned object is a database connection
        connection.row_factory = sqlite3.Row # makes query result easier to read
        connection.execute("PRAGMA foreign_keys = ON") # enables foreign key enforcement for this connection.
        try:
            with connection: # commits changes if everything succeeds. Rolls back changes if an error happens
                yield connection # "here is a connection, give it to whoever called me"
        finally: # closes the database even if the code crashes
            connection.close()

    # creates the tables
    def initialize(self) -> None:
        # our own with block
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @staticmethod
    # this converts Python objects into JSON strings that SQLite can store
    def _json(value: Any) -> str:
        # "does this object have a method named model_dump?"
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json") # if it is a Pydantic model, converts into a normal dictionary
        return json.dumps(value, ensure_ascii=False) # converts the dict into a JSON string

    @staticmethod
    def _create_job_description(connection: sqlite3.Connection, content: str) -> int:
        cursor = connection.execute(
            "INSERT INTO job_descriptions (content) VALUES (?)", (content,)
        )
        return int(cursor.lastrowid)

    def save_resume_analysis(self, resume_text: str, job_description: str, analysis: Any) -> int:
        with self.connect() as connection:
            job_id = self._create_job_description(connection, job_description)
            cursor = connection.execute(
                """INSERT INTO resume_analyses
                   (job_description_id, resume_text, analysis_json)
                   VALUES (?, ?, ?)""",
                (job_id, resume_text, self._json(analysis)),
            )
            return int(cursor.lastrowid)

    def save_interview_questions(self, resume_text: str, job_description: str, questions: Iterable[Any]) -> list[int]:
        with self.connect() as connection:
            job_id = self._create_job_description(connection, job_description)
            ids = []
            for item in questions:
                data = item.model_dump() if hasattr(item, "model_dump") else item
                cursor = connection.execute(
                    """INSERT INTO interview_questions
                       (job_description_id, resume_text, question, category, focus)
                       VALUES (?, ?, ?, ?, ?)""",
                    (job_id, resume_text, data["question"], data["category"], data["focus"]),
                )
                ids.append(int(cursor.lastrowid))
            return ids

    def save_answer_and_feedback(self, resume_text: str, job_description: str, question: str, answer: str, feedback: Any) -> tuple[int, int]:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT iq.id
                   FROM interview_questions AS iq
                   JOIN job_descriptions AS jd ON jd.id = iq.job_description_id
                   WHERE iq.resume_text = ? AND jd.content = ? AND iq.question = ?
                   ORDER BY iq.id DESC LIMIT 1""",
                (resume_text, job_description, question)
            ).fetchone()
            question_id = int(row["id"]) if row else None
            answer_cursor = connection.execute(
                """INSERT INTO user_answers
                   (interview_question_id, question_text, answer_text)
                   VALUES (?, ?, ?)""",
                (question_id, question, answer)
            )
            answer_id = int(answer_cursor.lastrowid)
            feedback_cursor = connection.execute("INSERT INTO ai_feedback (user_answer_id, feedback_json) VALUES (?, ?)", (answer_id, self._json(feedback)))
            return answer_id, int(feedback_cursor.lastrowid)

    def export_all(self) -> dict[str, list[dict[str, Any]]]:
        exported: dict[str, list[dict[str, Any]]] = {}
        with self.connect() as connection:
            for table in self.TABLES:
                rows = [dict(row) for row in connection.execute(
                    f"SELECT * FROM {table} ORDER BY id"
                ).fetchall()]
                for row in rows:
                    for field in ("analysis_json", "feedback_json"):
                        if field in row:
                            row[field.removesuffix("_json")] = json.loads(row.pop(field))
                exported[table] = rows
        return exported

    def record_counts(self) -> dict[str, int]:
        with self.connect() as connection:
            return {table: int(connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0])
                for table in self.TABLES
            }

    def mark_question_practiced(self, resume_text: str, job_description: str, question: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT iq.id
                   FROM interview_questions AS iq
                   JOIN job_descriptions AS jd ON jd.id = iq.job_description_id
                   WHERE iq.resume_text = ? AND jd.content = ? AND iq.question = ?
                   ORDER BY iq.id DESC LIMIT 1""",
                (resume_text, job_description, question),
            ).fetchone()
            if row is None:
                return False
            connection.execute(
                """INSERT INTO practiced_questions (interview_question_id)
                   VALUES (?)
                   ON CONFLICT(interview_question_id)
                   DO UPDATE SET practiced_at = CURRENT_TIMESTAMP""",
                (row["id"],),
            )
            return True

    def history(self) -> dict[str, list[dict[str, Any]]]:
        with self.connect() as connection:
            job_descriptions = [
                dict(row)
                for row in connection.execute(
                    """SELECT ra.id AS analysis_id, jd.content,
                              ra.created_at
                       FROM resume_analyses AS ra
                       JOIN job_descriptions AS jd
                         ON jd.id = ra.job_description_id
                       ORDER BY ra.created_at DESC, ra.id DESC"""
                ).fetchall()
            ]
            practiced_questions = [
                dict(row)
                for row in connection.execute(
                    """SELECT pq.id AS practice_id, iq.question,
                              iq.category, iq.focus,
                              jd.content AS job_description,
                              pq.practiced_at,
                              EXISTS(
                                  SELECT 1
                                  FROM user_answers AS ua
                                  JOIN ai_feedback AS af
                                    ON af.user_answer_id = ua.id
                                  WHERE ua.interview_question_id = iq.id
                              ) AS has_feedback
                       FROM practiced_questions AS pq
                       JOIN interview_questions AS iq
                         ON iq.id = pq.interview_question_id
                       JOIN job_descriptions AS jd
                         ON jd.id = iq.job_description_id
                       ORDER BY pq.practiced_at DESC, pq.id DESC"""
                ).fetchall()
            ]
        return {
            "job_descriptions": job_descriptions,
            "practiced_questions": practiced_questions,
        }

    def analysis_detail(self, analysis_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT ra.id, ra.resume_text, ra.analysis_json,
                          ra.created_at, jd.content AS job_description
                   FROM resume_analyses AS ra
                   JOIN job_descriptions AS jd
                     ON jd.id = ra.job_description_id
                   WHERE ra.id = ?""",
                (analysis_id,),
            ).fetchone()
        if row is None:
            return None
        detail = dict(row)
        detail["analysis"] = json.loads(detail.pop("analysis_json"))
        return detail

    def practice_detail(self, practice_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT pq.id, pq.practiced_at, iq.question,
                          iq.category, iq.focus, iq.resume_text,
                          jd.content AS job_description
                   FROM practiced_questions AS pq
                   JOIN interview_questions AS iq
                     ON iq.id = pq.interview_question_id
                   JOIN job_descriptions AS jd
                     ON jd.id = iq.job_description_id
                   WHERE pq.id = ?""",
                (practice_id,),
            ).fetchone()
            if row is None:
                return None
            detail = dict(row)
            feedback = connection.execute(
                """SELECT ua.answer_text, ua.created_at AS answered_at,
                          af.feedback_json
                   FROM user_answers AS ua
                   JOIN ai_feedback AS af ON af.user_answer_id = ua.id
                   JOIN practiced_questions AS pq
                     ON pq.interview_question_id = ua.interview_question_id
                   WHERE pq.id = ?
                   ORDER BY ua.created_at DESC, ua.id DESC
                   LIMIT 1""",
                (practice_id,),
            ).fetchone()
        if feedback:
            detail["answer"] = feedback["answer_text"]
            detail["answered_at"] = feedback["answered_at"]
            detail["feedback"] = json.loads(feedback["feedback_json"])
        else:
            detail["answer"] = None
            detail["feedback"] = None
        return detail

    def delete_all(self) -> int:
        with self.connect() as connection:
            deleted = sum(int(connection.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    ) for table in self.TABLES
            )
            for table in reversed(self.TABLES):
                connection.execute(f"DELETE FROM {table}")
            connection.execute(
                "DELETE FROM sqlite_sequence WHERE name IN (?, ?, ?, ?, ?, ?)",
                self.TABLES,
            )
        return deleted
