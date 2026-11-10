# StudyPilot AI — Personalized Study Assistant

**Python · Streamlit · PDF Study Materials · Local AI Tutoring**

**[View the GitHub repository](https://github.com/fernandatrevi/studypilot-ai)**

StudyPilot AI is an educational Streamlit app for organizing subjects, working with uploaded PDF study materials, asking a local AI tutor questions, practicing quizzes, simulating exams and reviewing mistakes.

## Features documented in the application

- Create and select subjects.
- Upload and browse PDF study materials, including page previews and extracted text.
- Ask questions grounded in the uploaded material.
- Generate practice questions and exam-style quizzes.
- Score responses and store results.
- Review incorrect answers and track performance statistics.

## Technology and execution

- **Frontend:** Streamlit
- **Document processing:** PyMuPDF
- **Local AI service:** Ollama, with a `qwen3:1.7b` model configured in `src/tutor.py`
- **Application modules:** `src/database.py`, `src/documents.py`, `src/quiz.py`, `src/tutor.py`

This is **not a hosted public AI service**. The tutor currently expects an Ollama server running locally at `http://localhost:11434/api/chat`, with the configured model available. The user interface and internal tutor prompts currently contain Spanish text.

## Local setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

For AI tutoring and quiz generation, configure and start the local Ollama service and install the model referenced in `src/tutor.py`. Depending on local settings, generated answers and extracted documents may need additional review.

## Limitations

The application is a learning prototype. AI-generated explanations and quiz questions can contain errors and should be checked against course materials. Do not upload sensitive or confidential PDFs without reviewing the application's data storage and processing behavior.

**Public demo URL:** Not verified or documented. This repository is the project link.
