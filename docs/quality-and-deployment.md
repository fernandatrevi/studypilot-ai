# Quality and deployment checks

StudyPilot AI is an educational prototype, not a verified grading or knowledge system.

## What to verify locally

1. Install dependencies from `requirements.txt` in a fresh virtual environment.
2. Launch `streamlit run app.py` and check subject creation, PDF upload, document preview, quiz scoring, and saved results.
3. For AI-backed features, start Ollama separately and confirm that the model configured in `src/tutor.py` is installed and reachable.
4. Test questions that have answers in uploaded documents and questions that do not. The tutor should distinguish uncertainty instead of inventing citations.
5. Test scanned PDFs, empty files, malformed PDFs, and long documents; document extraction failures rather than silently assuming complete text.
6. Verify that quiz scoring and explanations agree with the source material.

## Deployment distinction

A hosted Streamlit page is **not** evidence that a local Ollama endpoint is reachable from the hosting environment. A production AI deployment needs an explicitly configured, secured, reachable inference service and appropriate cost, access, and failure handling.

## Privacy and limitations

Avoid uploading confidential, identifying, or copyrighted documents without proper authorization. Review retention and access controls before exposing uploaded material to other users. AI explanations and generated questions require human verification.

No automated test run, live-cloud deployment check, or model benchmark is claimed by this document.
