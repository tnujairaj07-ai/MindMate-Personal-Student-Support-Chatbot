-- =========================
-- USERS TABLE (your auth)
-- =========================
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS messages;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin')),
    password TEXT NOT NULL
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'bot')),
    intent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- =========================
-- STUDENTS TABLE (team)
-- =========================
DROP TABLE IF EXISTS students;
CREATE TABLE students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,  
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    roll_no TEXT UNIQUE,
    course TEXT,
    year INTEGER,
    semester INTEGER, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- =========================
-- user_settings
-- =========================
DROP TABLE IF EXISTS user_settings;
CREATE TABLE user_settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  theme TEXT DEFAULT 'dark',
  preferred_language TEXT DEFAULT 'auto',   -- auto / en / hi / hinglish
  chat_mode TEXT DEFAULT 'auto',           -- auto / wellbeing / academics
  allow_analytics INTEGER DEFAULT 1,       -- 1 = true, 0 = false
  show_deadlines_card INTEGER DEFAULT 1,
  show_notices_card INTEGER DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

-- =========================
-- NOTICES TABLE (team)
-- =========================
DROP TABLE IF EXISTS notices;
CREATE TABLE notices (
    notice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    category TEXT,
    date_posted DATE,
    visible_to TEXT
);

INSERT INTO notices (title, description, category, date_posted, visible_to) VALUES
('Mid Semester Exams', 'Mid sem exams will start from 12 March 2026', 'exam', '2026-02-20', 'student'),
('Holi Holiday', 'College will remain closed on Holi', 'holiday', '2026-03-10', 'both');

-- =========================
-- DEADLINES TABLE 
-- =========================
DROP TABLE IF EXISTS deadlines;

CREATE TABLE deadlines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  label TEXT NOT NULL,
  due_date DATE NOT NULL,
  course TEXT,
  subject TEXT,
  type TEXT,          -- 'exam', 'assignment', 'project', etc.
  visible_to TEXT,    -- 'student', 'both', etc.
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

--Sample data
--INSERT INTO deadlines (label, due_date, course, subject, type, visible_to)
--VALUES
  --('DBMS Assignment 1', '2026-03-05', 'B.Tech CSE', 'DBMS', 'assignment', 'student'),
  --('OS Midsem Exam',    '2026-03-12', 'B.Tech CSE', 'OS',   'exam',       'student'),
  --('Mini Project Demo', '2026-04-01', 'B.Tech CSE', 'AI',   'project',    'student');

INSERT INTO deadlines (label, due_date, course, subject, type, visible_to)
VALUES ('DBMS Assignment 1', '2026-03-10', 'B.Tech CSE', 'DBMS', 'assignment', 'student');

INSERT INTO deadlines (label, due_date, course, subject, type, visible_to)
VALUES ('Campus Orientation', '2026-03-05', NULL, NULL, 'other', 'student');

INSERT INTO deadlines (label, due_date, course, subject, type, visible_to)
VALUES ('MBA Presentation', '2026-03-15', 'MBA', 'Marketing', 'project', 'student');


-- =========================
-- SYLLABUS TABLE (team)
-- =========================
DROP TABLE IF EXISTS syllabus;
CREATE TABLE syllabus (
    syllabus_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course TEXT,
    subject TEXT,
    unit TEXT,
    topics TEXT
);

INSERT INTO syllabus (course, subject, unit, topics) VALUES
('BCA', 'DBMS', 'Unit 1', 'Introduction, File System'),
('BCA', 'DBMS', 'Unit 3', 'Normalization, ER Model'),
('BCA', 'OS', 'Unit 2', 'Process Scheduling');

-- =========================
-- PYQs TABLE (team)
-- =========================
DROP TABLE IF EXISTS pyqs;
CREATE TABLE pyqs (
    pyq_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    year INTEGER,
    question TEXT
);

INSERT INTO pyqs (subject, year, question) VALUES
('DBMS', 2023, 'What is normalization? Explain 2NF.'),
('DBMS', 2022, 'Explain ER Model with diagram.');

-- =========================
-- PROJECTS TABLE (team)
-- =========================
DROP TABLE IF EXISTS projects;
CREATE TABLE projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    domain TEXT,
    description TEXT,
    difficulty TEXT
);

INSERT INTO projects (title, domain, description, difficulty) VALUES
('Student Result Analysis', 'Python', 'Analyze student marks using pandas', 'easy'),
('Mental Health Chatbot', 'AI/NLP', 'Chatbot for student mental health support', 'medium');

-- =========================
-- HELPLINES TABLE (team)
-- =========================
DROP TABLE IF EXISTS helplines;
CREATE TABLE helplines (
    helpline_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    email TEXT,
    available_hours TEXT,
    type TEXT
);

INSERT INTO helplines (name, phone, email, available_hours, type) VALUES
('Kiran Mental Health Helpline', '1800-599-0019', 'support@kiran.gov.in', '24x7', 'mental'),
('iCALL', '9152987821', 'icall@tiss.edu', 'Mon-Sat 10am-8pm', 'mental');

-- =========================
-- CHAT MESSAGES (privacy-safe, team)
-- =========================
DROP TABLE IF EXISTS chat_messages;
CREATE TABLE chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    sender TEXT,
    message_text TEXT,
    intent_detected TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--========================
-- Complaints table
--========================
DROP TABLE IF EXISTS complaints;
CREATE TABLE complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    roll_no TEXT NOT NULL,
    department TEXT,
    complaint_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    risk_level TEXT NOT NULL DEFAULT 'low',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Generic academic resources (notes, links, docs, videos, etc.)
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    type TEXT NOT NULL,              -- 'note', 'syllabus', 'pyq', 'project', 'link', etc.
    subject TEXT,                    -- e.g. 'DBMS'
    semester INTEGER,
    program TEXT,                    -- e.g. 'B.Tech CSE'
    url TEXT,                        -- optional link
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    visible_to TEXT DEFAULT 'student'  -- 'student', 'admin', 'all'
);

--============================
-- Saved resources per user
--============================
DROP TABLE IF EXISTS saved_resources;
CREATE TABLE saved_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    resource_id INTEGER,           -- optional pointer to original (for info only)
    title TEXT NOT NULL,
    type TEXT,
    subject TEXT,
    semester INTEGER,
    program TEXT,
    url TEXT,
    description TEXT,
    saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS intent_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message_text TEXT NOT NULL,
    intent TEXT NOT NULL,
    mood TEXT NOT NULL,
    source TEXT NOT NULL, -- 'rule', 'llm', 'manual'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS intent_stats_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    intent TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0
);