# 📄 AI Resume & Interview Coach

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-black)
![Google Gemini](https://img.shields.io/badge/AI-Google_Gemini-4285F4)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57)
![License](https://img.shields.io/badge/License-MIT-yellow)

An AI-powered web application that helps job seekers improve their resumes and prepare for interviews.

AI Resume & Interview Coach analyzes resumes against specific job descriptions using Google's Gemini AI, provides personalized improvement suggestions, identifies missing skills and keywords, generates tailored interview questions, and stores previous analyses in a SQLite database for future reference.

---

## ✨ Features

* 🤖 AI-powered resume analysis using Google Gemini
* 📄 PDF resume upload and text extraction
* 🎯 Resume matching against job descriptions
* 📈 Resume match score with detailed feedback
* 🛠️ Suggestions for improving bullet points
* 🔍 Missing keyword and skill detection
* 💼 AI-generated interview questions tailored to the role
* 💾 Persistent storage using SQLite
* ✅ Structured AI responses using Pydantic models
* 🔐 Secure API key management through environment variables

---

## 📸 Preview

<img width="848" height="454" alt="AIresume" src="https://github.com/user-attachments/assets/9e424dd6-c003-4ba0-aac2-a3cfca0f0462" />


---

## 🛠️ Built With

* Python 3
* Flask
* Google Gemini API
* SQLite
* Pydantic
* PyPDF
* python-dotenv
* HTML
* CSS
* Jinja2

---

## 📂 Project Structure

```text
AIResume/
│
├── templates/
│   ├── index.html
│   ├── results.html
│   └── ...
│
├── static/
│   ├── css/
│   ├── images/
│   └── ...
│
├── app.py                 # Flask application
├── interview_coach.py     # Gemini AI integration
├── database.py            # SQLite database manager
├── pdf_utils.py           # PDF validation and text extraction
├── test_database.py       # Database unit tests
├── requirements.txt
├── .env                   # API configuration (not committed)
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/PadmeAIcaza/AI-resume-coach.git
cd AI-resume-coach
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your Gemini API Key

Create a `.env` file in the project root.

```env
GEMINI_API_KEY=your_api_key_here

# Optional
GEMINI_MODEL=gemini-3.6-flash
```

### 4. Run the application

```bash
python app.py
```

Then open your browser and navigate to:

```
http://127.0.0.1:5000
```

---

## ⚙️ How It Works

1. The user uploads a PDF resume.
2. The application extracts and validates the resume text.
3. A target job description is entered.
4. Resume and job description are sent to Google Gemini.
5. Gemini returns structured feedback validated with Pydantic.
6. Results are displayed in the web interface.
7. Resume analyses and interview questions are stored in a SQLite database for future use.

---

## 🧠 AI Features

The application uses Google Gemini to provide:

- Resume match scoring
- Resume summaries
- Missing skills and keywords
- Improved resume bullet points
- Actionable improvement suggestions
- Customized interview questions based on the job description

Using Pydantic ensures that every AI response follows a predictable structure before being displayed to the user.

---

## 🗄️ Database

The application stores generated content in SQLite, including:

| Table | Purpose |
|--------|----------|
| `job_descriptions` | Stores submitted job descriptions |
| `resume_analyses` | Stores AI-generated resume analyses |
| `interview_questions` | Stores generated interview questions |
| `user_answers` | Stores interview practice responses |

---

## 🔒 Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `GEMINI_MODEL` | *(Optional)* Gemini model to use |

---

## 📋 Input Validation

The application includes several safeguards to improve reliability:

- PDF file validation
- File size limits
- Maximum page limits
- Detection of encrypted PDFs
- Empty input validation
- Structured AI output validation using Pydantic
- Graceful error handling for API failures

---

## 🧪 Testing

Database functionality can be tested with:

```bash
python -m unittest test_database.py
```

---

## 📄 License

This project is licensed under the MIT License.
