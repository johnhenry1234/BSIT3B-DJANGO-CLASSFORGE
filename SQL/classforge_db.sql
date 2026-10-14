-- ============================================================================
-- ClassForge Database Schema (MySQL / MariaDB Compatible)
-- ============================================================================
-- Django app: apps.courses
-- Django tables map 1:1 via Meta.db_table:
--   Course     -> `courses`
--   Enrollment -> `enrollments`   (NEW - see note 5)
--   Assignment -> `assignments`
--   Submission -> `submissions`
--   Grade      -> `grades`
--
-- What changed vs the original draft, and why:
--   1. Added FK constraints for instructor_id / student_id -> auth_user(id).
--      The original only had comments; without FKs orphaned rows are possible.
--   2. submissions: added UNIQUE(assignment_id, student_id, version) so the
--      append-only versioning can't create duplicate version numbers, plus an
--      index on (assignment_id, student_id) for "latest version per student".
--   3. submissions: added CHECK that at least one of file_attachment /
--      text_content is present (matches model clean() validation).
--   4. grades: split graded_at (ON UPDATE) into created_at + graded_at.
--      A single ON UPDATE column loses the original grading time on every
--      edit; Django uses created_at (auto_now_add) + graded_at (auto_now).
--      Added CHECK (score >= 0); the score <= max_score rule is enforced in
--      Django (needs a join, can't be a simple CHECK).
--   5. NEW `enrollments` table (course_id, student_id UNIQUE). A real LMS
--      needs to know who is in a course to scope visibility, submissions and
--      grading. Safe to ignore if you want fully open courses.
--   6. Added updated_at to courses/assignments/submissions, indexes on all
--      FKs, ENGINE=InnoDB + utf8mb4, and IF NOT EXISTS for re-runnable setup.
-- ============================================================================

-- To use a dedicated database instead of your Django database, uncomment:
-- CREATE DATABASE IF NOT EXISTS classforge
--   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE classforge;
-- By default, import this file into the same database Django uses
-- (see DB_NAME in mysite/settings.py, default `bsitcrud`) so the table
-- names below (courses, enrollments, assignments, submissions, grades)
-- match the Django models' Meta.db_table values.

-- 1. Courses Table -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    instructor_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_courses_instructor
        FOREIGN KEY (instructor_id) REFERENCES auth_user (id) ON DELETE CASCADE,
    INDEX idx_courses_instructor (instructor_id),
    INDEX idx_courses_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Enrollments Table (NEW) -------------------------------------------------
-- One row per (course, student). Students must enroll before submitting.
CREATE TABLE IF NOT EXISTS enrollments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    student_id INT NOT NULL,
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_enrollments_course
        FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
    CONSTRAINT fk_enrollments_student
        FOREIGN KEY (student_id) REFERENCES auth_user (id) ON DELETE CASCADE,
    UNIQUE KEY uq_enrollments_course_student (course_id, student_id),
    INDEX idx_enrollments_student (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Assignments Table -------------------------------------------------------
CREATE TABLE IF NOT EXISTS assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(20) NOT NULL DEFAULT 'code_project',
    description TEXT NULL,
    due_date DATETIME NOT NULL,
    max_score DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_assignments_course
        FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
    CONSTRAINT chk_assignments_max_score CHECK (max_score > 0),
    CONSTRAINT chk_assignments_category
        CHECK (category IN ('code_project', 'erd', 'database_design', 'documentation', 'other')),
    INDEX idx_assignments_course (course_id),
    INDEX idx_assignments_due_date (due_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Submissions Table (Append-Only) -----------------------------------------
-- Re-submitting INSERTs a new row with version = MAX(version) + 1 for that
-- (assignment_id, student_id) pair. Never UPDATEs existing rows.
CREATE TABLE IF NOT EXISTS submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    student_id INT NOT NULL,
    version INT UNSIGNED NOT NULL DEFAULT 1,
    file_attachment VARCHAR(255) NULL,
    text_content TEXT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_submissions_assignment
        FOREIGN KEY (assignment_id) REFERENCES assignments (id) ON DELETE CASCADE,
    CONSTRAINT fk_submissions_student
        FOREIGN KEY (student_id) REFERENCES auth_user (id) ON DELETE CASCADE,
    UNIQUE KEY uq_submissions_assignment_student_version (assignment_id, student_id, version),
    CONSTRAINT chk_submissions_has_content
        CHECK (file_attachment IS NOT NULL OR text_content IS NOT NULL),
    INDEX idx_submissions_assignment_student (assignment_id, student_id),
    INDEX idx_submissions_student (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Grades Table (One grade per submission version) -------------------------
CREATE TABLE IF NOT EXISTS grades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    submission_id INT NOT NULL UNIQUE,
    instructor_id INT NOT NULL,
    score DECIMAL(5,2) NOT NULL,
    feedback TEXT NULL,
    is_published TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_grades_submission
        FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE,
    CONSTRAINT fk_grades_instructor
        FOREIGN KEY (instructor_id) REFERENCES auth_user (id) ON DELETE CASCADE,
    CONSTRAINT chk_grades_score_non_negative CHECK (score >= 0),
    INDEX idx_grades_instructor (instructor_id),
    INDEX idx_grades_published (is_published)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
