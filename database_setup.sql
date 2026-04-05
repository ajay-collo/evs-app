-- ============================================================
--  database_setup.sql
--  Run this file in MySQL to create all required tables
--  Command: mysql -u root -p env_education < database_setup.sql
-- ============================================================

-- Create database (run this first, then switch to it)
CREATE DATABASE IF NOT EXISTS env_education;
USE env_education;

-- ─────────────────────────────────────────────
--  TABLE 1: users
--  Stores students, teachers, and admins
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(150)  UNIQUE NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,        -- bcrypt hash, NEVER plain text
    role          ENUM('student', 'teacher', 'admin') NOT NULL,
    student_id    VARCHAR(20)   UNIQUE,           -- only for students e.g. STU2024001
    class_id      INT           DEFAULT NULL,     -- FK to classes table (add later)
    created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
--  TABLE 2: password_resets
--  Stores forgot-password tokens
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS password_resets (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT          NOT NULL,
    token      VARCHAR(128) NOT NULL UNIQUE,
    expires_at DATETIME     NOT NULL,
    used       TINYINT(1)   DEFAULT 0,            -- 0 = not used, 1 = already used
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
--  TABLE 3: activities
--  Environmental tasks created by teachers
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activities (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(200) NOT NULL,
    description  TEXT,
    type         ENUM('plantation', 'waste', 'water', 'composting', 'other') NOT NULL,
    qr_token     VARCHAR(64)  UNIQUE NOT NULL,
    qr_image_url VARCHAR(500),
    created_by   INT          NOT NULL,
    expires_at   DATETIME     DEFAULT NULL,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- ─────────────────────────────────────────────
--  TABLE 4: submissions
--  Student proof uploads after scanning QR
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS submissions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    student_id   INT          NOT NULL,
    activity_id  INT          NOT NULL,
    photo_url    VARCHAR(500) DEFAULT NULL,
    answer_text  TEXT         DEFAULT NULL,
    status       ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    teacher_note TEXT         DEFAULT NULL,
    submitted_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    reviewed_at  DATETIME     DEFAULT NULL,
    FOREIGN KEY (student_id)  REFERENCES users(id),
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

-- ─────────────────────────────────────────────
--  TABLE 5: attendance
--  Auto-recorded when student scans QR
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    student_id       INT NOT NULL,
    activity_id      INT NOT NULL,
    scan_time        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_minutes INT DEFAULT 0,
    FOREIGN KEY (student_id)  REFERENCES users(id),
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

-- ─────────────────────────────────────────────
--  SAMPLE DATA — test accounts
--  Password for all: Test@1234
--  bcrypt hash of 'Test@1234':
-- ─────────────────────────────────────────────

-- Generate this hash by running in Python:
--   import bcrypt
--   print(bcrypt.hashpw(b'Test@1234', bcrypt.gensalt()).decode())

-- Then paste the output below instead of the placeholder hash:
INSERT INTO users (name, email, password_hash, role, student_id) VALUES
(
    'Aanya Sharma',
    'student@test.com',
    '$2b$12$PLACEHOLDER_HASH_RUN_PYTHON_TO_GENERATE',
    'student',
    'STU2024001'
),
(
    'Mr. Rajan Mehta',
    'teacher@test.com',
    '$2b$12$PLACEHOLDER_HASH_RUN_PYTHON_TO_GENERATE',
    'teacher',
    NULL
),
(
    'Admin User',
    'admin@test.com',
    '$2b$12$PLACEHOLDER_HASH_RUN_PYTHON_TO_GENERATE',
    'admin',
    NULL
);

-- ─────────────────────────────────────────────
--  HOW TO GENERATE REAL PASSWORD HASHES
--  Run this Python script once to get hashes:
-- ─────────────────────────────────────────────
-- import bcrypt
-- password = b'Test@1234'
-- hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode()
-- print(hashed)
-- Then copy the output into the INSERT above
