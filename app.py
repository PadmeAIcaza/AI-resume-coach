import os
from typing import List # used for setting data types
from dotenv import load_dotenv # loads environment variables
from flask import Flask, render_template, request
from google import genai
from google.genai import types # configure gemini requests
from pydantic import BaseModel, Field # define structured AI output with validation, add validation rules and descriptions to field models
from werkzeug.exceptions import RequestEntityTooLarge # werkzeug is used by Flask for things like file uploads
from interview_coach import InterviewCoach
from pdf_utils import ResumeUploadError, extract_pdf_text # this py file receives the PDF file

load_dotenv()

# creates the web application
app = Flask(__name__) # __name__ tells Flask where the app file is located
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 # 5,242,880 bytes (RequestEntityTooLarge)

MAX_INPUT_LENGTH = 30000

# creates a new data type called BulletPoint
class BulletPoint(BaseModel):
    # original and improved bullets must be strings. Field is telling Gemini instructions on how to receive and how to respond to the given bullets
    original: str = Field(description="The original resume bullet, or a short description if none exists.")
    improved: str = Field(description="A stronger, truthful rewrite using an action verb and measurable impact where possible.")
    # BulletPoint(original="Built a website.", improved="Developed a responsive web application using Flask.")

# this is the entire AI response
class ResumeAnalysis(BaseModel):
    # match score must be an int. Fields tells Gemini what the match score is, and that the minimum score is 0, maximum is 100. Everything sent by Gemini that is out of those bounds is invalid.
    match_score: int = Field(ge=0, le=100, description="Overall percentage match between the resume and job description.")
    # everything here must be sent as a string.
    summary: str = Field(description="A concise explanation of the match score.")
    # it will retrieve all matching skills from the resume and job description (as a list of strings), and they have to be sent as a string
    matching_skills: List[str] = Field(description="Skills required by the job that are supported by the resume.")
    missing_keywords: List[str] = Field(description="Important job-description keywords not supported by the resume.")
    improvements: List[str] = Field(description="Specific, prioritized improvements tailored to this job.")
    # list of (original, improved). Needed to not loose the original bullet.
    stronger_bullet_points: List[BulletPoint] = Field(description="Two to five stronger rewrites of existing resume bullet points.")

def _gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY to your .env file.")
    return genai.Client(api_key=api_key)


def _generate_structured(prompt: str, schema: type[BaseModel], temperature: float = 0.2):
    # keep a strong reference to the client until the request has completed.
    client = _gemini_client()
    # everything inside the parentheses tells Gemini what to do. It tells the model of Gemini that is using, it sends the prompt, and configures how Gemini should answer (temperature=0.2 controls randomness -> 0.0 is very predictble, 1.0 is very creative)
    # MIME type tells Gemini that we want a response in a JSON format (that looks like our ResumeAnalysis) so it doesnt just send "nice resume".
    # Response schema is basically handing the blueprint of ResumeAnalysis to Gemini. "Return data exaclty like this" instead of making up its own format
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature, response_mime_type="application/json", response_schema=schema))
    if response.parsed:
        return response.parsed
    if response.text:
        return schema.model_validate_json(response.text)
    raise RuntimeError("Gemini returned an empty response. Please try again.")


# heart of the entire project. This is the function that talks with Gemini
def analyze_with_gemini(resume_text: str, job_description: str) -> ResumeAnalysis: # when this function finishes, it will return a ResumeAnalysis object
    # prompt engineeringgg !!
    prompt = f"""
You are an expert resume coach and applicant-tracking-system analyst.
Compare the resume with the job description and return a candid, evidence-based
analysis.

Rules:
- Count a skill as matching only when the resume provides evidence for it.
- Missing keywords must be important to the job and absent from the resume.
- Never invent experience, credentials, employers, dates, metrics, or skills.
- Rewritten bullets must preserve the candidate's facts. If a useful metric is
  unavailable, improve clarity and impact without fabricating one.
- Keep every recommendation specific and actionable.

RESUME:
---BEGIN RESUME---
{resume_text}
---END RESUME---

JOB DESCRIPTION:
---BEGIN JOB DESCRIPTION---
{job_description}
---END JOB DESCRIPTION---
"""

    return _generate_structured(prompt, ResumeAnalysis)


@app.route("/")
def home():
    return render_template("index.html")

