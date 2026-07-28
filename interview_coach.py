import os
from typing import List
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# represents ONE interview question
class InterviewQuestion(BaseModel):
    question: str = Field(description="A concise interview question tailored to the role and candidate.")
    category: str = Field(description="Question category, such as Behavioral, Technical, or Role-specific.")
    focus: str = Field(description="A short explanation of what the interviewer is evaluating.")

# Gemini returns a set of questions (question/category/focus) and pydantic converts that into a list of InterviewQuestions
class InterviewQuestionSet(BaseModel):
    # the response should contain between 8 and 10 questions
    questions: List[InterviewQuestion] = Field(min_length=8, max_length=10, description="A balanced set of tailored interview questions.")

# this represents ONE grading category (clarity/technical depth/relevance/STAR)
class FeedbackDimension(BaseModel):
    score: int = Field(ge=1, le=5, description="Score from 1 (weak) to 5 (excellent).")
    feedback: str = Field(description="Specific, constructive feedback supported by the answer.")

class InterviewFeedback(BaseModel):
    # it gives a score and feedback for each grading category (JSON -> Pydantic)
    relevance: FeedbackDimension
    clarity: FeedbackDimension
    technical_depth: FeedbackDimension
    star_format: FeedbackDimension
    # it gives areas to improve + an improved version of the given answer
    areas_to_improve: List[str] = Field(min_length=1, description="Prioritized, actionable suggestions for improving this answer.") # must provide at leats one improvement
    improved_answer: str = Field(description=("A stronger example answer that preserves the candidate's facts and does not invent experience."))


class InterviewCoach:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    def _generate_structured(self, prompt: str, schema: type[BaseModel], temperature: float = 0.2):
        if not self.api_key:
            raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY to your .env file.")

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature, response_mime_type="application/json",  response_schema=schema))

        if response.parsed:
            return response.parsed
        if response.text:
            return schema.model_validate_json(response.text)
        raise RuntimeError("Gemini returned an empty response. Please try again.")

    def generate_questions(self, resume_text: str, job_description: str) -> InterviewQuestionSet:
        prompt = f"""
You are an expert interview coach. Create 6 interview questions tailored to the
candidate's resume and the target job.

Requirements:
- Include a useful mix of behavioral, technical, and role-specific questions.
- Ground questions in the job requirements and the candidate's actual experience.
- Probe important gaps or risks tactfully, without assuming missing experience.
- Make each question realistic, specific, and answerable in a live interview.
- Do not invent facts about the candidate or employer.

RESUME:
---BEGIN RESUME---
{resume_text}
---END RESUME---

JOB DESCRIPTION:
---BEGIN JOB DESCRIPTION---
{job_description}
---END JOB DESCRIPTION---
"""
        return self._generate_structured(prompt, InterviewQuestionSet, temperature=0.35)

    def evaluate_answer(self, resume_text: str, job_description: str, question: str, answer: str,) -> InterviewFeedback:
        prompt = f"""
You are a candid, supportive interview coach. Evaluate the candidate's answer
to the supplied interview question in the context of their resume and target job.

Score relevance, clarity, technical depth, and STAR format from 1 to 5. Explain
each score with concrete references to the answer. For STAR, assess Situation,
Task, Action, and Result; if STAR is not naturally appropriate for the question,
explain what structure would work better instead of penalizing it unfairly.
Provide prioritized areas to improve and a stronger example answer. Preserve only
facts the candidate supplied in the resume or answer. Never invent metrics,
technologies, responsibilities, or outcomes. When a useful detail is missing, use
a bracketed prompt such as "[add the measurable result]".

INTERVIEW QUESTION:
{question}

CANDIDATE ANSWER:
---BEGIN ANSWER---
{answer}
---END ANSWER---

RESUME:
---BEGIN RESUME---
{resume_text}
---END RESUME---

JOB DESCRIPTION:
---BEGIN JOB DESCRIPTION---
{job_description}
---END JOB DESCRIPTION---
"""
        return self._generate_structured(prompt, InterviewFeedback)
