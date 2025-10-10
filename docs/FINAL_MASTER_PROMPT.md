# FINAL MASTER PROMPT — BOTCAMP MEDICAL

0. CONTEXT / GOAL
You are building a Telegram-based medical quiz and learning assistant for MBChB students (starting with the University of Nairobi). The system will:
- Deliver structured quizzes drawn from validated MCQs.
- Let users choose University → Course → Year → Unit → Topic before taking a quiz and persist that selection.
- Have three roles: Student, Admin, Super Admin.
- Provide upload/review tools for Admins and analytics for Super Admin.
- Include OCR + AI parsing of PDFs into quiz data.

1. CORE FEATURES & FLOW
1.1 Role Selection (/start)
- Prompt: choose Student, Admin, Super Admin; gated by passcodes in env
- Persist role + context in DB/Redis user_state

1.2 University → Course → Year → Unit → Topic
- Inline keyboards with hierarchical persistence
- Confirmation message after selection; state persists

1.3 Quiz Mode
- Fetch N random questions by selected topic
- One-question-per-message with A–D buttons
- Track session and cumulative stats

1.4 Statistics
- /stats for personal summary: quizzes taken, average score, top units, last active
- Super Admin aggregated analytics

1.5 Admin & Super Admin
- Admin: /upload (PDF→OCR→AI→review→approve), /list_uploads
- Super Admin: manage admins, view logs, rotate codes

1.6 OCR + AI
- OCR via Google Vision/Tesseract
- Parse MCQs via Gemini/OpenAI
- JSON format: {"question","options":["A","B","C","D"],"answer":"B","topic":"..."}
- Save to Postgres, link uploader

1.7 Data
- Postgres primary storage; Redis for ephemeral sessions
- Alembic migrations

2. ARCHITECTURE
User (Telegram) → Aiogram Handlers → (FastAPI optional) → Postgres + Redis → AI/OCR
Deploy with Docker (Render/Railway/Fly). CI/CD via GitHub Actions.

3. DATABASE (SUMMARY)
- users, universities, courses, years, units, topics
- questions(id, topic_id, question, options_json, answer, added_by)
- user_stats, admin_uploads, event_logs, telemetry_snapshots

4. SECURITY & ACCESS
- Role middleware; passcodes from env; rotate regularly

5. DEPLOYMENT & ENV
- .env: BOT_TOKEN, DATABASE_URL, REDIS_URL, ADMIN_CODE, SUPERADMIN_CODE, OCR_PROVIDER, AI_PROVIDER, AI_API_KEY
- Local: docker compose up, python -m app.main / uvicorn app.main:app

6. MONITORING & LOGS
- Daily telemetry snapshot
- /healthz and /ready endpoints
- /report (super admin summary)

7. DEV DOCS (SUMMARY)
- Commands: pytest, black, isort, flake8; CI must pass before merge

8. USER FLOW
- /start role → context selection → Start Quiz
- Admin upload pipeline
- Super Admin stats and management

9. AI PROMPTS
- Parse MCQs: “Extract MCQs with answers and topics… JSON {question, options, answer, topic}.”
- Summarize performance: “Summarize trends and weak areas in 50 words.”

10. CODEGEN INSTRUCTIONS (for Cursor)
- Generate aiogram 3 project per above
- Optional FastAPI backend
- Persist role and context; role-based menus; admin upload pipeline
- Postgres + Redis + Docker
- Include unit tests and CI workflow

11. TEST SCENARIOS
- Student completes selection + quiz → state saved, correct topic questions
- Admin uploads PDF → OCR+AI → question stored
- Super Admin views stats → aggregate values
- Restart bot → user context restored

12. ROADMAP (SUMMARY)
- MVP: Role flow, Quiz, Upload, Stats
- +3 mo: Payments, Web admin panel
- +6 mo: Adaptive AI, Leaderboards
- +12 mo: Multi-institution scaling

13. DELIVERABLES
- Working Telegram bot (Dockerized)
- Admin & Super Admin flows
- Persistent user context
- OCR + AI upload pipeline
- CI/CD & tests
- README + developer docs

14. FINAL PROMPT (Paste to Cursor)
“Build a complete aiogram 3 Telegram bot called ‘BotCamp Medical’. Implement every feature exactly as described in the Master Prompt: role selection (Student/Admin/Super Admin), persistent university→course→year→unit→topic selection, quiz engine, OCR + AI upload pipeline, stats, and admin controls. Use Postgres + Redis + Docker. Follow the architecture, database schema, and developer guidelines above. Write production-grade, well-structured, documented Python code with FastAPI optional backend and full CI workflow. Prioritize reliability, persistence, and clarity of user flow.”