# sends to the results page and gets the resume and job description (POST)
@app.route("/analyze", methods=["POST"])
def analyze():
    # request.form.get reads the resume/job description text (.form.get only looks at the HTML form data and "resume"/"job_description" must match the name attribute in the HTML form
    resume_text = request.form.get("resume", "").strip()
    job_description = request.form.get("job_description", "").strip()
    # reads the resume file uploaded into the app
    resume_file = request.files.get("resume_file")

    # if all entries (especially resume_text and resume_file entries) are non-empty (filling both is not allowed)
    if resume_text and resume_file and resume_file.filename:
        return render_template("index.html", error="Use either pasted resume text or a PDF upload, not both.", resume=resume_text, job_description=job_description)

    if resume_file and resume_file.filename:
        try:
            resume_text = extract_pdf_text(resume_file) # extract pdf text (may give an error)
        except ResumeUploadError as exc: # if it is empty, show exception
            return render_template("index.html", error=str(exc), resume=resume_text, job_description=job_description)

    if not resume_text or not job_description:
        return render_template("index.html", error="Please provide a resume and a job description.", resume=resume_text, job_description=job_description)

    # checks if the input is within the bounds (less than 30000)
    if len(resume_text) > MAX_INPUT_LENGTH or len(job_description) > MAX_INPUT_LENGTH:
        return render_template("index.html", error="Each field must be 30,000 characters or fewer.", resume=resume_text, job_description=job_description)

    try:
        # calls function that returns ResumeAnalysis and is stored in feedback
        feedback = analyze_with_gemini(resume_text, job_description)
    except Exception as exc: # if anything inside try fails, give an error
        app.logger.exception("Resume analysis failed")
        message = (
            str(exc)
            if isinstance(exc, RuntimeError) # if this is a runtime error
            else "Gemini could not analyze the resume right now. Please try again.") # else, print generic message
        return render_template("index.html", error=message, resume=resume_text, job_description=job_description)

    return render_template("results.html", feedback=feedback, resume=resume_text, job_description=job_description)


def _valid_coach_inputs(resume_text: str, job_description: str) -> str | None:
    if not resume_text or not job_description:
        return "Resume and job description context are required."
    if len(resume_text) > MAX_INPUT_LENGTH or len(job_description) > MAX_INPUT_LENGTH:
        return "Each source field must be 30,000 characters or fewer."
    return None


@app.route("/interview/questions", methods=["POST"])
def interview_questions():
    # request.form.get reads the resume/job description text (.form.get only looks at the HTML form data and "resume"/"job_description" must match the name attribute in the HTML form
    resume_text = request.form.get("resume", "").strip()
    job_description = request.form.get("job_description", "").strip()
    # checks if the input is within the bounds (less than 30000)
    error = _valid_coach_inputs(resume_text, job_description)
    if error:
        return render_template("interview.html", error=error), 400

    try:
        question_set = InterviewCoach().generate_questions(resume_text, job_description)
    except Exception as exc:
        app.logger.exception("Interview question generation failed")
        message = str(exc) if isinstance(exc, RuntimeError) else "Questions could not be generated right now. Please try again."
        return render_template("interview.html", error=message, resume=resume_text, job_description=job_description)

    return render_template("interview.html", questions=question_set.questions, resume=resume_text, job_description=job_description)


@app.route("/interview/feedback", methods=["POST"])
def interview_feedback():
    # request.form.get reads the resume/job/question/answer description text (.form.get only looks at the HTML form data and "resume"/"job_description" must match the name attribute in the HTML form
    resume_text = request.form.get("resume", "").strip()
    job_description = request.form.get("job_description", "").strip()
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()
    error = _valid_coach_inputs(resume_text, job_description)
    if not error and (not question or not answer):
        error = "Choose a question and enter an answer before requesting feedback."
    if not error and (len(question) > 2000 or len(answer) > 10000):
        error = "The question or answer is too long."
    if error:
        return render_template("interview.html", error=error, resume=resume_text, job_description=job_description, selected_question=question, answer=answer), 400

    try:
        feedback = InterviewCoach().evaluate_answer(resume_text, job_description, question, answer)
    except Exception as exc:
        app.logger.exception("Interview answer evaluation failed")
        message = str(exc) if isinstance(exc, RuntimeError) else "Your answer could not be evaluated right now. Please try again."
        return render_template("interview.html", error=message, resume=resume_text, job_description=job_description, selected_question=question, answer=answer)

    return render_template("interview.html", feedback=feedback, resume=resume_text, job_description=job_description, selected_question=question, answer=answer)

# if the file is too large
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(_error):
    return render_template("index.html", error="The upload is too large. PDF files must be 5 MB or smaller."), 413 # HTTP status code "payload is too large"


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "").lower() == "true")
