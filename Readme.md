# MindMate – Student Wellbeing & Academics Companion

MindMate is a full‑stack AI‑powered web application that supports students with both mental wellbeing and academic needs. It combines a custom rule‑based intent and mood layer with a pre‑trained Large Language Model (LLM), plus university‑specific academic resources and admin insights for trends and complaints management. 

***

## 1. Project Overview

MindMate is designed as a “digital companion” for students that they can use to talk about stress, ask academic doubts, plan studies, and access university resources from a single interface. 

The system focuses on three pillars:

- **Student support**: anonymous, low‑friction chat for everyday stress, anxiety, motivation, and doubts. 
- **Academics hub**: deadlines, syllabus, PYQs, projects, and helplines tailored to the student’s course and semester. 
- **Admin insights**: anonymised trends, complaints, and high‑level mood/intent signals to help colleges understand what students are struggling with (without seeing raw conversations). 

MindMate is built as a realistic mini‑product rather than a toy demo, with proper authentication, role‑based views, a structured database, and a clear feature roadmap. 

***

## 2. Core Features

### 2.1 Student‑facing features

- **AI Chatbot (MindMate bot)**  
  - Conversational interface for wellbeing and academic questions. 
  - Uses a keyword/rule‑based intent and mood detector plus an external pre‑trained LLM for responses (no custom LLM training). 
  - Modes (planned and partially wired): auto, wellbeing, academics, to bias responses according to context. 

- **Academics view**  
  - Shows notices, deadlines, syllabus, PYQs, projects, and helplines from the database instead of hard‑coded data. 
  - Uses a unified `resources` model to fetch PYQs and projects filtered by course/semester/subject. 
  - Basic **bookmarking** of resources using a `saved_resources` table and `/api/saved_resources` endpoints so students can save useful PYQs/projects. 

- **Right‑panel cards**  
  - Quick view of upcoming deadlines, notices, and tips. 
  - Chips like “Help me plan my study” send predefined prompts to the chatbot; a dedicated `/api/studyplan` endpoint is planned for a more structured planner. 

- **Profile & Settings (in progress)**  
  - Profile UI for name, email, course, year, semester, section (backed by `users` + `students` tables). 
  - Planned `user_settings` table for theme, preferred language, chat mode, and cards visibility. 

### 2.2 Admin‑facing features

- **Role‑based admin dashboard**  
  - Admin login unlocks extra views: Insights, Manage, Complaints. 
  - Access controlled in backend using helper functions like `require_admin()` around admin APIs. 

- **Content management (Phase 4)**  
  - `resources` table: generic store for PYQs, syllabus, and projects with fields like type, title, course, semester, subject, difficulty, meta_json. 
  - `saved_resources` table: links students to their bookmarked resources. 
  - `/api/admin/resources` CRUD: list, create, update, delete resources with filters by type, course, semester, subject. 
  - `/api/admin/notices` CRUD: full management of notices (no hard‑coded/demo alerts). 
  - Academics UI prepared to show bookmark buttons via `bookmarkResource(resourceId)` calling `/api/saved_resources`. 

- **Insights & complaints**  
  - `/api/insights/overview` returns aggregated intent counts and complaints summary for the admin dashboard. 
  - Complaints table with department and status, plus APIs for listing complaints and grouping by department/status. 
  - Time‑series trends and more advanced crisis‑risk metrics are planned as future work. 

***

## 3. Architecture

MindMate follows a clean separation between frontend, backend, LLM wrapper, and database. 

### 3.1 High‑level architecture

1. **Frontend (single‑page app)**  
   - HTML/CSS/JavaScript, with `app.js` managing login, views, and API calls. 
   - Views: Login, Chat, Academics, Insights, Manage, Settings, Profile, etc. 

2. **Backend (Flask)**  
   - `backend/app.py` exposes REST APIs for auth, chat, academics resources, notices, deadlines, helplines, complaints, insights, and bookmarks. 
   - Uses a central `Config` class (in `backend/config.py`) to load environment variables (`SECRET_KEY`, `DEMO_MODE`, `LLM_MODE`, model name, paths). 
   - Logging configured via Python `logging` instead of `print`, with `/chat` demo route removed; only `/api/chat` is used. 

3. **Chatbot & LLM layer**

   - `backend/chatbot.py`  
     - Applies keyword/rule‑based logic for **intent** (e.g., wellbeing vs academics vs specific resource types) and **mood/risk** tags. 
     - Calls a pre‑trained LLM via wrapper (e.g., `llm_ollama` for local models or an online provider) using prompt engineering (zero‑shot; no fine‑tuning). 

   - `backend/llm_ollama.py`  
     - Handles interaction with a local Ollama model; model name is configurable via env (`OLLAMA_MODEL_NAME` or `Config.LLM_MODEL_NAME`).

4. **Database layer**

   - `backend/db.py` centralises all DB operations: users, students, messages, chat_messages, notices, deadlines, syllabus, PYQs, projects, resources, helplines, complaints, saved_resources. 
   - Academic data and resources are stored in relational tables with sample entries for demo and testing. 

***

## 4. Data & Privacy Model

MindMate takes a privacy‑aware approach, especially for sensitive mental‑health conversations. 

- **Authentication & sessions**  
  - Passwords are stored using secure hashing via `werkzeug.security`. 
  - Flask sessions identify logged‑in users; admin APIs call `require_admin()` helpers to enforce role‑based access. 

