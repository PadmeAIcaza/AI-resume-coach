from flask import Flask, render_template, request

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    resume_text = request.form.get("resume", "").strip()
    job_description = request.form.get("job_description", "").strip()

    if not resume_text or not job_description:
        return render_template(
            "index.html",
            error="Please enter both your resume and the job description."
        )

    feedback = {
        "match_score": 75,
        "matching_skills": [
            "Python",
            "Flask",
            "SQL"
        ],
        "missing_skills": [
            "Docker",
            "Unit testing"
        ],
        "suggestion": (
            "Add more measurable results to your project descriptions "
            "and mention the tools you used."
        )
    }

    return render_template(
        "results.html",
        resume=resume_text,
        job_description=job_description,
        feedback=feedback
    )


if __name__ == "__main__":
    app.run(debug=True)