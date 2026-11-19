# Deployment readiness and limitations

StudyPilot AI combines a Streamlit interface with local components. A reachable Streamlit page does **not** by itself mean all tutoring functions work in the cloud.

## Current architectural constraint
The tutor module expects Ollama at `http://localhost:11434/api/chat` and the configured `qwen3:1.7b` model. On a cloud Streamlit instance, `localhost` refers to that cloud instance, **not** to a student's laptop.

## Verify before promoting the demo
- [ ] Confirm startup from a clean installation of `requirements.txt`.
- [ ] Test subject creation and persistence across sessions/restarts.
- [ ] Test PDF upload, extracted text accuracy and unsupported/scanned PDFs.
- [ ] Confirm quiz generation fails gracefully when Ollama is unavailable.
- [ ] Confirm tutoring requests show an explicit error instead of falsely claiming an answer.
- [ ] If remote inference is introduced, configure endpoint and credentials through server-side secrets.
- [ ] Review uploaded document retention, deletion, access controls and logging.
- [ ] Confirm model-generated answers cite the user's study material or clearly indicate uncertainty.

## Suggested deployment design
For a fully hosted tutor, replace the fixed local endpoint with a configurable, authenticated hosted inference service. Add connection timeouts, clear failure messages and cost/usage limits. Keep credentials out of source code. Treat student documents as potentially sensitive and specify retention policies.

No production deployment or end-to-end functionality is asserted by this checklist.
