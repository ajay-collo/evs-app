-- 1. Create Types first (Postgres specific)
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('student', 'teacher', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE activity_type AS ENUM ('plantation', 'waste', 'water', 'composting', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE submission_status AS ENUM ('pending', 'approved', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. TABLE: users
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,  -- Use SERIAL, not AUTO_INCREMENT
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(150)  UNIQUE NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    role          user_role     NOT NULL,
    student_id    VARCHAR(20)   UNIQUE,
    class_id      INT           DEFAULT NULL,
    created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- 3. TABLE: password_resets
CREATE TABLE IF NOT EXISTS password_resets (
    id         SERIAL PRIMARY KEY,
    user_id    INT          NOT NULL,
    token      VARCHAR(128) NOT NULL UNIQUE,
    expires_at TIMESTAMP    NOT NULL,
    used       BOOLEAN      DEFAULT FALSE,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. TABLE: activities
CREATE TABLE IF NOT EXISTS activities (
    id           SERIAL PRIMARY KEY,
    title        VARCHAR(200) NOT NULL,
    description  TEXT,
    type         activity_type NOT NULL,
    qr_token     VARCHAR(64)  UNIQUE NOT NULL,
    qr_image_url VARCHAR(500),
    created_by   INT          NOT NULL,
    expires_at   TIMESTAMP    DEFAULT NULL,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 5. TABLE: submissions
CREATE TABLE IF NOT EXISTS submissions (
    id           SERIAL PRIMARY KEY,
    student_id   INT          NOT NULL,
    activity_id  INT          NOT NULL,
    photo_url    VARCHAR(500) DEFAULT NULL,
    answer_text  TEXT         DEFAULT NULL,
    status       submission_status DEFAULT 'pending',
    teacher_note TEXT         DEFAULT NULL,
    submitted_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    reviewed_at  TIMESTAMP    DEFAULT NULL,
    FOREIGN KEY (student_id)  REFERENCES users(id),
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

-- 6. TABLE: attendance
CREATE TABLE IF NOT EXISTS attendance (
    id               SERIAL PRIMARY KEY,
    student_id       INT NOT NULL,
    activity_id      INT NOT NULL,
    scan_time        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_minutes INT DEFAULT 0,
    FOREIGN KEY (student_id)  REFERENCES users(id),
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);