-- THE QTO - ASSISTANT SaaS schema
-- Idempotent TiDB/MySQL migration.

CREATE TABLE IF NOT EXISTS qto_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    email_verified TINYINT(1) DEFAULT 0,
    reset_token_hash VARCHAR(255),
    reset_token_expires_at DATETIME,
    verification_token_hash VARCHAR(255),
    last_login_at DATETIME,
    google_id VARCHAR(255),
    microsoft_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qto_subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_tier INT DEFAULT 0,
    provider VARCHAR(50) DEFAULT 'manual',
    provider_customer_id VARCHAR(255),
    provider_subscription_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'inactive',
    current_period_start DATETIME,
    current_period_end DATETIME,
    cancel_at_period_end TINYINT(1) DEFAULT 0,
    projects_used INT DEFAULT 0,
    ai_calls_used INT DEFAULT 0,
    exports_used INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sub_user (user_id),
    INDEX idx_sub_provider (provider, provider_subscription_id)
);

CREATE TABLE IF NOT EXISTS qto_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    date VARCHAR(50),
    boq_data JSON,
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_project_user_name (user_id, name),
    INDEX idx_project_user (user_id)
);

CREATE TABLE IF NOT EXISTS qto_usage_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    project_id INT,
    event_type VARCHAR(100) NOT NULL,
    quantity INT DEFAULT 1,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usage_user_event (user_id, event_type),
    INDEX idx_usage_created (created_at)
);

CREATE TABLE IF NOT EXISTS qto_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    project_id INT,
    original_name VARCHAR(255) NOT NULL,
    storage_provider VARCHAR(50) DEFAULT 'local',
    storage_key VARCHAR(512) NOT NULL,
    content_type VARCHAR(100),
    size_bytes BIGINT DEFAULT 0,
    checksum_sha256 VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_files_user (user_id),
    INDEX idx_files_project (project_id)
);

CREATE TABLE IF NOT EXISTS qto_invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    subscription_id INT,
    provider VARCHAR(50) NOT NULL,
    provider_invoice_id VARCHAR(255),
    amount_aed DECIMAL(12, 2) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'AED',
    status VARCHAR(50) DEFAULT 'draft',
    hosted_invoice_url VARCHAR(1024),
    issued_at DATETIME,
    paid_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_invoice_user (user_id),
    INDEX idx_invoice_provider (provider, provider_invoice_id)
);

CREATE TABLE IF NOT EXISTS qto_audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    actor_user_id INT,
    action VARCHAR(150) NOT NULL,
    target_type VARCHAR(100),
    target_id VARCHAR(100),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_actor (actor_user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_created (created_at)
);

CREATE TABLE IF NOT EXISTS qto_background_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    project_id INT,
    job_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'queued',
    payload JSON,
    result JSON,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    finished_at DATETIME,
    INDEX idx_jobs_status (status),
    INDEX idx_jobs_user (user_id)
);

CREATE TABLE IF NOT EXISTS qto_market_prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL,
    unit VARCHAR(50),
    rate_aed DECIMAL(10, 2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
