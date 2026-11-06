-- MySQL dump converted from SQLite (db.sqlite3)
-- Generated 2026-11-05  |  Requires MySQL 8.0.13+ (or MariaDB 10.5+ with JSON as LONGTEXT)
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';
SET time_zone = "+00:00";

DROP TABLE IF EXISTS `activity_logs`;
CREATE TABLE `activity_logs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `action` VARCHAR(64) NOT NULL,
  `entity_type` VARCHAR(64) NOT NULL,
  `entity_id` VARCHAR(64) NOT NULL,
  `description` TEXT NOT NULL,
  `ip_address` CHAR(39) NULL,
  `user_agent` TEXT NOT NULL,
  `metadata` JSON NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `actor_id` INT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_activity_actor_time` (`actor_id`, `created_at` DESC),
  KEY `idx_activity_entity` (`entity_type`, `entity_id`),
  KEY `activity_logs_actor_id_0356ce50` (`actor_id`),
  KEY `activity_logs_created_at_2048f5f6` (`created_at`),
  KEY `activity_logs_action_8ace2550` (`action`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `ai_evaluations`;
CREATE TABLE `ai_evaluations` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `status` VARCHAR(20) NOT NULL,
  `mode` VARCHAR(20) NOT NULL,
  `model_name` VARCHAR(120) NOT NULL,
  `suggested_score` DECIMAL(10,2) NULL,
  `suggested_feedback` TEXT NOT NULL,
  `summary` TEXT NOT NULL,
  `suggested_criteria` JSON NOT NULL,
  `guideline_snapshot` TEXT NOT NULL,
  `inspection` JSON NOT NULL,
  `raw_response` LONGTEXT NOT NULL,
  `error` TEXT NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `started_at` DATETIME(6) NULL,
  `completed_at` DATETIME(6) NULL,
  `applied_at` DATETIME(6) NULL,
  `applied_by_id` INT NULL,
  `requested_by_id` INT NULL,
  `submission_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ai_evaluations_submission_id_e9e27fc0` (`submission_id`),
  KEY `ai_evaluations_requested_by_id_348520c4` (`requested_by_id`),
  KEY `ai_evaluations_applied_by_id_b82bdfb1` (`applied_by_id`),
  KEY `ai_evaluations_created_at_032e6246` (`created_at`),
  KEY `ai_evaluations_status_bbe17fe5` (`status`),
  KEY `idx_ai_eval_submission_time` (`submission_id`, `created_at` DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `ai_flags`;
CREATE TABLE `ai_flags` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `kind` VARCHAR(32) NOT NULL,
  `severity` VARCHAR(16) NOT NULL,
  `message` TEXT NOT NULL,
  `evidence` TEXT NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `evaluation_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ai_flags_evaluation_id_9025b97f` (`evaluation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `assignment_seen`;
CREATE TABLE `assignment_seen` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `seen_at` DATETIME(6) NOT NULL,
  `assignment_id` BIGINT NOT NULL,
  `student_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `assignment_seen_student_id_bff01af9` (`student_id`),
  KEY `assignment_seen_assignment_id_24013ffb` (`assignment_id`),
  UNIQUE KEY `uq_assignment_seen_student_id_assignment_id` (`student_id`, `assignment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `assignments`;
CREATE TABLE `assignments` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `due_date` DATETIME(6) NOT NULL,
  `max_score` DECIMAL(10,2) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `course_id` BIGINT NOT NULL,
  `category` VARCHAR(20) NOT NULL,
  `accepts_pdf` TINYINT(1) NOT NULL,
  `accepts_zip` TINYINT(1) NOT NULL,
  `ai_auto_run` TINYINT(1) NOT NULL,
  `guidelines` TEXT NOT NULL,
  `required_files` TEXT NOT NULL,
  `accepted_formats` TEXT NOT NULL,
  `ai_grading_mode` VARCHAR(32) NOT NULL,
  `allow_resubmission` TINYINT(1) NOT NULL,
  `default_exclusions` TEXT NOT NULL,
  `documentation_requirements` TEXT NOT NULL,
  `expected_outcomes` TEXT NOT NULL,
  `late_penalty_percent` DECIMAL(10,2) NOT NULL,
  `late_policy` VARCHAR(16) NOT NULL,
  `manual_review_required` TINYINT(1) NOT NULL,
  `max_upload_mb` INT UNSIGNED NOT NULL,
  `published_at` DATETIME(6) NULL,
  `required_directories` TEXT NOT NULL,
  `required_tests` TEXT NOT NULL,
  `revision_deadline_days` INT UNSIGNED NOT NULL,
  `status` VARCHAR(20) NOT NULL,
  `validation_rules` TEXT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `assignments_course_id_0c35aaf8` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `auth_group`;
CREATE TABLE `auth_group` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_auth_group_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `auth_group_permissions`;
CREATE TABLE `auth_group_permissions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `group_id` INT NOT NULL,
  `permission_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `auth_group_permissions_permission_id_84c5c92e` (`permission_id`),
  KEY `auth_group_permissions_group_id_b120cbf9` (`group_id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`, `permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `auth_permission`;
CREATE TABLE `auth_permission` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `content_type_id` INT NOT NULL,
  `codename` VARCHAR(100) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `auth_permission_content_type_id_2f476e4b` (`content_type_id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`, `codename`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `auth_user`;
CREATE TABLE `auth_user` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `password` VARCHAR(128) NOT NULL,
  `last_login` DATETIME(6) NULL,
  `is_superuser` TINYINT(1) NOT NULL,
  `username` VARCHAR(150) NOT NULL,
  `last_name` VARCHAR(150) NOT NULL,
  `email` VARCHAR(254) NOT NULL,
  `is_staff` TINYINT(1) NOT NULL,
  `is_active` TINYINT(1) NOT NULL,
  `date_joined` DATETIME(6) NOT NULL,
  `first_name` VARCHAR(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_auth_user_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `auth_user_groups`;
CREATE TABLE `auth_user_groups` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `group_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `auth_user_groups_group_id_97559544` (`group_id`),
  KEY `auth_user_groups_user_id_6a12ed8b` (`user_id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`, `group_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `auth_user_user_permissions`;
CREATE TABLE `auth_user_user_permissions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `permission_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `auth_user_user_permissions_permission_id_1fbb5f2c` (`permission_id`),
  KEY `auth_user_user_permissions_user_id_a95ead1b` (`user_id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`, `permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `classforge_api_tokens`;
CREATE TABLE `classforge_api_tokens` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `prefix` VARCHAR(16) NOT NULL,
  `token_hash` VARCHAR(64) NOT NULL,
  `scopes` VARCHAR(255) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `expires_at` DATETIME(6) NULL,
  `last_used_at` DATETIME(6) NULL,
  `revoked_at` DATETIME(6) NULL,
  `user_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `classforge_api_tokens_user_id_759ab19b` (`user_id`),
  KEY `classforge_api_tokens_prefix_f56eeb54` (`prefix`),
  UNIQUE KEY `uq_classforge_api_tokens_token_hash` (`token_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `classforge_notifications`;
CREATE TABLE `classforge_notifications` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `kind` VARCHAR(32) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `body` TEXT NOT NULL,
  `url` VARCHAR(500) NOT NULL,
  `read_at` DATETIME(6) NULL,
  `created_at` DATETIME(6) NOT NULL,
  `user_id` INT NOT NULL,
  `project_id` BIGINT NULL,
  `snapshot_id` BIGINT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_notify_user_read` (`user_id`, `read_at`),
  KEY `classforge_notifications_snapshot_id_040b95b5` (`snapshot_id`),
  KEY `classforge_notifications_project_id_36986db7` (`project_id`),
  KEY `classforge_notifications_user_id_bd2f48d6` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `course_assistants`;
CREATE TABLE `course_assistants` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(6) NOT NULL,
  `added_by_id` INT NULL,
  `course_id` BIGINT NOT NULL,
  `user_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `course_assistants_user_id_6a973eb8` (`user_id`),
  KEY `course_assistants_course_id_b06d8883` (`course_id`),
  KEY `course_assistants_added_by_id_a24253ad` (`added_by_id`),
  UNIQUE KEY `uq_course_assistants_course_id_user_id` (`course_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `courses`;
CREATE TABLE `courses` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `code` VARCHAR(50) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `instructor_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `courses_instructor_id_f5e3e077` (`instructor_id`),
  UNIQUE KEY `uq_courses_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `criterion_scores`;
CREATE TABLE `criterion_scores` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `points_awarded` DECIMAL(10,2) NOT NULL,
  `comment` TEXT NOT NULL,
  `grade_id` BIGINT NOT NULL,
  `criterion_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `criterion_scores_criterion_id_55b6f0e5` (`criterion_id`),
  KEY `criterion_scores_grade_id_ec9f7d0a` (`grade_id`),
  UNIQUE KEY `uq_criterion_scores_grade_id_criterion_id` (`grade_id`, `criterion_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `django_admin_log`;
CREATE TABLE `django_admin_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `object_id` TEXT NULL,
  `object_repr` VARCHAR(200) NOT NULL,
  `action_flag` SMALLINT UNSIGNED NOT NULL,
  `change_message` TEXT NOT NULL,
  `content_type_id` INT NULL,
  `user_id` INT NOT NULL,
  `action_time` DATETIME(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_user_id_c564eba6` (`user_id`),
  KEY `django_admin_log_content_type_id_c4bce8eb` (`content_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `django_content_type`;
CREATE TABLE `django_content_type` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `app_label` VARCHAR(100) NOT NULL,
  `model` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`, `model`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `django_migrations`;
CREATE TABLE `django_migrations` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `app` VARCHAR(255) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `applied` DATETIME(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `django_session`;
CREATE TABLE `django_session` (
  `session_key` VARCHAR(40) NOT NULL,
  `session_data` LONGTEXT NOT NULL,
  `expire_date` DATETIME(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `enrollments`;
CREATE TABLE `enrollments` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `enrolled_at` DATETIME(6) NOT NULL,
  `course_id` BIGINT NOT NULL,
  `student_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `enrollments_student_id_19c0bed4` (`student_id`),
  KEY `enrollments_course_id_8964c6c8` (`course_id`),
  UNIQUE KEY `uq_enrollments_course_id_student_id` (`course_id`, `student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `feedback_annotations`;
CREATE TABLE `feedback_annotations` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `anchor` VARCHAR(255) NOT NULL,
  `body` TEXT NOT NULL,
  `file_attachment` VARCHAR(255) NULL,
  `created_at` DATETIME(6) NOT NULL,
  `author_id` INT NOT NULL,
  `grade_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `feedback_annotations_grade_id_ce4e77b9` (`grade_id`),
  KEY `feedback_annotations_author_id_a456e499` (`author_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `grades`;
CREATE TABLE `grades` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `score` DECIMAL(10,2) NOT NULL,
  `feedback` TEXT NOT NULL,
  `is_published` TINYINT(1) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `graded_at` DATETIME(6) NOT NULL,
  `instructor_id` INT NOT NULL,
  `submission_id` BIGINT NOT NULL,
  `published_at` DATETIME(6) NULL,
  `published_by_id` INT NULL,
  PRIMARY KEY (`id`),
  KEY `grades_published_by_id_5f3103e3` (`published_by_id`),
  KEY `grades_instructor_id_28375254` (`instructor_id`),
  UNIQUE KEY `uq_grades_submission_id` (`submission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `portfolio_items`;
CREATE TABLE `portfolio_items` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `item_type` VARCHAR(20) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `reflection` TEXT NOT NULL,
  `skills` VARCHAR(512) NOT NULL,
  `link` VARCHAR(500) NOT NULL,
  `file_attachment` VARCHAR(255) NULL,
  `is_featured` TINYINT(1) NOT NULL,
  `position` INT UNSIGNED NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `grade_id` BIGINT NULL,
  `portfolio_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `portfolio_items_portfolio_id_7df29094` (`portfolio_id`),
  KEY `portfolio_items_grade_id_a7769c7d` (`grade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `portfolios`;
CREATE TABLE `portfolios` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `bio` TEXT NOT NULL,
  `visibility` VARCHAR(16) NOT NULL,
  `share_slug` VARCHAR(64) NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `student_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_portfolios_student_id` (`student_id`),
  UNIQUE KEY `uq_portfolios_share_slug` (`share_slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `project_assessments`;
CREATE TABLE `project_assessments` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `status` VARCHAR(16) NOT NULL,
  `mode` VARCHAR(32) NOT NULL,
  `engine` VARCHAR(16) NOT NULL,
  `model_name` VARCHAR(255) NOT NULL,
  `overall_score` DECIMAL(10,2) NULL,
  `max_score` DECIMAL(10,2) NOT NULL,
  `summary` TEXT NOT NULL,
  `feedback` TEXT NOT NULL,
  `validation` JSON NOT NULL,
  `checks` JSON NOT NULL,
  `structure` JSON NOT NULL,
  `artifacts` JSON NOT NULL,
  `evidence` JSON NOT NULL,
  `raw_response` LONGTEXT NOT NULL,
  `error` TEXT NOT NULL,
  `attempts` INT UNSIGNED NOT NULL,
  `requires_review` TINYINT(1) NOT NULL,
  `review_status` VARCHAR(16) NOT NULL,
  `instructor_score` DECIMAL(10,2) NULL,
  `instructor_feedback` TEXT NOT NULL,
  `reviewed_at` DATETIME(6) NULL,
  `applied_at` DATETIME(6) NULL,
  `created_at` DATETIME(6) NOT NULL,
  `started_at` DATETIME(6) NULL,
  `completed_at` DATETIME(6) NULL,
  `applied_grade_id` BIGINT NULL,
  `requested_by_id` INT NULL,
  `reviewer_id` INT NULL,
  `rubric_version_id` BIGINT NULL,
  `snapshot_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_assess_status` (`status`, `created_at`),
  KEY `idx_assess_snapshot` (`snapshot_id`, `created_at` DESC),
  KEY `project_assessments_snapshot_id_ebcac8ed` (`snapshot_id`),
  KEY `project_assessments_rubric_version_id_bc9fee49` (`rubric_version_id`),
  KEY `project_assessments_reviewer_id_e421df58` (`reviewer_id`),
  KEY `project_assessments_requested_by_id_c6d2a9d2` (`requested_by_id`),
  UNIQUE KEY `uq_project_assessments_applied_grade_id` (`applied_grade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `project_criterion_assessments`;
CREATE TABLE `project_criterion_assessments` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `criterion_name` VARCHAR(255) NOT NULL,
  `position` INT UNSIGNED NOT NULL,
  `max_points` DECIMAL(10,2) NOT NULL,
  `ai_points` DECIMAL(10,2) NOT NULL,
  `instructor_points` DECIMAL(10,2) NULL,
  `comment` TEXT NOT NULL,
  `evidence` TEXT NOT NULL,
  `confidence` DECIMAL(10,4) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `assessment_id` BIGINT NOT NULL,
  `criterion_id` BIGINT NULL,
  PRIMARY KEY (`id`),
  KEY `project_criterion_assessments_criterion_id_6dfa5477` (`criterion_id`),
  KEY `project_criterion_assessments_assessment_id_84227a39` (`assessment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `project_pull_request_comments`;
CREATE TABLE `project_pull_request_comments` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `body` TEXT NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `author_id` INT NOT NULL,
  `pull_request_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `project_pull_request_comments_pull_request_id_da29fe76` (`pull_request_id`),
  KEY `project_pull_request_comments_author_id_4b9a6171` (`author_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `project_pull_requests`;
CREATE TABLE `project_pull_requests` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `source_branch` VARCHAR(128) NOT NULL,
  `target_branch` VARCHAR(128) NOT NULL,
  `status` VARCHAR(16) NOT NULL,
  `merge_commit_sha` VARCHAR(64) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `merged_at` DATETIME(6) NULL,
  `created_by_id` INT NULL,
  `merged_snapshot_id` BIGINT NULL,
  `project_id` BIGINT NOT NULL,
  `reviewed_by_id` INT NULL,
  `source_snapshot_id` BIGINT NULL,
  `revision_request_id` BIGINT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_pr_project_status` (`project_id`, `status`),
  KEY `project_pull_requests_revision_request_id_ec5c5eac` (`revision_request_id`),
  KEY `project_pull_requests_source_snapshot_id_16e0d46f` (`source_snapshot_id`),
  KEY `project_pull_requests_reviewed_by_id_3bb6ce18` (`reviewed_by_id`),
  KEY `project_pull_requests_project_id_ea8e657d` (`project_id`),
  KEY `project_pull_requests_merged_snapshot_id_e7bfb3df` (`merged_snapshot_id`),
  KEY `project_pull_requests_created_by_id_9dca8abe` (`created_by_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `project_repositories`;
CREATE TABLE `project_repositories` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `provider` VARCHAR(32) NOT NULL,
  `remote_url` VARCHAR(500) NOT NULL,
  `default_branch` VARCHAR(128) NOT NULL,
  `current_branch` VARCHAR(128) NOT NULL,
  `last_commit_sha` VARCHAR(64) NOT NULL,
  `git_initialised` TINYINT(1) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `project_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_project_repositories_project_id` (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `project_revision_requests`;
CREATE TABLE `project_revision_requests` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `branch_name` VARCHAR(128) NOT NULL,
  `due_date` DATETIME(6) NULL,
  `status` VARCHAR(16) NOT NULL,
  `resolved_at` DATETIME(6) NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `project_id` BIGINT NOT NULL,
  `requested_by_id` INT NULL,
  `resolved_by_id` INT NULL,
  `snapshot_id` BIGINT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_revision_project_status` (`project_id`, `status`),
  KEY `project_revision_requests_snapshot_id_0d32a1fb` (`snapshot_id`),
  KEY `project_revision_requests_resolved_by_id_563ba021` (`resolved_by_id`),
  KEY `project_revision_requests_requested_by_id_f82749a0` (`requested_by_id`),
  KEY `project_revision_requests_project_id_023fb418` (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `project_snapshots`;
CREATE TABLE `project_snapshots` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `version` INT UNSIGNED NOT NULL,
  `source` VARCHAR(16) NOT NULL,
  `branch` VARCHAR(128) NOT NULL,
  `archive` VARCHAR(255) NOT NULL,
  `checksum` VARCHAR(64) NOT NULL,
  `commit_sha` VARCHAR(64) NOT NULL,
  `base_commit_sha` VARCHAR(64) NOT NULL,
  `file_count` INT UNSIGNED NOT NULL,
  `total_bytes` BIGINT NOT NULL,
  `manifest` JSON NOT NULL,
  `validation` JSON NOT NULL,
  `metadata` JSON NOT NULL,
  `note` VARCHAR(500) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `created_by_id` INT NULL,
  `project_id` BIGINT NOT NULL,
  `submission_id` BIGINT NULL,
  `parent_id` BIGINT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_snapshot_checksum` (`checksum`),
  KEY `idx_snapshot_project_version` (`project_id`, `version` DESC),
  KEY `project_snapshots_parent_id_d60bbfb0` (`parent_id`),
  KEY `project_snapshots_project_id_4843d191` (`project_id`),
  KEY `project_snapshots_created_by_id_2e24dd59` (`created_by_id`),
  UNIQUE KEY `uq_project_snapshots_project_id_version` (`project_id`, `version`),
  UNIQUE KEY `uq_project_snapshots_submission_id` (`submission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `project_workspaces`;
CREATE TABLE `project_workspaces` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `status` VARCHAR(16) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `assignment_id` BIGINT NOT NULL,
  `student_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_project_student_status` (`student_id`, `status`),
  KEY `project_workspaces_student_id_113571d8` (`student_id`),
  KEY `project_workspaces_assignment_id_db2a83b7` (`assignment_id`),
  UNIQUE KEY `uq_project_workspaces_assignment_id_student_id` (`assignment_id`, `student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `rubric_criteria`;
CREATE TABLE `rubric_criteria` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `max_points` DECIMAL(10,2) NOT NULL,
  `weight` DECIMAL(10,4) NOT NULL,
  `position` INT UNSIGNED NOT NULL,
  `rubric_id` BIGINT NOT NULL,
  `ai_instructions` TEXT NOT NULL,
  `expected_evidence` TEXT NOT NULL,
  `feedback_requirements` TEXT NOT NULL,
  `scoring_guidance` TEXT NOT NULL,
  `validation_rule` VARCHAR(64) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `rubric_criteria_rubric_id_2ca5a4e8` (`rubric_id`),
  UNIQUE KEY `uq_rubric_criteria_rubric_id_name` (`rubric_id`, `name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `rubric_versions`;
CREATE TABLE `rubric_versions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `version` INT UNSIGNED NOT NULL,
  `snapshot` JSON NOT NULL,
  `total_points` DECIMAL(10,2) NOT NULL,
  `notes` TEXT NOT NULL,
  `published_at` DATETIME(6) NOT NULL,
  `assignment_id` BIGINT NOT NULL,
  `published_by_id` INT NULL,
  `rubric_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_rubric_versions_assignment` (`assignment_id`, `version` DESC),
  KEY `rubric_versions_rubric_id_fc537d08` (`rubric_id`),
  KEY `rubric_versions_published_by_id_a0155f1b` (`published_by_id`),
  KEY `rubric_versions_assignment_id_6f8a27e7` (`assignment_id`),
  UNIQUE KEY `uq_rubric_versions_rubric_id_version` (`rubric_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `rubrics`;
CREATE TABLE `rubrics` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `instructions` TEXT NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `assignment_id` BIGINT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_rubrics_assignment_id` (`assignment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `submissions`;
CREATE TABLE `submissions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `version` INT UNSIGNED NOT NULL,
  `file_attachment` VARCHAR(255) NULL,
  `text_content` TEXT NULL,
  `submitted_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `assignment_id` BIGINT NOT NULL,
  `student_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_submissions_asgmt_student` (`assignment_id`, `student_id`),
  KEY `submissions_student_id_b2b21be5` (`student_id`),
  KEY `submissions_assignment_id_835bcd69` (`assignment_id`),
  UNIQUE KEY `uq_submissions_assignment_id_student_id_version` (`assignment_id`, `student_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `tblattendance`;
CREATE TABLE `tblattendance` (
  `attend_id` INT NOT NULL AUTO_INCREMENT,
  `attend_date` DATE NOT NULL,
  `status` VARCHAR(50) NOT NULL,
  `date_added` DATETIME(6) NOT NULL,
  `student_id` INT NOT NULL,
  PRIMARY KEY (`attend_id`),
  KEY `tblattendance_student_id_05f46e8d` (`student_id`),
  UNIQUE KEY `uq_tblattendance_student_id_attend_date` (`student_id`, `attend_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `tblcourse`;
CREATE TABLE `tblcourse` (
  `courseid` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `section` VARCHAR(100) NOT NULL,
  `schoolyr` VARCHAR(100) NOT NULL,
  `status` VARCHAR(20) NOT NULL,
  `user_id` INT NULL,
  PRIMARY KEY (`courseid`),
  KEY `tblcourse_user_id_b85e850b` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `tblcourseschedule`;
CREATE TABLE `tblcourseschedule` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `day` INT NOT NULL,
  `start_time` TIME(6) NOT NULL,
  `end_time` TIME(6) NOT NULL,
  `room` VARCHAR(100) NOT NULL,
  `course_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `tblcourseschedule_course_id_7a9e0106` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `tblinfo`;
CREATE TABLE `tblinfo` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `age` INT UNSIGNED NOT NULL,
  `address` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `user_id` INT NULL,
  `id_number` VARCHAR(50) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `tblinfo_user_id_4a36749d` (`user_id`),
  UNIQUE KEY `uq_tblinfo_id_number` (`id_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `tblquiz`;
CREATE TABLE `tblquiz` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `is_active` TINYINT(1) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `course_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `tblquiz_course_id_1e0348f5` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `tblquizquestion`;
CREATE TABLE `tblquizquestion` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `question_text` TEXT NOT NULL,
  `option_a` VARCHAR(255) NOT NULL,
  `option_b` VARCHAR(255) NOT NULL,
  `option_c` VARCHAR(255) NOT NULL,
  `option_d` VARCHAR(255) NOT NULL,
  `order` INT UNSIGNED NOT NULL,
  `quiz_id` BIGINT NOT NULL,
  `question_type` VARCHAR(20) NOT NULL,
  `correct_option` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `tblquizquestion_quiz_id_45191b5a` (`quiz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `tblstudents`;
CREATE TABLE `tblstudents` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `idno` VARCHAR(50) NOT NULL,
  `fullname` VARCHAR(255) NOT NULL,
  `courseid` VARCHAR(50) NOT NULL,
  `enrollment_type` VARCHAR(20) NOT NULL,
  `user_id` INT NULL,
  PRIMARY KEY (`id`),
  KEY `tblstudents_user_id_48a1234d` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `user_profiles`;
CREATE TABLE `user_profiles` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `role` VARCHAR(20) NOT NULL,
  `created_at` DATETIME(6) NOT NULL,
  `updated_at` DATETIME(6) NOT NULL,
  `user_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_profiles_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------
-- DATA
-- ---------------------------------------------------------------
-- activity_logs: 82 rows
INSERT INTO `activity_logs` (`id`, `action`, `entity_type`, `entity_id`, `description`, `ip_address`, `user_agent`, `metadata`, `created_at`, `actor_id`) VALUES
(1, 'auth.login_failed', 'User', '', 'Failed sign-in for username "Cj2"', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:30:20.244192', NULL),
(2, 'auth.login_failed', 'User', '', 'Failed sign-in for username "Cj"', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:30:25.512657', NULL),
(3, 'auth.registered', 'User', '21', 'New student account "Cj" registered', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:30:54.413188', 21),
(4, 'auth.logout', 'User', '21', 'Cj signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:31:04.571146', 21),
(5, 'auth.login', 'User', '21', 'Cj signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:31:08.425648', 21),
(6, 'auth.logout', 'User', '21', 'Cj signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:31:12.125975', 21),
(7, 'auth.registered', 'User', '22', 'New instructor account "CjInstructor1" registered', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:31:41.423358', 22),
(8, 'auth.logout', 'User', '22', 'CjInstructor1 signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:31:43.778296', 22),
(9, 'auth.login', 'User', '21', 'Cj signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:32:15.766473', 21),
(10, 'auth.logout', 'User', '21', 'Cj signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:32:51.875563', 21),
(11, 'auth.login', 'User', '22', 'CjInstructor1 signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:32:57.221721', 22),
(12, 'course.created', 'Course', '1', 'Created course ITE201', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:33:37.129630', 22),
(13, 'assignment.created', 'Assignment', '1', 'Created assignment "SYSTEM INITIAL DATABASE DESIGN" in ITE201', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1}', '2026-10-27 09:42:46.319128', 22),
(14, 'auth.logout', 'User', '22', 'CjInstructor1 signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:52:39.185226', 22),
(15, 'auth.login', 'User', '21', 'Cj signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:52:43.170614', 21),
(16, 'course.enrolled', 'Course', '1', 'Enrolled in ITE201', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1}', '2026-10-27 09:52:52.351196', 21),
(17, 'submission.created', 'Submission', '1', 'Uploaded v1 for "SYSTEM INITIAL DATABASE DESIGN"', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1}', '2026-10-27 09:57:46.282793', 21),
(18, 'auth.logout', 'User', '21', 'Cj signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:57:51.221966', 21),
(19, 'auth.login', 'User', '22', 'CjInstructor1 signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:57:57.138811', 22),
(20, 'ai.evaluation.requested', 'AIEvaluation', '1', 'AI draft requested for v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 1}', '2026-10-27 09:58:05.593637', 22),
(21, 'ai.evaluation.completed', 'AIEvaluation', '1', 'AI draft completed for v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 1, "flags": 0}', '2026-10-27 09:58:06.221243', 22),
(22, 'ai.evaluation.requested', 'AIEvaluation', '2', 'AI draft requested for v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 1}', '2026-10-27 09:58:19.708197', 22),
(23, 'ai.evaluation.completed', 'AIEvaluation', '2', 'AI draft completed for v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 1, "flags": 0}', '2026-10-27 09:58:20.058764', 22),
(24, 'ai.evaluation.applied', 'AIEvaluation', '2', 'AI draft applied to a draft grade for v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 1, "grade_id": 1, "published": false}', '2026-10-27 09:58:29.243849', 22),
(25, 'ai.evaluation.reviewed', 'AIEvaluation', '2', 'Instructor opened AI-assisted grading for v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1, "grade_id": 1}', '2026-10-27 09:58:29.373350', 22),
(26, 'grade.saved', 'Grade', '1', 'Graded submission v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1, "assignment_id": 1, "submission_id": 1, "published": false}', '2026-10-27 09:58:49.325268', 22),
(27, 'auth.logout', 'User', '22', 'CjInstructor1 signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:59:01.309000', 22),
(28, 'auth.login', 'User', '21', 'Cj signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:59:07.370305', 21),
(29, 'auth.logout', 'User', '21', 'Cj signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:59:20.886164', 21),
(30, 'auth.login', 'User', '22', 'CjInstructor1 signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 09:59:27.102312', 22),
(31, 'grade.published', 'Grade', '1', 'Published grade for v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1}', '2026-10-27 09:59:55.925822', 22),
(32, 'grade.saved', 'Grade', '1', 'Graded submission v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1, "assignment_id": 1, "submission_id": 1, "published": true}', '2026-10-27 10:00:21.678218', 22),
(33, 'auth.logout', 'User', '22', 'CjInstructor1 signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 10:00:30.395051', 22),
(34, 'auth.login', 'User', '21', 'Cj signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-27 10:00:37.065112', 21),
(35, 'auth.login', 'User', '21', 'Cj signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-28 01:47:26.753870', 21),
(36, 'auth.logout', 'User', '21', 'Cj signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-28 23:36:58.889690', 21),
(37, 'auth.login', 'User', '22', 'CjInstructor1 signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-28 23:37:05.221852', 22),
(38, 'auth.logout', 'User', '22', 'CjInstructor1 signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 06:48:38.959555', 22),
(39, 'auth.login', 'User', '21', 'Cj signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 07:10:13.770584', 21),
(40, 'api.token.created', 'ApiToken', '1', 'API token created for Cj', '127.0.0.1', 'node', '{}', '2026-10-29 07:11:34.856280', 21),
(41, 'project.snapshot.created', 'ProjectSnapshot', '1', 'Uploaded project snapshot v1 for SYSTEM INITIAL DATABASE DESIGN', '127.0.0.1', 'node', '{"course_id": 1, "assignment_id": 1, "project_id": 1, "file_count": 2}', '2026-10-29 07:13:26.492185', 21),
(42, 'assessment.requested', 'Assessment', '1', 'Project assessment requested for SYSTEM INITIAL DATABASE DESIGN v1', NULL, '', '{"course_id": 1, "assignment_id": 1, "project_id": 1, "snapshot_id": 1}', '2026-10-29 07:13:26.753692', 21),
(43, 'assessment.completed', 'Assessment', '1', 'Assessment completed for SYSTEM INITIAL DATABASE DESIGN v1', NULL, '', '{"course_id": 1, "assignment_id": 1, "project_id": 1, "snapshot_id": 1, "engine": "local", "score": "100.00", "requires_review": true}', '2026-10-29 07:13:27.214110', 21),
(44, 'api.token.created', 'ApiToken', '2', 'API token created from the web UI', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 07:17:20.889586', 21),
(45, 'api.token.revoked', 'ApiToken', '2', 'API token revoked from the web UI', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 07:17:41.299753', 21),
(46, 'auth.logout', 'User', '21', 'Cj signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 07:26:55.418036', 21),
(47, 'auth.login', 'User', '22', 'CjInstructor1 signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 07:26:59.487326', 22),
(48, 'ai.evaluation.requested', 'AIEvaluation', '3', 'AI draft requested for v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 1}', '2026-10-29 07:37:31.784834', 22),
(49, 'ai.evaluation.completed', 'AIEvaluation', '3', 'AI draft completed for v1 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 1, "flags": 0}', '2026-10-29 07:37:32.320177', 22),
(50, 'ai.evaluation.requested', 'AIEvaluation', '4', 'AI draft requested for v2 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 2}', '2026-10-29 07:37:45.887486', 22),
(51, 'ai.evaluation.completed', 'AIEvaluation', '4', 'AI draft completed for v2 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 2, "flags": 0}', '2026-10-29 07:37:46.475048', 22),
(52, 'ai.evaluation.requested', 'AIEvaluation', '5', 'AI draft requested for v2 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 2}', '2026-10-29 07:38:52.071638', 22),
(53, 'ai.evaluation.completed', 'AIEvaluation', '5', 'AI draft completed for v2 by Cj for SYSTEM INITIAL DATABASE DESIGN (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 1, "submission_id": 2, "flags": 0}', '2026-10-29 07:38:52.595606', 22),
(54, 'assignment.created', 'Assignment', '2', 'Created assignment "Hello World Test Project" in ITE201', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1}', '2026-10-29 07:59:56.753158', 22),
(55, 'auth.logout', 'User', '22', 'CjInstructor1 signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 08:00:02.051516', 22),
(56, 'auth.login', 'User', '21', 'Cj signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 08:00:05.895633', 21),
(57, 'api.token.created', 'ApiToken', '3', 'API token created for Cj', '127.0.0.1', 'node', '{}', '2026-10-29 08:03:49.095134', 21),
(58, 'api.token.created', 'ApiToken', '4', 'API token created for Cj', '127.0.0.1', 'node', '{}', '2026-10-29 23:43:21.196720', 21),
(59, 'project.snapshot.created', 'ProjectSnapshot', '2', 'Uploaded project snapshot v1 for Hello World Test Project', '127.0.0.1', 'node', '{"course_id": 1, "assignment_id": 2, "project_id": 2, "file_count": 1}', '2026-10-29 23:44:28.660425', 21),
(60, 'assessment.requested', 'Assessment', '2', 'Project assessment requested for Hello World Test Project v1', NULL, '', '{"course_id": 1, "assignment_id": 2, "project_id": 2, "snapshot_id": 2}', '2026-10-29 23:44:28.893868', 21),
(61, 'assessment.completed', 'Assessment', '2', 'Assessment completed for Hello World Test Project v1', NULL, '', '{"course_id": 1, "assignment_id": 2, "project_id": 2, "snapshot_id": 2, "engine": "local", "score": "100.00", "requires_review": true}', '2026-10-29 23:44:29.495152', 21),
(62, 'auth.logout', 'User', '21', 'Cj signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 23:45:28.185310', 21),
(63, 'auth.login', 'User', '22', 'CjInstructor1 signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 23:45:33.142514', 22),
(64, 'ai.evaluation.requested', 'AIEvaluation', '6', 'AI draft requested for v1 by Cj for Hello World Test Project (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 2, "submission_id": 3}', '2026-10-29 23:45:48.308414', 22),
(65, 'ai.evaluation.completed', 'AIEvaluation', '6', 'AI draft completed for v1 by Cj for Hello World Test Project (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 2, "submission_id": 3, "flags": 1}', '2026-10-29 23:45:48.825956', 22),
(66, 'ai.evaluation.applied', 'AIEvaluation', '6', 'AI draft applied to a draft grade for v1 by Cj for Hello World Test Project (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 2, "submission_id": 3, "grade_id": 2, "published": false}', '2026-10-29 23:46:39.063988', 22),
(67, 'ai.evaluation.reviewed', 'AIEvaluation', '6', 'Instructor opened AI-assisted grading for v1 by Cj for Hello World Test Project (ITE201)', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1, "grade_id": 2}', '2026-10-29 23:46:39.186892', 22),
(68, 'grade.published', 'Grade', '2', 'Published grade for v1 by Cj for Hello World Test Project (ITE201)', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1}', '2026-10-29 23:47:01.395161', 22),
(69, 'auth.logout', 'User', '22', 'CjInstructor1 signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 23:48:05.004136', 22),
(70, 'auth.registered', 'User', '23', 'New student account "Cj1" registered', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 23:48:43.291210', 23),
(71, 'course.enrolled', 'Course', '1', 'Enrolled in ITE201', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1}', '2026-10-29 23:48:51.768651', 23),
(72, 'auth.logout', 'User', '23', 'Cj1 signed out', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 23:49:23.536182', 23),
(73, 'auth.login', 'User', '22', 'CjInstructor1 signed in', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{}', '2026-10-29 23:49:30.115807', 22),
(74, 'api.token.created', 'ApiToken', '5', 'API token created for Cj1', '127.0.0.1', 'node', '{}', '2026-10-29 23:55:46.835015', 23),
(75, 'project.snapshot.created', 'ProjectSnapshot', '3', 'Uploaded project snapshot v1 for Hello World Test Project', '127.0.0.1', 'node', '{"course_id": 1, "assignment_id": 2, "project_id": 3, "file_count": 2}', '2026-10-29 23:56:20.183289', 23),
(76, 'assessment.requested', 'Assessment', '3', 'Project assessment requested for Hello World Test Project v1', NULL, '', '{"course_id": 1, "assignment_id": 2, "project_id": 3, "snapshot_id": 3}', '2026-10-29 23:56:20.407040', 23),
(77, 'assessment.completed', 'Assessment', '3', 'Assessment completed for Hello World Test Project v1', NULL, '', '{"course_id": 1, "assignment_id": 2, "project_id": 3, "snapshot_id": 3, "engine": "local", "score": "100.00", "requires_review": true}', '2026-10-29 23:56:20.916443', 23),
(78, 'assessment.applied', 'Assessment', '3', 'Assessment applied to a draft grade for Cj1', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1, "assessment_id": 3, "grade_id": 3}', '2026-10-29 23:57:25.257756', 22),
(79, 'ai.evaluation.requested', 'AIEvaluation', '7', 'AI draft requested for v1 by Cj1 for Hello World Test Project (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 2, "submission_id": 4}', '2026-10-29 23:59:30.533129', 22),
(80, 'ai.evaluation.completed', 'AIEvaluation', '7', 'AI draft completed for v1 by Cj1 for Hello World Test Project (ITE201)', NULL, '', '{"course_id": 1, "assignment_id": 2, "submission_id": 4, "flags": 0}', '2026-10-29 23:59:31.189704', 22),
(81, 'grade.saved', 'Grade', '2', 'Graded submission v1 by Cj for Hello World Test Project (ITE201)', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1, "assignment_id": 2, "submission_id": 3, "published": true}', '2026-10-30 00:00:15.591024', 22),
(82, 'grade.published', 'Grade', '3', 'Published grade for v1 by Cj1 for Hello World Test Project (ITE201)', '127.0.0.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36', '{"course_id": 1}', '2026-10-30 00:00:23.088114', 22);

-- ai_evaluations: 2 rows
INSERT INTO `ai_evaluations` (`id`, `status`, `mode`, `model_name`, `suggested_score`, `suggested_feedback`, `summary`, `suggested_criteria`, `guideline_snapshot`, `inspection`, `raw_response`, `error`, `created_at`, `started_at`, `completed_at`, `applied_at`, `applied_by_id`, `requested_by_id`, `submission_id`) VALUES
(6, 'completed', 'draft', 'classforge-local-inspector', 87.5, 'Automated inspection of submission v1 (zip).\nDetected 1 archive file(s); 1 source file(s) and 0 documentation file(s).\n\nDraft findings:\n• [info] No README file was found in the code archive.\n\nThis is an AI-assisted draft only. Final scores and comments must be reviewed by the instructor.', '1 finding(s): 0 critical, 0 warning(s), 1 informational.', '[]', 'create a folder containing a helloworld.php file with basic HTML inside, and explain how to run it on a local web server.', '{"submission_id": 3, "version": 1, "submission_type": "zip", "file_name": "project-2-v1.zip", "file_type": ".zip", "file_count": 1, "total_uncompressed_size": 263, "files": ["helloworld.php"], "source_file_count": 1, "doc_file_count": 0, "has_readme": false, "pdf_pages": 0, "issues": [{"kind": "structural_discrepancy", "severity": "info", "message": "No README file was found in the code archive.", "evidence": ""}], "notes": ["test"]}', '', '', '2026-10-29 23:45:48.174143', '2026-10-29 23:45:48.404687', '2026-10-29 23:45:48.492454', '2026-10-29 23:46:38.930359', 22, 22, 3),
(7, 'completed', 'draft', 'classforge-local-inspector', 88, 'Automated inspection of submission v1 (zip).\nDetected 2 archive file(s); 1 source file(s) and 1 documentation file(s).\nNo structural anomalies were detected by the local inspector.\n\nThis is an AI-assisted draft only. Final scores and comments must be reviewed by the instructor.', '0 finding(s): 0 critical, 0 warning(s), 0 informational.', '[]', 'create a folder containing a helloworld.php file with basic HTML inside, and explain how to run it on a local web server.', '{"submission_id": 4, "version": 1, "submission_type": "zip", "file_name": "project-3-v1.zip", "file_type": ".zip", "file_count": 2, "total_uncompressed_size": 416, "files": ["README.md", "helloworld.php"], "source_file_count": 1, "doc_file_count": 1, "has_readme": true, "pdf_pages": 0, "issues": [], "notes": ["done readme"]}', '', '', '2026-10-29 23:59:30.400469', '2026-10-29 23:59:30.678749', '2026-10-29 23:59:30.834340', NULL, NULL, 22, 4);

-- ai_flags: 1 rows
INSERT INTO `ai_flags` (`id`, `kind`, `severity`, `message`, `evidence`, `created_at`, `evaluation_id`) VALUES
(7, 'structural_discrepancy', 'info', 'No README file was found in the code archive.', '', '2026-10-29 23:45:48.668954', 6);

-- assignment_seen: 2 rows
INSERT INTO `assignment_seen` (`id`, `seen_at`, `assignment_id`, `student_id`) VALUES
(2, '2026-10-29 08:00:06.934224', 2, 21),
(3, '2026-10-29 23:48:55.878533', 2, 23);

-- assignments: 1 rows
INSERT INTO `assignments` (`id`, `title`, `description`, `due_date`, `max_score`, `created_at`, `updated_at`, `course_id`, `category`, `accepts_pdf`, `accepts_zip`, `ai_auto_run`, `guidelines`, `required_files`, `accepted_formats`, `ai_grading_mode`, `allow_resubmission`, `default_exclusions`, `documentation_requirements`, `expected_outcomes`, `late_penalty_percent`, `late_policy`, `manual_review_required`, `max_upload_mb`, `published_at`, `required_directories`, `required_tests`, `revision_deadline_days`, `status`, `validation_rules`) VALUES
(2, 'Hello World Test Project', '"Please create a folder containing a helloworld.php file with basic HTML inside, and explain how to run it on a local web server.', '2026-10-30 15:55:00', 100, '2026-10-29 07:59:56.213781', '2026-10-29 23:47:49.655638', 1, 'code_project', 1, 1, 1, 'create a folder containing a helloworld.php file with basic HTML inside, and explain how to run it on a local web server.', '', '', 'automatic', 1, '', '', '', 0, 'accept', 1, 25, '2026-10-29 07:59:56.490934', '', '', 7, 'published', '');

-- auth_permission: 164 rows
INSERT INTO `auth_permission` (`id`, `content_type_id`, `codename`, `name`) VALUES
(1, 1, 'add_logentry', 'Can add log entry'),
(2, 1, 'change_logentry', 'Can change log entry'),
(3, 1, 'delete_logentry', 'Can delete log entry'),
(4, 1, 'view_logentry', 'Can view log entry'),
(5, 3, 'add_permission', 'Can add permission'),
(6, 3, 'change_permission', 'Can change permission'),
(7, 3, 'delete_permission', 'Can delete permission'),
(8, 3, 'view_permission', 'Can view permission'),
(9, 2, 'add_group', 'Can add group'),
(10, 2, 'change_group', 'Can change group'),
(11, 2, 'delete_group', 'Can delete group'),
(12, 2, 'view_group', 'Can view group'),
(13, 4, 'add_user', 'Can add user'),
(14, 4, 'change_user', 'Can change user'),
(15, 4, 'delete_user', 'Can delete user'),
(16, 4, 'view_user', 'Can view user'),
(17, 5, 'add_contenttype', 'Can add content type'),
(18, 5, 'change_contenttype', 'Can change content type'),
(19, 5, 'delete_contenttype', 'Can delete content type'),
(20, 5, 'view_contenttype', 'Can view content type'),
(21, 6, 'add_session', 'Can add session'),
(22, 6, 'change_session', 'Can change session'),
(23, 6, 'delete_session', 'Can delete session'),
(24, 6, 'view_session', 'Can view session'),
(25, 10, 'add_tblcourse', 'Can add tblcourse'),
(26, 10, 'change_tblcourse', 'Can change tblcourse'),
(27, 10, 'delete_tblcourse', 'Can delete tblcourse'),
(28, 10, 'view_tblcourse', 'Can view tblcourse'),
(29, 8, 'add_quiz', 'Can add quiz'),
(30, 8, 'change_quiz', 'Can change quiz'),
(31, 8, 'delete_quiz', 'Can delete quiz'),
(32, 8, 'view_quiz', 'Can view quiz'),
(33, 9, 'add_quizquestion', 'Can add quiz question'),
(34, 9, 'change_quizquestion', 'Can change quiz question'),
(35, 9, 'delete_quizquestion', 'Can delete quiz question'),
(36, 9, 'view_quizquestion', 'Can view quiz question'),
(37, 7, 'add_courseschedule', 'Can add course schedule'),
(38, 7, 'change_courseschedule', 'Can change course schedule'),
(39, 7, 'delete_courseschedule', 'Can delete course schedule'),
(40, 7, 'view_courseschedule', 'Can view course schedule'),
(41, 11, 'add_tblstudents', 'Can add tblstudents'),
(42, 11, 'change_tblstudents', 'Can change tblstudents'),
(43, 11, 'delete_tblstudents', 'Can delete tblstudents'),
(44, 11, 'view_tblstudents', 'Can view tblstudents'),
(45, 12, 'add_tblattendance', 'Can add tblattendance'),
(46, 12, 'change_tblattendance', 'Can change tblattendance'),
(47, 12, 'delete_tblattendance', 'Can delete tblattendance'),
(48, 12, 'view_tblattendance', 'Can view tblattendance'),
(49, 13, 'add_info', 'Can add info'),
(50, 13, 'change_info', 'Can change info'),
(51, 13, 'delete_info', 'Can delete info'),
(52, 13, 'view_info', 'Can view info'),
(53, 15, 'add_course', 'Can add course'),
(54, 15, 'change_course', 'Can change course'),
(55, 15, 'delete_course', 'Can delete course'),
(56, 15, 'view_course', 'Can view course'),
(57, 16, 'add_enrollment', 'Can add enrollment'),
(58, 16, 'change_enrollment', 'Can change enrollment'),
(59, 16, 'delete_enrollment', 'Can delete enrollment'),
(60, 16, 'view_enrollment', 'Can view enrollment'),
(61, 17, 'add_grade', 'Can add grade'),
(62, 17, 'change_grade', 'Can change grade'),
(63, 17, 'delete_grade', 'Can delete grade'),
(64, 17, 'view_grade', 'Can view grade'),
(65, 14, 'add_assignment', 'Can add assignment'),
(66, 14, 'change_assignment', 'Can change assignment'),
(67, 14, 'delete_assignment', 'Can delete assignment'),
(68, 14, 'view_assignment', 'Can view assignment'),
(69, 18, 'add_submission', 'Can add submission'),
(70, 18, 'change_submission', 'Can change submission'),
(71, 18, 'delete_submission', 'Can delete submission'),
(72, 18, 'view_submission', 'Can view submission'),
(73, 19, 'add_activitylog', 'Can add activity log'),
(74, 19, 'change_activitylog', 'Can change activity log'),
(75, 19, 'delete_activitylog', 'Can delete activity log'),
(76, 19, 'view_activitylog', 'Can view activity log'),
(77, 20, 'add_userprofile', 'Can add user profile'),
(78, 20, 'change_userprofile', 'Can change user profile'),
(79, 20, 'delete_userprofile', 'Can delete user profile'),
(80, 20, 'view_userprofile', 'Can view user profile'),
(81, 21, 'add_courseassistant', 'Can add course assistant'),
(82, 21, 'change_courseassistant', 'Can change course assistant'),
(83, 21, 'delete_courseassistant', 'Can delete course assistant'),
(84, 21, 'view_courseassistant', 'Can view course assistant'),
(85, 22, 'add_feedbackannotation', 'Can add feedback annotation'),
(86, 22, 'change_feedbackannotation', 'Can change feedback annotation'),
(87, 22, 'delete_feedbackannotation', 'Can delete feedback annotation'),
(88, 22, 'view_feedbackannotation', 'Can view feedback annotation'),
(89, 23, 'add_rubric', 'Can add rubric'),
(90, 23, 'change_rubric', 'Can change rubric'),
(91, 23, 'delete_rubric', 'Can delete rubric'),
(92, 23, 'view_rubric', 'Can view rubric'),
(93, 24, 'add_rubriccriterion', 'Can add rubric criterion'),
(94, 24, 'change_rubriccriterion', 'Can change rubric criterion'),
(95, 24, 'delete_rubriccriterion', 'Can delete rubric criterion'),
(96, 24, 'view_rubriccriterion', 'Can view rubric criterion'),
(97, 25, 'add_criterionscore', 'Can add criterion score'),
(98, 25, 'change_criterionscore', 'Can change criterion score'),
(99, 25, 'delete_criterionscore', 'Can delete criterion score'),
(100, 25, 'view_criterionscore', 'Can view criterion score');
INSERT INTO `auth_permission` (`id`, `content_type_id`, `codename`, `name`) VALUES
(101, 26, 'add_aievaluation', 'Can add ai evaluation'),
(102, 26, 'change_aievaluation', 'Can change ai evaluation'),
(103, 26, 'delete_aievaluation', 'Can delete ai evaluation'),
(104, 26, 'view_aievaluation', 'Can view ai evaluation'),
(105, 27, 'add_aiflag', 'Can add ai flag'),
(106, 27, 'change_aiflag', 'Can change ai flag'),
(107, 27, 'delete_aiflag', 'Can delete ai flag'),
(108, 27, 'view_aiflag', 'Can view ai flag'),
(109, 28, 'add_portfolio', 'Can add portfolio'),
(110, 28, 'change_portfolio', 'Can change portfolio'),
(111, 28, 'delete_portfolio', 'Can delete portfolio'),
(112, 28, 'view_portfolio', 'Can view portfolio'),
(113, 29, 'add_portfolioitem', 'Can add portfolio item'),
(114, 29, 'change_portfolioitem', 'Can change portfolio item'),
(115, 29, 'delete_portfolioitem', 'Can delete portfolio item'),
(116, 29, 'view_portfolioitem', 'Can view portfolio item'),
(117, 30, 'add_assignmentseen', 'Can add assignment seen'),
(118, 30, 'change_assignmentseen', 'Can change assignment seen'),
(119, 30, 'delete_assignmentseen', 'Can delete assignment seen'),
(120, 30, 'view_assignmentseen', 'Can view assignment seen'),
(121, 31, 'add_rubricversion', 'Can add rubric version'),
(122, 31, 'change_rubricversion', 'Can change rubric version'),
(123, 31, 'delete_rubricversion', 'Can delete rubric version'),
(124, 31, 'view_rubricversion', 'Can view rubric version'),
(125, 32, 'add_apitoken', 'Can add api token'),
(126, 32, 'change_apitoken', 'Can change api token'),
(127, 32, 'delete_apitoken', 'Can delete api token'),
(128, 32, 'view_apitoken', 'Can view api token'),
(129, 33, 'add_assessment', 'Can add assessment'),
(130, 33, 'change_assessment', 'Can change assessment'),
(131, 33, 'delete_assessment', 'Can delete assessment'),
(132, 33, 'view_assessment', 'Can view assessment'),
(133, 34, 'add_criterionassessment', 'Can add criterion assessment'),
(134, 34, 'change_criterionassessment', 'Can change criterion assessment'),
(135, 34, 'delete_criterionassessment', 'Can delete criterion assessment'),
(136, 34, 'view_criterionassessment', 'Can view criterion assessment'),
(137, 36, 'add_project', 'Can add project'),
(138, 36, 'change_project', 'Can change project'),
(139, 36, 'delete_project', 'Can delete project'),
(140, 36, 'view_project', 'Can view project'),
(141, 37, 'add_projectsnapshot', 'Can add project snapshot'),
(142, 37, 'change_projectsnapshot', 'Can change project snapshot'),
(143, 37, 'delete_projectsnapshot', 'Can delete project snapshot'),
(144, 37, 'view_projectsnapshot', 'Can view project snapshot'),
(145, 35, 'add_notification', 'Can add notification'),
(146, 35, 'change_notification', 'Can change notification'),
(147, 35, 'delete_notification', 'Can delete notification'),
(148, 35, 'view_notification', 'Can view notification'),
(149, 38, 'add_pullrequest', 'Can add pull request'),
(150, 38, 'change_pullrequest', 'Can change pull request'),
(151, 38, 'delete_pullrequest', 'Can delete pull request'),
(152, 38, 'view_pullrequest', 'Can view pull request'),
(153, 39, 'add_pullrequestcomment', 'Can add pull request comment'),
(154, 39, 'change_pullrequestcomment', 'Can change pull request comment'),
(155, 39, 'delete_pullrequestcomment', 'Can delete pull request comment'),
(156, 39, 'view_pullrequestcomment', 'Can view pull request comment'),
(157, 40, 'add_repository', 'Can add repository'),
(158, 40, 'change_repository', 'Can change repository'),
(159, 40, 'delete_repository', 'Can delete repository'),
(160, 40, 'view_repository', 'Can view repository'),
(161, 41, 'add_revisionrequest', 'Can add revision request'),
(162, 41, 'change_revisionrequest', 'Can change revision request'),
(163, 41, 'delete_revisionrequest', 'Can delete revision request'),
(164, 41, 'view_revisionrequest', 'Can view revision request');

-- auth_user: 3 rows
INSERT INTO `auth_user` (`id`, `password`, `last_login`, `is_superuser`, `username`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`, `first_name`) VALUES
(21, 'pbkdf2_sha256$1500000$jkFf5lcF8BPREBaquYFk3R$8mnbf3cYq6VZslJrLvfAzRKL2qihYEk/fYJiaMFCPxE=', '2026-10-29 08:00:05.796620', 0, 'Cj', 'Pagador', 'sapanzacyrus143@gmail.com', 0, 1, '2026-10-27 09:30:53.195036', 'Cyrus'),
(22, 'pbkdf2_sha256$1500000$rYRrzLch69pvCc0SyTjD0M$1fTaGRyVtKo73HL+c+/Xnl+q1aDmr9L4SfS3D9blSf8=', '2026-10-29 23:49:29.990554', 0, 'CjInstructor1', 'Sapanza', 'sapanzacyrus23143@gmail.com', 1, 1, '2026-10-27 09:31:40.191320', 'Cyrus'),
(23, 'pbkdf2_sha256$1500000$o6ez0IYlMhUdtBXhuTKBdR$iR97mTpzvmdhg4z6J2Hqij9EIHKkUWlx9WVW2/RxAQ4=', '2026-10-29 23:48:43.191981', 0, 'Cj1', 'Pagador', 'sapanzacyr2us143@gmail.com', 0, 1, '2026-10-29 23:48:42.139401', 'Cyrus');

-- classforge_api_tokens: 5 rows
INSERT INTO `classforge_api_tokens` (`id`, `name`, `prefix`, `token_hash`, `scopes`, `created_at`, `expires_at`, `last_used_at`, `revoked_at`, `user_id`) VALUES
(1, 'VS Code extension', 'cf_PjQoC0u', '2f02dcef69b1c78a35ae74c2f89451e2186eb85556750f2103eaa8e751381a33', 'read write', '2026-10-29 07:11:34.506294', '2026-11-28 07:11:34.505936', '2026-10-29 08:02:55.157397', NULL, 21),
(2, 'INTERNET OF THINGS', 'cf_PnAyoT4', '38ec4adbec7ce3c9aaa1904f9d2a8d67865c4bc7a2442e0dec749a2c1052e578', 'read write', '2026-10-29 07:17:20.698434', '2026-11-28 07:17:20.698029', NULL, '2026-10-29 07:17:41.197207', 21),
(3, 'VS Code extension', 'cf_Oh5VUIu', '3e7ce5c7900b55be9c39414da8720c88d414ed368de6fc9bf689f1f1984e205c', 'read write', '2026-10-29 08:03:48.845928', '2026-11-28 08:03:48.845597', '2026-10-29 08:04:52.081949', NULL, 21),
(4, 'VS Code extension', 'cf_Xa9DWnW', '507b1e590e870def9498c3bc852afd43f7f66d03ee7d5d89346a0af3298a3c7d', 'read write', '2026-10-29 23:43:20.757367', '2026-11-28 23:43:20.756785', '2026-10-29 23:44:33.978454', NULL, 21),
(5, 'VS Code extension', 'cf_ZrpcXnY', '77bd24689a8011e60fe58cdf6895942f78aee6e19ea4a8d19152e8a6bfb312cc', 'read write', '2026-10-29 23:55:46.704341', '2026-11-28 23:55:46.704011', '2026-10-29 23:56:23.608465', NULL, 23);

-- classforge_notifications: 6 rows
INSERT INTO `classforge_notifications` (`id`, `kind`, `title`, `body`, `url`, `read_at`, `created_at`, `user_id`, `project_id`, `snapshot_id`) VALUES
(4, 'info', 'New project snapshot from Cj', 'Hello World Test Project · v1', '/projects/snapshots/2/', '2026-10-29 23:58:03.341670', '2026-10-29 23:44:28.437603', 22, 2, 2),
(5, 'assessment', 'Assessment ready for Hello World Test Project', 'Snapshot v1: 100.00/100.00. This is a draft until your instructor reviews it.', '/projects/snapshots/2/', NULL, '2026-10-29 23:44:29.245783', 21, 2, 2),
(6, 'assessment', 'Assessment needs review: Cj', 'Hello World Test Project · snapshot v1', '/projects/assessments/2/review/', '2026-10-29 23:58:03.341670', '2026-10-29 23:44:29.351351', 22, 2, 2),
(7, 'info', 'New project snapshot from Cj1', 'Hello World Test Project · v1', '/projects/snapshots/3/', '2026-10-29 23:58:03.341670', '2026-10-29 23:56:20.076127', 22, 3, 3),
(8, 'assessment', 'Assessment ready for Hello World Test Project', 'Snapshot v1: 100.00/100.00. This is a draft until your instructor reviews it.', '/projects/snapshots/3/', NULL, '2026-10-29 23:56:20.698649', 23, 3, 3),
(9, 'assessment', 'Assessment needs review: Cj1', 'Hello World Test Project · snapshot v1', '/projects/assessments/3/review/', '2026-10-29 23:58:03.341670', '2026-10-29 23:56:20.785658', 22, 3, 3);

-- courses: 1 rows
INSERT INTO `courses` (`id`, `name`, `description`, `code`, `created_at`, `updated_at`, `instructor_id`) VALUES
(1, 'INTERNET OF THINGS', '', 'ITE201', '2026-10-27 09:33:36.879809', '2026-10-27 09:33:36.879830', 22);

-- django_content_type: 41 rows
INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(1, 'admin', 'logentry'),
(2, 'auth', 'group'),
(3, 'auth', 'permission'),
(4, 'auth', 'user'),
(5, 'contenttypes', 'contenttype'),
(6, 'sessions', 'session'),
(7, 'courses', 'courseschedule'),
(8, 'courses', 'quiz'),
(9, 'courses', 'quizquestion'),
(10, 'courses', 'tblcourse'),
(11, 'students', 'tblstudents'),
(12, 'attendance', 'tblattendance'),
(13, 'info', 'info'),
(14, 'courses', 'assignment'),
(15, 'courses', 'course'),
(16, 'courses', 'enrollment'),
(17, 'courses', 'grade'),
(18, 'courses', 'submission'),
(19, 'core', 'activitylog'),
(20, 'users', 'userprofile'),
(21, 'courses', 'courseassistant'),
(22, 'courses', 'feedbackannotation'),
(23, 'courses', 'rubric'),
(24, 'courses', 'rubriccriterion'),
(25, 'courses', 'criterionscore'),
(26, 'ai', 'aievaluation'),
(27, 'ai', 'aiflag'),
(28, 'portfolio', 'portfolio'),
(29, 'portfolio', 'portfolioitem'),
(30, 'courses', 'assignmentseen'),
(31, 'courses', 'rubricversion'),
(32, 'projects', 'apitoken'),
(33, 'projects', 'assessment'),
(34, 'projects', 'criterionassessment'),
(35, 'projects', 'notification'),
(36, 'projects', 'project'),
(37, 'projects', 'projectsnapshot'),
(38, 'projects', 'pullrequest'),
(39, 'projects', 'pullrequestcomment'),
(40, 'projects', 'repository'),
(41, 'projects', 'revisionrequest');

-- django_migrations: 45 rows
INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
(1, 'contenttypes', '0001_initial', '2026-05-12 01:46:53.555369'),
(2, 'auth', '0001_initial', '2026-05-12 01:46:53.574735'),
(3, 'admin', '0001_initial', '2026-05-12 01:46:53.588840'),
(4, 'admin', '0002_logentry_remove_auto_add', '2026-05-12 01:46:53.598790'),
(5, 'admin', '0003_logentry_add_action_flag_choices', '2026-05-12 01:46:53.606702'),
(6, 'contenttypes', '0002_remove_content_type_name', '2026-05-12 01:46:53.619313'),
(7, 'auth', '0002_alter_permission_name_max_length', '2026-05-12 01:46:53.629475'),
(8, 'auth', '0003_alter_user_email_max_length', '2026-05-12 01:46:53.639336'),
(9, 'auth', '0004_alter_user_username_opts', '2026-05-12 01:46:53.647836'),
(10, 'auth', '0005_alter_user_last_login_null', '2026-05-12 01:46:53.657695'),
(11, 'auth', '0006_require_contenttypes_0002', '2026-05-12 01:46:53.663172'),
(12, 'auth', '0007_alter_validators_add_error_messages', '2026-05-12 01:46:53.671436'),
(13, 'auth', '0008_alter_user_username_max_length', '2026-05-12 01:46:53.681141'),
(14, 'auth', '0009_alter_user_last_name_max_length', '2026-05-12 01:46:53.690683'),
(15, 'auth', '0010_alter_group_name_max_length', '2026-05-12 01:46:53.699977'),
(16, 'auth', '0011_update_proxy_permissions', '2026-05-12 01:46:53.708714'),
(17, 'auth', '0012_alter_user_first_name_max_length', '2026-05-12 01:46:53.718043'),
(18, 'sessions', '0001_initial', '2026-05-12 01:46:53.729620'),
(19, 'students', '0001_initial', '2026-09-09 07:24:32.187168'),
(20, 'attendance', '0001_initial', '2026-09-09 07:24:32.200774'),
(21, 'attendance', '0002_dedupe_and_unique', '2026-09-09 07:24:32.214977'),
(23, 'courses', '0002_alter_tblcourse_courseid', '2026-09-09 07:24:32.232123'),
(24, 'courses', '0003_tblcourse_status', '2026-09-09 07:24:32.242718'),
(25, 'courses', '0004_quiz_quizquestion', '2026-09-09 07:24:32.272063'),
(26, 'courses', '0005_quizquestion_question_type_and_more', '2026-09-09 07:24:32.302198'),
(27, 'courses', '0006_courseschedule', '2026-09-09 07:24:32.321870'),
(28, 'courses', '0007_tblcourse_user', '2026-09-09 07:24:32.342963'),
(29, 'courses', '0008_assign_course_ownership', '2026-09-09 07:24:32.361193'),
(30, 'students', '0002_alter_tblstudents_idno', '2026-09-09 07:24:32.371652'),
(31, 'students', '0003_tblstudents_enrollment_type', '2026-09-09 07:24:32.392354'),
(32, 'students', '0004_tblstudents_user', '2026-09-09 07:24:32.415453'),
(33, 'students', '0005_assign_student_ownership', '2026-09-09 07:24:32.435378'),
(34, 'info', '0001_initial', '2026-10-14 04:34:16.916939'),
(35, 'courses', '0001_initial', '2026-10-14 04:38:34.169999'),
(36, 'courses', '0002_assignment_category', '2026-10-14 05:04:38.630518'),
(37, 'info', '0002_info_id_number', '2026-10-14 05:14:33.129525'),
(38, 'courses', '0003_assignment_accepts_github_assignment_accepts_pdf_and_more', '2026-10-24 04:22:13.151756'),
(39, 'ai', '0001_initial', '2026-10-24 04:22:13.613538'),
(40, 'core', '0001_initial', '2026-10-24 04:22:13.849527'),
(41, 'portfolio', '0001_initial', '2026-10-24 04:22:14.231253'),
(42, 'users', '0001_initial', '2026-10-24 04:22:14.506650'),
(43, 'courses', '0004_assignmentseen', '2026-10-27 09:18:18.521105'),
(44, 'courses', '0005_assignment_accepted_formats_and_more', '2026-10-29 06:00:30.915837'),
(45, 'projects', '0001_initial', '2026-10-29 06:00:31.958892'),
(46, 'courses', '0006_remove_assignment_accepts_github_and_more', '2026-10-29 07:49:24.134425');

-- django_session: 70 rows
INSERT INTO `django_session` (`session_key`, `session_data`, `expire_date`) VALUES
('6u3gnbwys56lixiufpr9sqmb3jtxsbxl', '.eJxVjEEOgyAQAP-yZ0PAlkU99t43kAWWSkVsFE9N_96YePE6M5kvREqZg6Vaef7UDQbZQF78ZGuaGYay59yApb2Odt94tSnAAAouzJGfuBwivKm8FuGXUtfkxJGI027iuQTOj7O9DEbaRhiAsWU0TN1dKhODVlEyed06QvSM2BnWRNjHgL5XqLQMXvXRmRCp1zeE3x_HOkWg:1x4Ced:3C6-XryaEPjcsAHJTaGCK71gFSHJdppbXVhUrhl0v3I', '2026-09-23 07:23:35.825786'),
('qebwgqxbkvyz8lhgo5czrdo0s27iywbs', '.eJxVjEEOwiAQAP-yZ0MWlm5pj959AwGW2qqBpLQn499Nkx70OjOZN_iwb7PfW179IjCChcsviyE9czmEPEK5V5Vq2dYlqiNRp23qViW_rmf7N5hDm2GEEM1EqUuTEY2ClofYsSBnMn1PpFHT4GxAFx2LYCcoPFHPbLUzjjJ8vtNjNts:1xGqlO:a4JmWeL3oLYiR7--fIHc7-22Tgjv3ipUIuWl2y2fnGU', '2026-10-28 04:38:50.666413'),
('odsjgfa3dcx8k33fykp7ibhk0gyzjk3k', '.eJxVjLsOgzAMAP_FcxXlQTAwdu83RHYcF9oKJAJT1X-vkBja9e50b0i0b2Paa1nTJDBAhMsvY8rPMh9CHjTfF5OXeVsnNkdiTlvNbZHyup7t32CkOsIA2nZZSW1vIyqrOo8qVFwOnl3mgIFiz14teewbm7uoHbI0Ii1aHwQ-Xw4SOJM:1xGqlO:35oqZKqnej4R6BH4IkXrlMIyGmuXoMpH84b3dHFUZGg', '2026-10-28 04:38:50.780219'),
('gl2hcakfx1s1dsdj2zbj8tprtw6co4jh', '.eJxVjEEOwiAQAP-yZ0MWlm5pj959AwGW2qqBpLQn499Nkx70OjOZN_iwb7PfW179IjCChcsviyE9czmEPEK5V5Vq2dYlqiNRp23qViW_rmf7N5hDm2GEEM1EqUuTEY2ClofYsSBnMn1PpFHT4GxAFx2LYCcoPFHPbLUzjjJ8vtNjNts:1xGqla:G6rvdzUiGttP9_ppYSS_qVSIx8J4rSv145bwCyFofXw', '2026-10-28 04:39:02.743790'),
('i9ccznlnobs7r1yjqpt883x04b8n6t5t', '.eJxVjLsOgzAMAP_FcxXlQTAwdu83RHYcF9oKJAJT1X-vkBja9e50b0i0b2Paa1nTJDBAhMsvY8rPMh9CHjTfF5OXeVsnNkdiTlvNbZHyup7t32CkOsIA2nZZSW1vIyqrOo8qVFwOnl3mgIFiz14teewbm7uoHbI0Ii1aHwQ-Xw4SOJM:1xGqla:kgIwUPJ56u2JIuJJRTa6u2_p_PybHl4RBVjvJLM0DxM', '2026-10-28 04:39:02.847393'),
('gns7tewf0dsub62vqwmah8j9rnuhebdc', '.eJxVjEEOwiAQAP-yZ0MWlm5pj959AwGW2qqBpLQn499Nkx70OjOZN_iwb7PfW179IjCChcsviyE9czmEPEK5V5Vq2dYlqiNRp23qViW_rmf7N5hDm2GEEM1EqUuTEY2ClofYsSBnMn1PpFHT4GxAFx2LYCcoPFHPbLUzjjJ8vtNjNts:1xGqll:8jg83dqn9XoFS9eREGUcpoDSRVK1gKfr6r9Q3AgSXOg', '2026-10-28 04:39:13.151310'),
('pp250mcsd2er39gsheyy4djtfu54o3cb', '.eJxVjLsOgzAMAP_FcxXlQTAwdu83RHYcF9oKJAJT1X-vkBja9e50b0i0b2Paa1nTJDBAhMsvY8rPMh9CHjTfF5OXeVsnNkdiTlvNbZHyup7t32CkOsIA2nZZSW1vIyqrOo8qVFwOnl3mgIFiz14teewbm7uoHbI0Ii1aHwQ-Xw4SOJM:1xGqll:bGWSrPI8dBsmFhVxos6uGVOTEtuGwsR4rEAxF4mCBzc', '2026-10-28 04:39:13.257812'),
('2psd3m85ebgp88lbaitjoaijbadpazze', '.eJxVjLsOgzAMAP_FcxXlQTAwdu83RHYcF9oKJAJT1X-vkBja9e50b0i0b2Paa1nTJDBAhMsvY8rPMh9CHjTfF5OXeVsnNkdiTlvNbZHyup7t32CkOsIA2nZZSW1vIyqrOo8qVFwOnl3mgIFiz14teewbm7uoHbI0Ii1aHwQ-Xw4SOJM:1xGqlu:x2z7DDTODbu3toW3DrhhrxQVi-iEl8Y3opq166WqzvE', '2026-10-28 04:39:22.223733'),
('108tnr1q4aunieu3ih67skd7lwu4yeks', '.eJxVjEEOwiAQAP-yZ0MWlm5pj959AwGW2qqBpLQn499Nkx70OjOZN_iwb7PfW179IjCChcsviyE9czmEPEK5V5Vq2dYlqiNRp23qViW_rmf7N5hDm2GEEM1EqUuTEY2ClofYsSBnMn1PpFHT4GxAFx2LYCcoPFHPbLUzjjJ8vtNjNts:1xGqm5:Lc5GFC6d4x5ihaYkgI7X6CNmcufciNuwLZ9Gr8v4sdA', '2026-10-28 04:39:33.945377'),
('mzyddtu48g4pzsnezsjaimh5z45rsbm3', '.eJxVjLsOgzAMAP_FcxXlQTAwdu83RHYcF9oKJAJT1X-vkBja9e50b0i0b2Paa1nTJDBAhMsvY8rPMh9CHjTfF5OXeVsnNkdiTlvNbZHyup7t32CkOsIA2nZZSW1vIyqrOo8qVFwOnl3mgIFiz14teewbm7uoHbI0Ii1aHwQ-Xw4SOJM:1xGqm6:zY3quiruzjNWtj0NEn_clVqzIjLB0TuaYgP5aRgdoi8', '2026-10-28 04:39:34.051769'),
('wokjw02v97ks99u2rx95oixndok9ox4e', '.eJxVjEEOwiAQAP-yZ0MWlm5pj959AwGW2qqBpLQn499Nkx70OjOZN_iwb7PfW179IjCChcsviyE9czmEPEK5V5Vq2dYlqiNRp23qViW_rmf7N5hDm2GEEM1EqUuTEY2ClofYsSBnMn1PpFHT4GxAFx2LYCcoPFHPbLUzjjJ8vtNjNts:1xGqmH:kmLt6Z5YBAtB4DtOSxSgE7KikaEwPnoJadvLYJoA5oQ', '2026-10-28 04:39:45.458160'),
('jypc68ftbeku9e5s4xxe2j7l4ccfg3vc', '.eJxVjEEOwiAQAP-yZ0MWlm5pj959AwGW2qqBpLQn499Nkx70OjOZN_iwb7PfW179IjCChcsviyE9czmEPEK5V5Vq2dYlqiNRp23qViW_rmf7N5hDm2GEEM1EqUuTEY2ClofYsSBnMn1PpFHT4GxAFx2LYCcoPFHPbLUzjjJ8vtNjNts:1xGqnE:R6XPj5-IbAIZKTJiHaEHMBghZ8jICm-5vg3ZhY184kw', '2026-10-28 04:40:44.643638'),
('ym8szs6wjhkhra8nbzzl8z75wk35o7c9', '.eJxVjLsOgzAMAP_FcxXlQTAwdu83RHYcF9oKJAJT1X-vkBja9e50b0i0b2Paa1nTJDBAhMsvY8rPMh9CHjTfF5OXeVsnNkdiTlvNbZHyup7t32CkOsIA2nZZSW1vIyqrOo8qVFwOnl3mgIFiz14teewbm7uoHbI0Ii1aHwQ-Xw4SOJM:1xGqnE:Xace6QWd3y8ZO4ns_65GcX8JBw1EjKGF-O1bcevd-iQ', '2026-10-28 04:40:44.771761'),
('jqvsoeetmx3uprv8olqpf2ab7vcno9yj', 'eyJmYWlsZWRfYXR0ZW1wdHMiOjF9:1xGqvC:DRYsBln6MObwKp_Cv_NwUdnz03SNxGj6F1viCPO9pUs', '2026-10-28 04:48:58.568373'),
('xmzzgop0mnscdhli6f6874222t0l0mbs', '.eJxVjDEOgzAMAP_iuYpCcMBh7N43IMdxCm0VJAJT1b9XSAztene6N4y8b9O4V13HOcEABJdfFlmeWg6RHlzui5GlbOsczZGY01ZzW5K-rmf7N5i4TjAAOucVURz7VpAa8X2wsRMbcm9zaqO2JCGRbWLMGZUCM1vCFKxSpwifL9xiOA8:1xGqyv:KhIAtTIORa_fHi38a3O36IyUkKpKAki4VfUds_-1Hj4', '2026-10-28 04:52:49.179982'),
('s92nwhg3au90vd5cvxpobcgjokupn1wz', '.eJxVjEsOwiAUAO_y1oYAD3jYpfuegfCVqoGktCvj3U2TLnQ7M5k3OL9v1e0jr25JMIGByy8LPj5zO0R6-HbvLPa2rUtgR8JOO9jcU37dzvZvUP2oMEEIRUlORnlVctCJl2gsL0JTxGLRkCfU3KLMWARpY2TEq1KByGK2XMDnC97gNvI:1xGqyv:KrICUDr4LfoQ59y31YV67m_I0xriEP07Ggi2r0rXpSY', '2026-10-28 04:52:49.361583'),
('zet2cejmi90j4562t6oq03lkj6b09kr6', '.eJxVjMsOwiAQAP9lz4bwKBR69O43kIXdStVAUtqT8d9Nkx70OjOZN0TctxL3zmtcCCZQEi6_MGF-cj0MPbDem8itbuuSxJGI03Zxa8Sv69n-DQr2AhMkzMEyZiuDUskZ79SsXQqWLWarFY1m1JTkQJ6lyXaYSaJhT8Ghco7g8wULwDgp:1xGr38:abVps4yMLAGB3sLvDjhtNa7qKshg4976uIImK4flYVE', '2026-10-28 04:57:10.139123'),
('ftyc753866wlg2skfb3e1aigx6lmvrsd', '.eJxVjEEOwiAQAP-yZ0NKFxbao3ffQBZYpGrapLQn499Nkx70OjOZNwTetxr2JmuYMoygNVx-YeT0lPkw-cHzfVFpmbd1iupI1Gmbui1ZXtez_RtUbhVGEOtMjz4ximYiQvaddaiZOHLphe1QLHoaXKLEGr1Gsp2R5E0pUgb4fAH2Bzff:1xGr4p:fkQjHH5gP_G6etOHVJqRXol0ZDKjhr30MUKH7t_irhY', '2026-10-28 04:58:55.811345'),
('xwivk0c5n7v7yh33p0du8ed273f0j6nz', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xGrG7:cGtXTvab1rPq69lPyYb39CqEHWyYcYWc5qXq4BodOWo', '2026-10-28 05:10:35.821325'),
('ijyf8ejw4l2evvuz6rd2rme8q3icw67t', '.eJxVjMsOwiAQAP-FsyEtz9aj934DWdhdqRpISnsy_rsh6UGvM5N5iwDHnsPRaAsriqvw4vLLIqQnlS7wAeVeZapl39YoeyJP2-RSkV63s_0bZGi5b5VDYorK8mTZm2HUieyEKerZWxthcIwGZ1DeGULWyEA6gmOyaSQUny8GqDll:1xGrG7:JETq0QUhHuA7M7hz6uihkGHh1FsmyCs6fpawsm19j34', '2026-10-28 05:10:35.960160'),
('ej9fcw58oy7di9eloaawpnfuntu7yc4q', 'e30:1xKTTV:4mUrLWTZxMLhNYj2pJTh7zd2_LpMMZtaj83YZSmzJYE', '2026-11-07 04:35:21.204984'),
('b0qcdevk5qurszz0ji8tt3senbu02yfd', '.eJxVjLsOwjAMAP_FM4pKnbiPkZ1viBzb0AJKpKadEP-OKnWA9e50b4i8rVPcqi1xVhiB4PTLEsvT8i70wflenJS8LnNye-IOW921qL0uR_s3mLhOMMLQnYXVkCgYalAyY76JqGA7-BBCE6xHQ2FSTJ548H3L6H1H0hAZfL4GyDg-:1xKTaj:VIiaxrhKUOlhtZv3haQEbcDPbTL_hvrYJ4DWK7tQHP4', '2026-11-07 04:42:49.345225'),
('ftkd7aoqgweig5rgwsbd3jgtqpdsgocs', '.eJxVjEEOwiAQAP-yZ0OWVhB69O4byC4LUjWQlPZk_Ltp0oNeZybzhkDbWsLW0xJmgQk8nH4ZU3ymugt5UL03FVtdl5nVnqjDdnVrkl7Xo_0bFOoFJsgjZy-kTYw8Ziafs8GzsS7paK1GGoRQnHhiujBSTk6PUQZ0Ysgjw-cLIbE5QQ:1xKTap:_xsmeVtfwtexLHuN202_Ef-7X5GJJ7zcDLaZ9LsTc-g', '2026-11-07 04:42:55.177470'),
('fqp09822ltw96si0o89i0wfs7viyf2qn', '.eJxVjMsOwiAQAP9lz4YUWF49evcbyC5QqRqalPZk_HfTpAe9zkzmDZH2rca9lzXOGUZwcPllTOlZ2iHyg9p9EWlp2zqzOBJx2i5uSy6v69n-DSr1CiN4hVoiF8QwFK91oow6sTEU1ITao7cyYWFGks5Zk3kajJLJawwWScHnC8noNxE:1xKTau:iztQbs0pHvaO1lNgNXwt9x_8fnZ__bynQQlkvpmNSsc', '2026-11-07 04:43:00.508896'),
('wzjwsd6iraobfq2k9ta1fez3owihv4xt', '.eJxVjDEOgzAMAP_iuYpqAk7C2J03oMR2Cm0VJAJT1b9XSAztene6N4xx36Zxr7qOs0APBJdfliI_tRxCHrHcF8NL2dY5mSMxp61mWERft7P9G0yxTtADNtQmJyFnh9jxNbHNHTEjeRSkQCrOUySrjEEEW6-c2sY22km2TPD5AuKzOA8:1xKTba:sRujbZj6qMJbx5u-RO1SSAmo0W35Vy3v97ozo3YPoa4', '2026-11-07 04:43:42.038276'),
('irecigrdcje7g7ydcj9ms7wtqpwz6xnk', '.eJxVjDEOgzAMAP_iuYqcBFLC2J03IDs2hbZKJAJT1b9XSAztene6N4y0b_O4V13HRaCHCJdfxpSemg8hD8r3YlLJ27qwORJz2mqGIvq6ne3fYKY6Qw9ep1Ywip2oFTu12jUchD2jT1dplBymaEOK1nEI4pAb1BgsOU9IXYLPFwP4OEs:1xKTbh:zeVWVoWTR9KLx7roK5s0FNoZnOjbl-rAe1IecVHIU_8', '2026-11-07 04:43:49.132065'),
('y58o1hepfkscea6fx8phwggs4t17dksv', '.eJxVjDEOgzAMAP_iuYqKg-LA2L1vQI5tGtoqSAQm1L9XSAztene6HQbe1jxs1ZZhUuiB4PLLEsvLyiH0yeUxO5nLukzJHYk7bXX3We19O9u_QeaaoQeflHhECUhIHQYlxsBCbZTGRkalNBJSujbRe-xCayYaNYr3bIwIny_uRTg3:1xKTbm:nQNn7AAWU_7y4t-lLvcWuWNFmGwEGoZcjoGD3VqeE8Y', '2026-11-07 04:43:54.821146'),
('rlol7dkad21b9fvod2a5pq1cfuj6nz22', '.eJxVjEsOwiAUAO_y1oYAD3jYpfuegfCVqoGktCvj3U2TLnQ7M5k3OL9v1e0jr25JMIGByy8LPj5zO0R6-HbvLPa2rUtgR8JOO9jcU37dzvZvUP2oMEEIRUlORnlVctCJl2gsL0JTxGLRkCfU3KLMWARpY2TEq1KByGK2XMDnC97gNvI:1xKTej:I0KJ8eoFmDy8Jvqoqt5lfZJ7qe-xoaEYdEYe6dKamGE', '2026-11-07 04:46:57.252074'),
('qn1432ithk0d1fipnxw36k7g84u9ctcd', '.eJxVjEsOwiAUAO_y1oYAD3jYpfuegfCVqoGktCvj3U2TLnQ7M5k3OL9v1e0jr25JMIGByy8LPj5zO0R6-HbvLPa2rUtgR8JOO9jcU37dzvZvUP2oMEEIRUlORnlVctCJl2gsL0JTxGLRkCfU3KLMWARpY2TEq1KByGK2XMDnC97gNvI:1xKTfA:g2M0JE-hbWCjMXrr2lmS250awK6ZuCjL8Gj40rEcbKI', '2026-11-07 04:47:24.046776'),
('jhaw4hbohptdwgzwa8q50en7uiir4s4h', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKTfB:0ONzcZdmphZnqXXA4sPKVvXjcYa3XBd8bUdtubRiJkY', '2026-11-07 04:47:25.379238'),
('h7metyxpupxulvaa42bx3f3hoanbmeta', '.eJxVjMsOwiAQAP-FsyEtz9aj934DWdhdqRpISnsy_rsh6UGvM5N5iwDHnsPRaAsriqvw4vLLIqQnlS7wAeVeZapl39YoeyJP2-RSkV63s_0bZGi5b5VDYorK8mTZm2HUieyEKerZWxthcIwGZ1DeGULWyEA6gmOyaSQUny8GqDll:1xKTfC:SIQFCsOfw0xtRfos58g4m4KGBtnkkmWaATHjsIF587g', '2026-11-07 04:47:26.103085'),
('gge9aud9k2so1x3gizfq002otyu4wqz1', '.eJxVjMsOwiAQAP9lz4bwlKVH7_0Gsl2oVA0kpT0Z_9006UGvM5N5Q6R9K3HveY1LggGUhcsvnIifuR4mPajem-BWt3WZxJGI03YxtpRft7P9GxTqBQbQZIiz9cobZMdXqZ02nI0Ps9fGIjvlUGLQ1ilUyCyt98Qkyeg5YIDPF90vNrs:1xKThi:7mNsRie10LCR5iZMeIvetybamCul-2C0DzfDGNfAU2M', '2026-11-07 04:50:02.907941'),
('emxmqv9z69kels2yr73qp5gewmib2s46', '.eJxVjEsOwiAUAO_y1oYAD3jYpfuegfCVqoGktCvj3U2TLnQ7M5k3OL9v1e0jr25JMIGByy8LPj5zO0R6-HbvLPa2rUtgR8JOO9jcU37dzvZvUP2oMEEIRUlORnlVctCJl2gsL0JTxGLRkCfU3KLMWARpY2TEq1KByGK2XMDnC97gNvI:1xKTs0:fBbkdsuQd95gxRN-uh2lFvFhsziEEXYi98iCvyFcZaI', '2026-11-07 05:00:40.896620'),
('odf5kt8yw3kgdg8qqds8av863mxjaz0w', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKTs1:_GgYjjQstNREyo1QHLGUR5MlUkktlCz5RI0X3wbnwfA', '2026-11-07 05:00:41.709157'),
('tgm2cy3guvcujdn61eevq5xv1w4p5j4z', '.eJxVjMsOwiAQAP-FsyEtz9aj934DWdhdqRpISnsy_rsh6UGvM5N5iwDHnsPRaAsriqvw4vLLIqQnlS7wAeVeZapl39YoeyJP2-RSkV63s_0bZGi5b5VDYorK8mTZm2HUieyEKerZWxthcIwGZ1DeGULWyEA6gmOyaSQUny8GqDll:1xKTs2:8s2Mymv82T-0Blp37ph1LZcmQvl_IohMnvQoWL5_-f4', '2026-11-07 05:00:42.209411'),
('nln5xps09tjsxz1t1e0rc207wwwpzjxl', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKTti:8oN5WXhCkI5GR4-ku67oz5UkG7Ho1hn7IAJXT4zUgd4', '2026-11-07 05:02:26.483588'),
('s9gcb0qr4dqgly380ruv9g3okidcc3ry', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKTuA:ps4-WFVy1sclHKgSbOotsOkTYaGEwQB2mwUwo593Yqg', '2026-11-07 05:02:54.272661'),
('ay62kw44l03heiucq0etylo9fs7691fe', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKTuY:4tcsXKqrpkWv9bEEYDVguZzZec7SXMBnjzxaXX3ZF4Y', '2026-11-07 05:03:18.472032'),
('hgu6qb1p8zuerwcj2a0iv3r0wtsxdk35', '.eJxVjEsOwiAUAO_y1oYAD3jYpfuegfCVqoGktCvj3U2TLnQ7M5k3OL9v1e0jr25JMIGByy8LPj5zO0R6-HbvLPa2rUtgR8JOO9jcU37dzvZvUP2oMEEIRUlORnlVctCJl2gsL0JTxGLRkCfU3KLMWARpY2TEq1KByGK2XMDnC97gNvI:1xKTuZ:A09-cTBT4sDvcm5cVOyB6ojyxU_wMMqt8QXrDTHyJsg', '2026-11-07 05:03:19.233386'),
('plnzyu7qnr2za6gm2v8hrwjozqw5lthu', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKTwU:X41K7bJLiqvCNV-q3jiJV945c2VTBDcIgqZiCyf-oI8', '2026-11-07 05:05:18.484441'),
('hqj82q7cocsu2o4gzv4k2uxerllw3yo2', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKTxj:ssuPXGZUzOaTgSu0WVZM5m57CTqaIw63GcGWCycL4JY', '2026-11-07 05:06:35.144210'),
('t1a5p40uezrxpnj0q8c2phvxl8qjfecr', '.eJxVjMsOwiAQAP-FsyEtz9aj934DWdhdqRpISnsy_rsh6UGvM5N5iwDHnsPRaAsriqvw4vLLIqQnlS7wAeVeZapl39YoeyJP2-RSkV63s_0bZGi5b5VDYorK8mTZm2HUieyEKerZWxthcIwGZ1DeGULWyEA6gmOyaSQUny8GqDll:1xKTxj:-NjD0M3iE-Ge-LykM9mlFeXlnCNgFUSN7RntfSjUvu0', '2026-11-07 05:06:35.844716'),
('3fiubpg2e4wc99w49unyq3x4z5pj8d7o', '.eJxVjEsOwiAUAO_y1oYAD3jYpfuegfCVqoGktCvj3U2TLnQ7M5k3OL9v1e0jr25JMIGByy8LPj5zO0R6-HbvLPa2rUtgR8JOO9jcU37dzvZvUP2oMEEIRUlORnlVctCJl2gsL0JTxGLRkCfU3KLMWARpY2TEq1KByGK2XMDnC97gNvI:1xKTxk:wzqJ4EEFET2jwAGyqtCoJKqsHIqtneDoLaNyF9H42So', '2026-11-07 05:06:36.545414'),
('x1f96zd67x4ggohie1hyvs8iy0ezu0x6', '.eJxVjEEOwiAQAP-yZ0MKFBZ69O4byMJSqRpISnsy_t006UGvM5N5Q6B9K2HveQ0LwwTSwuUXRkrPXA_DD6r3JlKr27pEcSTitF3cGufX9Wz_BoV6gQmsykNURmmaR_ReoU-kNQ1kUY7Ilr1ijdY5F9FZKclIHExUmGfnE3v4fAHe9zcB:1xKU1C:w4DK8IuPoAvt6txjhqWurB9qtqsScSuujwjO2Y4wQck', '2026-11-07 05:10:10.106212'),
('tw0tjue01rtmx9pz9z9hcntset64dk1i', '.eJxVjMsOwiAQAP-FsyEtz9aj934DWdhdqRpISnsy_rsh6UGvM5N5iwDHnsPRaAsriqvw4vLLIqQnlS7wAeVeZapl39YoeyJP2-RSkV63s_0bZGi5b5VDYorK8mTZm2HUieyEKerZWxthcIwGZ1DeGULWyEA6gmOyaSQUny8GqDll:1xKU1C:ZmkcYyn1DC6kPcr-Vo2aIG02et6zWmW91GJksKwxn_s', '2026-11-07 05:10:10.891223'),
('1g1gxn9xw6s3ajonf90b6xfhyfdydjaf', '.eJxVjMsKwjAQAP9lzxKakM0mPXr3G8o-GluVFvo4if8uhR70OjPMGzret6Hb137pRoMWPMHlFwrrs58OYw-e7rPTedqWUdyRuNOu7jZb_7qe7d9g4HWAFigGFKJqFIVVVYibJoZScq5kFSMWb15S0oCaCyZEDo1pkVKTRITPFwoaN_M:1xKU1H:yPHeG2_6OrnlEw5pEdlr0fJvByeH23Rz7cafmIMbTNI', '2026-11-07 05:10:15.637219'),
('lc4b0lr12zetyugijrvvsfm66appsfzz', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKU5u:4jYV1LGlg6cNp03vgiNv8NHFFpSMKCewuD-VM-gEDPA', '2026-11-07 05:15:02.315534'),
('5nwojqthb4aeutjlf9lxx2rm2qe3paed', '.eJxVjEEOwiAQAP-yZ0Ogy0Lbo3ffQIBdpGrapLQn499Nkx70OjOZN4S4bzXsTdYwMYxgerj8whTzU-bD8CPO90XlZd7WKakjUadt6rawvK5n-zeosVUYISUrWjJpdEZwMN0gPiOy11KIvSAV7witdJqQU2IfKYvrPWriYiN8vgzKODk:1xKUA5:5v0a5RhnXaC-GamaQ1aJCBMWfI2vrJwmnidAen90kIs', '2026-11-07 05:19:21.483234'),
('mgdwpab0w4o4hojf7wrimsdhuu59lzu5', '.eJxVjMsOwiAQRf-FtSE8WnBcuvcbyAwMUjWQlHZl_HdD0oVu7znnvkXAfSth77yGJYmL0CBOvyNhfHIdJD2w3puMrW7rQnIo8qBd3lri1_Vw_w4K9jJqSN55a8nYs5mMnbLTpOdEWiOYDKC8IuUoMntAyBbBxtk7yhEZmMXnC_FuOEc:1xKUCK:3IQ80zXmZWlfh77vYgWjHY6zVdUIab5hKSpcmxJQYuk', '2026-11-07 05:21:40.036919'),
('y1l85gv5mmgmneezqwi5c6mjv5dtma0c', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKfne:nmceWAbktjYPckG6LiipPRfh4v4DZ8MEFROM2NeeoDM', '2026-11-07 17:44:58.577401'),
('tc80qak76om2bx9cd99w1iksfwlbx014', '.eJxVjMsOwiAQAP-FsyEtz9aj934DWdhdqRpISnsy_rsh6UGvM5N5iwDHnsPRaAsriqvw4vLLIqQnlS7wAeVeZapl39YoeyJP2-RSkV63s_0bZGi5b5VDYorK8mTZm2HUieyEKerZWxthcIwGZ1DeGULWyEA6gmOyaSQUny8GqDll:1xKfnq:VVUQQ3mMXJvKV6bdCKr1Iwl7Ut4rJLixGjzTRLOhGlE', '2026-11-07 17:45:10.672228'),
('vax6oh62kfrihes2wg3q3m63yccrlr7h', '.eJxVjMsOwiAQAP-FsyEtz9aj934DWdhdqRpISnsy_rsh6UGvM5N5iwDHnsPRaAsriqvw4vLLIqQnlS7wAeVeZapl39YoeyJP2-RSkV63s_0bZGi5b5VDYorK8mTZm2HUieyEKerZWxthcIwGZ1DeGULWyEA6gmOyaSQUny8GqDll:1xKfo5:D1MkCfpmAadnzwr7akczfrI-1uQacbVEMgtTwxqm0Tc', '2026-11-07 17:45:25.992117'),
('a1yfin8hjrz02cmplazf7i5g25c4tjee', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKfy4:5-DWs4hMO-piKBYhCkvVcsIcUw7YY-DN5uq3jWSk76g', '2026-11-07 17:55:44.834701'),
('k2fhe51v1fd1xnvv7l6t4xhm65mowydl', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKfyI:8XQeXI62ojtK5hAEfdyr11mWt5mVc8_Owhvt6d51p2c', '2026-11-07 17:55:58.796186'),
('fummj863uprx191rqud32r7p0goxc7jv', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKfyX:ry-3XLRAPo7ISacBn2C6qalvBI_h_ywd2JX3ly4qxww', '2026-11-07 17:56:13.528776'),
('pyj6pnhbtyd9su13dnlhiejjkvxz412p', '.eJxVjMsOgjAQAP9lz6aBvigcvfsNzW53sahpEwon478bEg56nZnMGyLuW457kzUuDBOMcPllhOkp5RD8wHKvKtWyrQupI1GnbepWWV7Xs_0bZGwZJtAdht46NMZ7skJJizEmyeCD7oPvCOdktSFmm2ZB0SN7zTI4IectMny-5Qo4iQ:1xKg0c:951qHff9GGQE0QhAY_DUlbE_xXwQO8e_QCZdrFfZSJE', '2026-11-07 17:58:22.246084'),
('eu91ogvbuxv3h7l22egdmuojyn9nm3ty', '.eJxVjEsOgjAUAO_y1qYpUugrS_ecgfT9BDWQUFgZ725IWOh2ZjJvGPK-jcNedB0mgQ6uFVx-IWV-6nwYeeT5vjhe5m2dyB2JO21x_SL6up3t32DMZYQOqBXzxNYyBUUfUZFRK2_mtQ1Ja_UmibkxChiFcoO1JYlegkQMCT5fQow5SA:1xLslC:GOZXeA_jLb20avOMp5AWhdGv_UFCQq0T1K_V0P2f5SI', '2026-11-11 01:47:26.774945'),
('bwtti4rauudz6i2fbnre7alcgtvb5me2', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMJI0:xHB86NU4_G2lzHktIXMcrc1vLfqrzotbMJmWX23Ra_I', '2026-11-12 06:07:04.320892'),
('k1kxgrb45jiwsv3l8bnzcbg052nzi3b0', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMJIM:sv9CSD_Y3Jkmp4lIGFU24p4AaimlrEol31uQVNfKzZs', '2026-11-12 06:07:26.697204'),
('ifgpguu34ueveba8ekr24xh8bvurelms', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMJIX:voDUa9O4rYbThdStsw7OJUmX1o3o0GqI3NpTTypCgQs', '2026-11-12 06:07:37.669486'),
('blw0uzh3sym7xolllb4qhzg83gmu40ic', '.eJxVjEsOgjAUAO_y1qYpUugrS_ecgfT9BDWQUFgZ725IWOh2ZjJvGPK-jcNedB0mgQ6uFVx-IWV-6nwYeeT5vjhe5m2dyB2JO21x_SL6up3t32DMZYQOqBXzxNYyBUUfUZFRK2_mtQ1Ja_UmibkxChiFcoO1JYlegkQMCT5fQow5SA:1xMKQX:1uhcpghFJJuPfKokU7qK9v9FozrtHzeDyCji6m7hi7M', '2026-11-12 07:19:57.815031'),
('lip42v2k6mxeknm7tli5uwnkep9ubhb1', '.eJxVjEsOgjAUAO_y1qYpUugrS_ecgfT9BDWQUFgZ725IWOh2ZjJvGPK-jcNedB0mgQ6uFVx-IWV-6nwYeeT5vjhe5m2dyB2JO21x_SL6up3t32DMZYQOqBXzxNYyBUUfUZFRK2_mtQ1Ja_UmibkxChiFcoO1JYlegkQMCT5fQow5SA:1xMKQo:va282GiV8_6JYy2H4FAf2QF-GanYpUXzjj-8SpWAJYg', '2026-11-12 07:20:14.729877'),
('j9e23qnqbcvbw7vdm2t370gv6rojxxve', '.eJxVjEsOgjAUAO_y1qYpUugrS_ecgfT9BDWQUFgZ725IWOh2ZjJvGPK-jcNedB0mgQ6uFVx-IWV-6nwYeeT5vjhe5m2dyB2JO21x_SL6up3t32DMZYQOqBXzxNYyBUUfUZFRK2_mtQ1Ja_UmibkxChiFcoO1JYlegkQMCT5fQow5SA:1xMKSM:OXYDivvQPujgv0N8OuzeyZt3M-0PdO6-5iQtathdgQA', '2026-11-12 07:21:50.804062'),
('veosyfyr9cb6v88reepo9fm6cya8bjcq', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMKWC:_jNwHJyPNZEbEzRjXyLKhboQ4z2zdzm8nT4A-THuJOw', '2026-11-12 07:25:48.562770'),
('ncwdltbojekq9aux60qtsmanh5qz1umz', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMKZ1:VngwS2kvf8g69JO30gUe_-kTN76A8iJQ2vVZW5yRggc', '2026-11-12 07:28:43.356644'),
('63l0mp9kz3t47zi385m7wsqafwy2laob', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMKZI:MeaUnNd7H9iUH1spgTVfgmSK6wzB1P79mWyqqdRNZc8', '2026-11-12 07:29:00.207430'),
('b1n8s5e5piyoo2eepjohuktr4g7whdt9', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMKZk:UHvBcGXHCc0BhCIWrVpqkI2NPbT8Ap1iau0hEptALgo', '2026-11-12 07:29:28.871603'),
('309b2ijj2msikeu77n2i4zedeysuoumg', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMKdC:wVtoIjzq7OnmiZ_h3eMRNPouPC5vcDpL4BzrvFzH02M', '2026-11-12 07:33:02.734292'),
('u8fw9aoe20dfb021qsq5ggj69wpe9rca', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMKxO:JHVQNRgo3yKGdA25VuJq7bTB9OH29vtS2FnsCVAFUI0', '2026-11-12 07:53:54.207614'),
('7mtdikeqs4zc92i5jjrwihgi4dzienqz', '.eJxVjM0OgjAQBt9lz6aBtrJZjt59huYr2xXUQMLPifjuhoSDXmcms1PCtvZpW8qcBqWWvKfLL8zoXmU8jD4xPibXTeM6D9kdiTvt4u6TlvftbP8GPZaeWhKNyMGDlbuI6AVXhMIoHCuI5ToHEW6MQxMbM0UtHlKZcaVitdHnCxuEOKU:1xMZsA:3bL_VyTk5n379gpDRRZyAdn5x-MC8XBqdkZ8_yBGpJk', '2026-11-12 23:49:30.278487');

-- enrollments: 2 rows
INSERT INTO `enrollments` (`id`, `enrolled_at`, `course_id`, `student_id`) VALUES
(1, '2026-10-27 09:52:52.244342', 1, 21),
(2, '2026-10-29 23:48:51.612161', 1, 23);

-- grades: 2 rows
INSERT INTO `grades` (`id`, `score`, `feedback`, `is_published`, `created_at`, `graded_at`, `instructor_id`, `submission_id`, `published_at`, `published_by_id`) VALUES
(2, 100, 'Automated inspection of submission v1 (zip).\r\nDetected 1 archive file(s); 1 source file(s) and 0 documentation file(s).\r\n\r\nDraft findings:\r\n• [info] No README file was found in the code archive.\r\n\r\nThis is an AI-assisted draft only. Final scores and comments must be reviewed by the instructor.', 1, '2026-10-29 23:46:38.926609', '2026-10-30 00:00:15.474925', 22, 3, '2026-10-29 23:47:01.180595', 22),
(3, 100, 'Automated project assessment draft.\n\nFiles inspected: 2 (1 code, 1 documentation).\nSQL tables: 0; SQLite databases: 0; ERD detected: no; tests: 0.\nChecks: 2 passed, 0 warning(s), 0 failed, 0 not run.\n\nThis is an automated draft. The instructor must review, adjust and publish the final grade.', 1, '2026-10-29 23:57:25.116983', '2026-10-30 00:00:22.957167', 22, 4, '2026-10-30 00:00:22.956932', 22);

-- portfolios: 1 rows
INSERT INTO `portfolios` (`id`, `title`, `bio`, `visibility`, `share_slug`, `created_at`, `updated_at`, `student_id`) VALUES
(5, 'My Portfolio', '', 'private', NULL, '2026-10-28 01:47:37.268067', '2026-10-28 01:47:37.268106', 21);

-- project_assessments: 2 rows
INSERT INTO `project_assessments` (`id`, `status`, `mode`, `engine`, `model_name`, `overall_score`, `max_score`, `summary`, `feedback`, `validation`, `checks`, `structure`, `artifacts`, `evidence`, `raw_response`, `error`, `attempts`, `requires_review`, `review_status`, `instructor_score`, `instructor_feedback`, `reviewed_at`, `applied_at`, `created_at`, `started_at`, `completed_at`, `applied_grade_id`, `requested_by_id`, `reviewer_id`, `rubric_version_id`, `snapshot_id`) VALUES
(2, 'completed', 'automatic', 'local', 'classforge-deterministic-inspector', 100, 100, '2 checks: 2 passed, 0 warnings, 0 failed, 0 not run.', 'Automated project assessment draft.\n\nFiles inspected: 1 (1 code, 0 documentation).\nSQL tables: 0; SQLite databases: 0; ERD detected: no; tests: 0.\nChecks: 2 passed, 0 warning(s), 0 failed, 0 not run.\n\nThis is an automated draft. The instructor must review, adjust and publish the final grade.', '{"checks": [{"key": "secrets", "label": "No secrets in the snapshot", "status": "pass", "message": "No credential patterns were detected.", "evidence": ""}, {"key": "suspicious_code", "label": "Source-code risk review", "status": "pass", "message": "No risky source patterns were detected.", "evidence": ""}], "counts": {"pass": 2, "warn": 0, "fail": 0, "skipped": 0}}', '[{"key": "secrets", "label": "No secrets in the snapshot", "status": "pass", "message": "No credential patterns were detected.", "evidence": ""}, {"key": "suspicious_code", "label": "Source-code risk review", "status": "pass", "message": "No risky source patterns were detected.", "evidence": ""}]', '{"directories": [], "extensions": {".php": 1}, "entry_points": [], "top_level": ["helloworld.php"], "code_files": 1, "documentation_files": 0}', '{"readme": null, "docs": [], "sql": {"files": [], "table_count": 0, "has_primary_key": false, "has_foreign_key": false, "syntax_issues": []}, "databases": [], "erd": {"drawio": [], "mermaid": [], "images": [], "has_erd": false}, "tests": [], "project_files": [], "suspicious": [], "secrets": [], "structure": {"directories": [], "extensions": {".php": 1}, "entry_points": [], "top_level": ["helloworld.php"], "code_files": 1, "documentation_files": 0}}', '[]', '', '', 1, 1, 'pending', NULL, '', NULL, NULL, '2026-10-29 23:44:28.772824', '2026-10-29 23:44:29.009756', '2026-10-29 23:44:29.085082', NULL, 21, NULL, NULL, 2),
(3, 'completed', 'automatic', 'local', 'classforge-deterministic-inspector', 100, 100, '2 checks: 2 passed, 0 warnings, 0 failed, 0 not run.', 'Automated project assessment draft.\n\nFiles inspected: 2 (1 code, 1 documentation).\nSQL tables: 0; SQLite databases: 0; ERD detected: no; tests: 0.\nChecks: 2 passed, 0 warning(s), 0 failed, 0 not run.\n\nThis is an automated draft. The instructor must review, adjust and publish the final grade.', '{"checks": [{"key": "secrets", "label": "No secrets in the snapshot", "status": "pass", "message": "No credential patterns were detected.", "evidence": ""}, {"key": "suspicious_code", "label": "Source-code risk review", "status": "pass", "message": "No risky source patterns were detected.", "evidence": ""}], "counts": {"pass": 2, "warn": 0, "fail": 0, "skipped": 0}}', '[{"key": "secrets", "label": "No secrets in the snapshot", "status": "pass", "message": "No credential patterns were detected.", "evidence": ""}, {"key": "suspicious_code", "label": "Source-code risk review", "status": "pass", "message": "No risky source patterns were detected.", "evidence": ""}]', '{"directories": [], "extensions": {".md": 1, ".php": 1}, "entry_points": [], "top_level": ["README.md", "helloworld.php"], "code_files": 1, "documentation_files": 1}', '{"readme": {"path": "README.md", "excerpt": "php-hello-world/\\r\\n\\u251c\\u2500\\u2500 helloworld.php    # Main PHP file containing HTML and PHP code\\r\\n\\u2514\\u2500\\u2500 README.md         # Project documentation and guide"}, "docs": [], "sql": {"files": [], "table_count": 0, "has_primary_key": false, "has_foreign_key": false, "syntax_issues": []}, "databases": [], "erd": {"drawio": [], "mermaid": [], "images": [], "has_erd": false}, "tests": [], "project_files": [], "suspicious": [], "secrets": [], "structure": {"directories": [], "extensions": {".md": 1, ".php": 1}, "entry_points": [], "top_level": ["README.md", "helloworld.php"], "code_files": 1, "documentation_files": 1}}', '[{"type": "readme", "path": "README.md"}]', '', '', 1, 1, 'pending', NULL, '', NULL, '2026-10-29 23:57:25.122020', '2026-10-29 23:56:20.294482', '2026-10-29 23:56:20.513871', '2026-10-29 23:56:20.613402', 3, 23, NULL, NULL, 3);

-- project_repositories: 2 rows
INSERT INTO `project_repositories` (`id`, `provider`, `remote_url`, `default_branch`, `current_branch`, `last_commit_sha`, `git_initialised`, `created_at`, `updated_at`, `project_id`) VALUES
(2, 'local', '', 'main', 'main', 'f64748c1609609c615c2128b9d4d54b002e8d1f4', 1, '2026-10-29 23:44:26.081287', '2026-10-29 23:44:27.978294', 2),
(3, 'local', '', 'main', 'main', '116e3a4406c3aa11299a0216cf76e503e7e0f906', 1, '2026-10-29 23:56:17.628269', '2026-10-29 23:56:19.563139', 3);

-- project_snapshots: 2 rows
INSERT INTO `project_snapshots` (`id`, `version`, `source`, `branch`, `archive`, `checksum`, `commit_sha`, `base_commit_sha`, `file_count`, `total_bytes`, `manifest`, `validation`, `metadata`, `note`, `created_at`, `created_by_id`, `project_id`, `submission_id`, `parent_id`) VALUES
(2, 1, 'vscode', 'main', 'project_snapshots/2026/10/project-2-v1.zip', 'cbe9a2c2b24b3a6886ec22c31c111de65ca818e53c440c2de5e50763d66e25d9', 'f64748c1609609c615c2128b9d4d54b002e8d1f4', '', 1, 263, '[{"path": "helloworld.php", "size": 263, "sha256": "4ac01b36637a8379b23fded6953950bde0e13b82c8c0502a7d40c671c9bb106a", "extension": ".php", "is_text": true}]', '{"issues": [], "file_count": 1, "total_bytes": 263, "source_count": 1, "doc_count": 0}', '{"exclusions": []}', 'test', '2026-10-29 23:44:26.691572', 21, 2, 3, NULL),
(3, 1, 'vscode', 'main', 'project_snapshots/2026/10/project-3-v1.zip', '70c486197cfe6203766d84320f3644aeaefe21c62519c04222ebb852775333d4', '116e3a4406c3aa11299a0216cf76e503e7e0f906', '', 2, 416, '[{"path": "README.md", "size": 153, "sha256": "1e0ec78d7bcb177d7d546f4ad0785d76fba3b0185c0ff988d4900c8292e6e8cf", "extension": ".md", "is_text": true}, {"path": "helloworld.php", "size": 263, "sha256": "4ac01b36637a8379b23fded6953950bde0e13b82c8c0502a7d40c671c9bb106a", "extension": ".php", "is_text": true}]', '{"issues": [], "file_count": 2, "total_bytes": 416, "source_count": 1, "doc_count": 1}', '{"exclusions": []}', 'done readme', '2026-10-29 23:56:18.131158', 23, 3, 4, NULL);

-- project_workspaces: 2 rows
INSERT INTO `project_workspaces` (`id`, `title`, `description`, `status`, `created_at`, `updated_at`, `assignment_id`, `student_id`) VALUES
(2, 'Hello World Test Project', '', 'active', '2026-10-29 23:44:25.954214', '2026-10-29 23:44:25.954235', 2, 21),
(3, 'Hello World Test Project', '', 'active', '2026-10-29 23:56:17.527349', '2026-10-29 23:56:17.527370', 2, 23);

-- submissions: 2 rows
INSERT INTO `submissions` (`id`, `version`, `file_attachment`, `text_content`, `submitted_at`, `updated_at`, `assignment_id`, `student_id`) VALUES
(3, 1, 'submissions/2026/10/project-2-v1.zip', 'test', '2026-10-29 23:44:28.146117', '2026-10-29 23:44:28.146141', 2, 21),
(4, 1, 'submissions/2026/10/project-3-v1.zip', 'done readme', '2026-10-29 23:56:19.812628', '2026-10-29 23:56:19.812651', 2, 23);

-- tblinfo: 3 rows
INSERT INTO `tblinfo` (`id`, `name`, `age`, `address`, `email`, `created_at`, `updated_at`, `user_id`, `id_number`) VALUES
(5, 'Cyrus Pagador', 21, 'prk tres', 'sapanzacyrus143@gmail.com', '2026-10-27 09:30:54.074857', '2026-10-27 09:30:54.074883', 21, '1243254'),
(6, 'Cyrus Sapanza', 23, 'lon', 'sapanzacyrus23143@gmail.com', '2026-10-27 09:31:41.070712', '2026-10-27 09:31:41.070737', 22, '1234314'),
(7, 'Cyrus Pagador', 21, 'adaera', 'sapanzacyr2us143@gmail.com', '2026-10-29 23:48:42.957628', '2026-10-29 23:48:42.957652', 23, '123124');

-- AUTO_INCREMENT counters from sqlite_sequence
ALTER TABLE `django_migrations` AUTO_INCREMENT = 47;
ALTER TABLE `django_admin_log` AUTO_INCREMENT = 1;
ALTER TABLE `django_content_type` AUTO_INCREMENT = 42;
ALTER TABLE `auth_permission` AUTO_INCREMENT = 165;
ALTER TABLE `auth_group` AUTO_INCREMENT = 1;
ALTER TABLE `auth_user` AUTO_INCREMENT = 24;
ALTER TABLE `tblattendance` AUTO_INCREMENT = 1;
ALTER TABLE `tblcourse` AUTO_INCREMENT = 1;
ALTER TABLE `tblquizquestion` AUTO_INCREMENT = 1;
ALTER TABLE `tblstudents` AUTO_INCREMENT = 1;
ALTER TABLE `tblinfo` AUTO_INCREMENT = 8;
ALTER TABLE `portfolios` AUTO_INCREMENT = 6;
ALTER TABLE `ai_flags` AUTO_INCREMENT = 8;
ALTER TABLE `activity_logs` AUTO_INCREMENT = 83;
ALTER TABLE `courses` AUTO_INCREMENT = 2;
ALTER TABLE `enrollments` AUTO_INCREMENT = 3;
ALTER TABLE `assignment_seen` AUTO_INCREMENT = 4;
ALTER TABLE `submissions` AUTO_INCREMENT = 5;
ALTER TABLE `ai_evaluations` AUTO_INCREMENT = 8;
ALTER TABLE `grades` AUTO_INCREMENT = 4;
ALTER TABLE `assignments` AUTO_INCREMENT = 3;
ALTER TABLE `rubric_criteria` AUTO_INCREMENT = 1;
ALTER TABLE `project_assessments` AUTO_INCREMENT = 4;
ALTER TABLE `project_workspaces` AUTO_INCREMENT = 4;
ALTER TABLE `project_snapshots` AUTO_INCREMENT = 4;
ALTER TABLE `rubrics` AUTO_INCREMENT = 2;
ALTER TABLE `classforge_api_tokens` AUTO_INCREMENT = 6;
ALTER TABLE `project_repositories` AUTO_INCREMENT = 4;
ALTER TABLE `classforge_notifications` AUTO_INCREMENT = 10;

-- ---------------------------------------------------------------
-- FOREIGN KEYS
-- ---------------------------------------------------------------
ALTER TABLE `activity_logs` ADD CONSTRAINT `fk_activity_logs_actor_id` FOREIGN KEY (`actor_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `ai_evaluations` ADD CONSTRAINT `fk_ai_evaluations_submission_id` FOREIGN KEY (`submission_id`) REFERENCES `submissions` (`id`);
ALTER TABLE `ai_evaluations` ADD CONSTRAINT `fk_ai_evaluations_requested_by_id` FOREIGN KEY (`requested_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `ai_evaluations` ADD CONSTRAINT `fk_ai_evaluations_applied_by_id` FOREIGN KEY (`applied_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `ai_flags` ADD CONSTRAINT `fk_ai_flags_evaluation_id` FOREIGN KEY (`evaluation_id`) REFERENCES `ai_evaluations` (`id`);
ALTER TABLE `assignment_seen` ADD CONSTRAINT `fk_assignment_seen_student_id` FOREIGN KEY (`student_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `assignment_seen` ADD CONSTRAINT `fk_assignment_seen_assignment_id` FOREIGN KEY (`assignment_id`) REFERENCES `assignments` (`id`);
ALTER TABLE `assignments` ADD CONSTRAINT `fk_assignments_course_id` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`);
ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `fk_auth_group_permissions_permission_id` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);
ALTER TABLE `auth_group_permissions` ADD CONSTRAINT `fk_auth_group_permissions_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);
ALTER TABLE `auth_permission` ADD CONSTRAINT `fk_auth_permission_content_type_id` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);
ALTER TABLE `auth_user_groups` ADD CONSTRAINT `fk_auth_user_groups_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);
ALTER TABLE `auth_user_groups` ADD CONSTRAINT `fk_auth_user_groups_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `auth_user_user_permissions` ADD CONSTRAINT `fk_auth_user_user_permissions_permission_id` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`);
ALTER TABLE `auth_user_user_permissions` ADD CONSTRAINT `fk_auth_user_user_permissions_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `classforge_api_tokens` ADD CONSTRAINT `fk_classforge_api_tokens_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `classforge_notifications` ADD CONSTRAINT `fk_classforge_notifications_snapshot_id` FOREIGN KEY (`snapshot_id`) REFERENCES `project_snapshots` (`id`);
ALTER TABLE `classforge_notifications` ADD CONSTRAINT `fk_classforge_notifications_project_id` FOREIGN KEY (`project_id`) REFERENCES `project_workspaces` (`id`);
ALTER TABLE `classforge_notifications` ADD CONSTRAINT `fk_classforge_notifications_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `course_assistants` ADD CONSTRAINT `fk_course_assistants_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `course_assistants` ADD CONSTRAINT `fk_course_assistants_course_id` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`);
ALTER TABLE `course_assistants` ADD CONSTRAINT `fk_course_assistants_added_by_id` FOREIGN KEY (`added_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `courses` ADD CONSTRAINT `fk_courses_instructor_id` FOREIGN KEY (`instructor_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `criterion_scores` ADD CONSTRAINT `fk_criterion_scores_criterion_id` FOREIGN KEY (`criterion_id`) REFERENCES `rubric_criteria` (`id`);
ALTER TABLE `criterion_scores` ADD CONSTRAINT `fk_criterion_scores_grade_id` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`);
ALTER TABLE `django_admin_log` ADD CONSTRAINT `fk_django_admin_log_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `django_admin_log` ADD CONSTRAINT `fk_django_admin_log_content_type_id` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);
ALTER TABLE `enrollments` ADD CONSTRAINT `fk_enrollments_student_id` FOREIGN KEY (`student_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `enrollments` ADD CONSTRAINT `fk_enrollments_course_id` FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`);
ALTER TABLE `feedback_annotations` ADD CONSTRAINT `fk_feedback_annotations_grade_id` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`);
ALTER TABLE `feedback_annotations` ADD CONSTRAINT `fk_feedback_annotations_author_id` FOREIGN KEY (`author_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `grades` ADD CONSTRAINT `fk_grades_published_by_id` FOREIGN KEY (`published_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `grades` ADD CONSTRAINT `fk_grades_submission_id` FOREIGN KEY (`submission_id`) REFERENCES `submissions` (`id`);
ALTER TABLE `grades` ADD CONSTRAINT `fk_grades_instructor_id` FOREIGN KEY (`instructor_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `portfolio_items` ADD CONSTRAINT `fk_portfolio_items_portfolio_id` FOREIGN KEY (`portfolio_id`) REFERENCES `portfolios` (`id`);
ALTER TABLE `portfolio_items` ADD CONSTRAINT `fk_portfolio_items_grade_id` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`);
ALTER TABLE `portfolios` ADD CONSTRAINT `fk_portfolios_student_id` FOREIGN KEY (`student_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_assessments` ADD CONSTRAINT `fk_project_assessments_snapshot_id` FOREIGN KEY (`snapshot_id`) REFERENCES `project_snapshots` (`id`);
ALTER TABLE `project_assessments` ADD CONSTRAINT `fk_project_assessments_rubric_version_id` FOREIGN KEY (`rubric_version_id`) REFERENCES `rubric_versions` (`id`);
ALTER TABLE `project_assessments` ADD CONSTRAINT `fk_project_assessments_reviewer_id` FOREIGN KEY (`reviewer_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_assessments` ADD CONSTRAINT `fk_project_assessments_requested_by_id` FOREIGN KEY (`requested_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_assessments` ADD CONSTRAINT `fk_project_assessments_applied_grade_id` FOREIGN KEY (`applied_grade_id`) REFERENCES `grades` (`id`);
ALTER TABLE `project_criterion_assessments` ADD CONSTRAINT `fk_project_criterion_assessments_criterion_id` FOREIGN KEY (`criterion_id`) REFERENCES `rubric_criteria` (`id`);
ALTER TABLE `project_criterion_assessments` ADD CONSTRAINT `fk_project_criterion_assessments_assessment_id` FOREIGN KEY (`assessment_id`) REFERENCES `project_assessments` (`id`);
ALTER TABLE `project_pull_request_comments` ADD CONSTRAINT `fk_project_pull_request_comments_pull_request_id` FOREIGN KEY (`pull_request_id`) REFERENCES `project_pull_requests` (`id`);
ALTER TABLE `project_pull_request_comments` ADD CONSTRAINT `fk_project_pull_request_comments_author_id` FOREIGN KEY (`author_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_pull_requests` ADD CONSTRAINT `fk_project_pull_requests_revision_request_id` FOREIGN KEY (`revision_request_id`) REFERENCES `project_revision_requests` (`id`);
ALTER TABLE `project_pull_requests` ADD CONSTRAINT `fk_project_pull_requests_source_snapshot_id` FOREIGN KEY (`source_snapshot_id`) REFERENCES `project_snapshots` (`id`);
ALTER TABLE `project_pull_requests` ADD CONSTRAINT `fk_project_pull_requests_reviewed_by_id` FOREIGN KEY (`reviewed_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_pull_requests` ADD CONSTRAINT `fk_project_pull_requests_project_id` FOREIGN KEY (`project_id`) REFERENCES `project_workspaces` (`id`);
ALTER TABLE `project_pull_requests` ADD CONSTRAINT `fk_project_pull_requests_merged_snapshot_id` FOREIGN KEY (`merged_snapshot_id`) REFERENCES `project_snapshots` (`id`);
ALTER TABLE `project_pull_requests` ADD CONSTRAINT `fk_project_pull_requests_created_by_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_repositories` ADD CONSTRAINT `fk_project_repositories_project_id` FOREIGN KEY (`project_id`) REFERENCES `project_workspaces` (`id`);
ALTER TABLE `project_revision_requests` ADD CONSTRAINT `fk_project_revision_requests_snapshot_id` FOREIGN KEY (`snapshot_id`) REFERENCES `project_snapshots` (`id`);
ALTER TABLE `project_revision_requests` ADD CONSTRAINT `fk_project_revision_requests_resolved_by_id` FOREIGN KEY (`resolved_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_revision_requests` ADD CONSTRAINT `fk_project_revision_requests_requested_by_id` FOREIGN KEY (`requested_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_revision_requests` ADD CONSTRAINT `fk_project_revision_requests_project_id` FOREIGN KEY (`project_id`) REFERENCES `project_workspaces` (`id`);
ALTER TABLE `project_snapshots` ADD CONSTRAINT `fk_project_snapshots_parent_id` FOREIGN KEY (`parent_id`) REFERENCES `project_snapshots` (`id`);
ALTER TABLE `project_snapshots` ADD CONSTRAINT `fk_project_snapshots_submission_id` FOREIGN KEY (`submission_id`) REFERENCES `submissions` (`id`);
ALTER TABLE `project_snapshots` ADD CONSTRAINT `fk_project_snapshots_project_id` FOREIGN KEY (`project_id`) REFERENCES `project_workspaces` (`id`);
ALTER TABLE `project_snapshots` ADD CONSTRAINT `fk_project_snapshots_created_by_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_workspaces` ADD CONSTRAINT `fk_project_workspaces_student_id` FOREIGN KEY (`student_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `project_workspaces` ADD CONSTRAINT `fk_project_workspaces_assignment_id` FOREIGN KEY (`assignment_id`) REFERENCES `assignments` (`id`);
ALTER TABLE `rubric_criteria` ADD CONSTRAINT `fk_rubric_criteria_rubric_id` FOREIGN KEY (`rubric_id`) REFERENCES `rubrics` (`id`);
ALTER TABLE `rubric_versions` ADD CONSTRAINT `fk_rubric_versions_rubric_id` FOREIGN KEY (`rubric_id`) REFERENCES `rubrics` (`id`);
ALTER TABLE `rubric_versions` ADD CONSTRAINT `fk_rubric_versions_published_by_id` FOREIGN KEY (`published_by_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `rubric_versions` ADD CONSTRAINT `fk_rubric_versions_assignment_id` FOREIGN KEY (`assignment_id`) REFERENCES `assignments` (`id`);
ALTER TABLE `rubrics` ADD CONSTRAINT `fk_rubrics_assignment_id` FOREIGN KEY (`assignment_id`) REFERENCES `assignments` (`id`);
ALTER TABLE `submissions` ADD CONSTRAINT `fk_submissions_student_id` FOREIGN KEY (`student_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `submissions` ADD CONSTRAINT `fk_submissions_assignment_id` FOREIGN KEY (`assignment_id`) REFERENCES `assignments` (`id`);
ALTER TABLE `tblattendance` ADD CONSTRAINT `fk_tblattendance_student_id` FOREIGN KEY (`student_id`) REFERENCES `tblstudents` (`id`);
ALTER TABLE `tblcourse` ADD CONSTRAINT `fk_tblcourse_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `tblcourseschedule` ADD CONSTRAINT `fk_tblcourseschedule_course_id` FOREIGN KEY (`course_id`) REFERENCES `tblcourse` (`courseid`);
ALTER TABLE `tblinfo` ADD CONSTRAINT `fk_tblinfo_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `tblquiz` ADD CONSTRAINT `fk_tblquiz_course_id` FOREIGN KEY (`course_id`) REFERENCES `tblcourse` (`courseid`);
ALTER TABLE `tblquizquestion` ADD CONSTRAINT `fk_tblquizquestion_quiz_id` FOREIGN KEY (`quiz_id`) REFERENCES `tblquiz` (`id`);
ALTER TABLE `tblstudents` ADD CONSTRAINT `fk_tblstudents_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `user_profiles` ADD CONSTRAINT `fk_user_profiles_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

SET FOREIGN_KEY_CHECKS = 1;