- **Messages vs chat_messages**  
  - `messages`: may store per‑user chat history where personalised context is needed (e.g., for better continuity), depending on mode. 
  - `chat_messages`: stores anonymised session‑level messages with a session ID decoupled from user ID to support aggregate mood/intent analytics. 
  - This supports anonymised **trends** (e.g., number of stress‑related chats) without exposing raw text to admins. 

- **Complaints & insights**  
  - Complaints are stored with department and status; admin sees structured data, not private chat logs. 
  - `/api/insights/overview` only returns aggregated counts (intents, complaints, mood tags), not message content. 

Planned improvements (documented as future work in the roadmap):

- Dedicated “Data & privacy” page explaining what is stored locally vs on the server, and for how long. 
- Per‑device anonymised IDs via secure cookies for `chat_messages` instead of a generic fallback like `"anonymous-session"`. 
- “Delete my account & messages” flow to purge user‑linked data on request. 

***

## 5. Security & Reliability

Phase 1 focused on making the backend safer and closer to production‑ready. 

- **Central configuration**  
  - `backend/config.py` loads `.env` once and exposes `Config` with `SECRET_KEY`, `DEBUG`, `DEMO_MODE`, `LLM_MODE`, and paths for templates/static. 
  - `app.py` uses `Config` for Flask initialisation, ensuring no hard‑coded secret key in code (must come from `.env`). 

- **Logging & cleanup**  
  - Replaced scattered `print()` statements with structured logging using `logging.basicConfig` and a module logger. 
  - Removed the old non‑API `/chat` demo route; all chat traffic uses `/api/chat` with unified logic and logging. 

- **Password policy**  
  - Backend enforces minimum password length (e.g., 8) and requiring both letters and digits via `is_password_strong()` in `app.py`. 
  - Signup (`/api/signup`) validates strength server‑side, independent of any frontend checks. 

- **Basic rate limiting**  
  - In‑memory per‑IP rate limiter for `/api/login` and `/api/signup`; e.g., maximum N attempts per window (10 per 60 seconds) returning HTTP 429 on abuse. 
  - Helps protect against brute‑force login/signup attacks in a simple but effective way for a demo deployment. 

- **Future security work**  
  - CSRF protection for non‑AJAX forms using Flask‑WTF or custom token + header for JSON APIs. 
  - Stronger session handling and cookie flags if deployed on the public internet. 

***

## 6. Tech Stack

- **Frontend**: HTML, CSS, vanilla JavaScript (`static/js/app.js`). 
- **Backend**: Python, Flask, `python-dotenv`, `werkzeug.security`, `logging`. 
- **Database**: SQLite (or similar) managed via `backend/db.py` helpers; schema includes users, students, messages, chat_messages, notices, deadlines, syllabus, pyqs, projects, resources, helplines, complaints, saved_resources. 
- **AI / NLP**:  
  - Rule‑based keyword heuristics for intent and mood detection. 
  - Pre‑trained LLM accessed via API or local Ollama backend; no custom dataset and no LLM training or fine‑tuning in this project (zero‑shot + prompt engineering only). 

***

## 7. Roadmap

The project is being developed in phases; many features are partially implemented and tracked as future enhancements. 

- **Phase 1 – Config, auth, and cleanup**  
  - Central config, `.env` usage, logging, rate‑limits, password rules (implemented). 

- **Phase 2 – Profile & Settings**  
  - `user_settings` table, `/api/settings`, `/api/profile`, and wiring chat modes and language preferences (planned/in progress). 

- **Phase 3 – Student filters & study planner**  
  - Extend `students` with semester, profile‑based filtering for academic APIs, and a real `/api/studyplan` endpoint (partially present as UI, backend pending). 

- **Phase 4 – Admin resources & bookmarks**  
  - `resources` + `saved_resources`, admin CRUD APIs, and bookmark buttons in Academics (largely implemented, polishing ongoing). 

- **Phase 5 – Stronger AI & language support**  
  - Replace pure keyword intent/mood with a classifier or dedicated LLM classification endpoint, add multilingual replies based on settings, and maintain a conversation buffer. 

- **Phase 6 – Insights & crisis‑risk**  
  - Time‑series analytics, crisis‑risk aggregations, and richer complaint workflows (status filters, updates) for admins. 

- **Phase 7 – Privacy UX & research features**  
  - Data & privacy page, delete‑account functionality, per‑device UUIDs, and prototype features for anomaly detection/federated‑style analytics. 

***

## 8. How to Run (local)

> Adjust paths/commands based on your actual repo structure.

1. Create and activate a virtual environment, then install requirements:
   ```bash
   pip install -r requirements.txt
   ```  

2. Create a `.env` file at the project root:
   ```env
   SECRET_KEY=your_secret_here
   DEBUG=true
   DEMO_MODE=true
   LLM_MODE=local           # or "online"
   OLLAMA_MODEL_NAME=llama3.2
   ```  

3. Initialise the database (if you have a script or CLI, e.g.):
   ```bash
   python -m backend.init_db
   ```  

4. Run the Flask app:
   ```bash
   python -m backend.app
   ```  

5. Open the app in your browser (typically `http://localhost:5000`) and log in with a test student/admin account seeded in the DB. 

