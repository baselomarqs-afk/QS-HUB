-- Migration: 010_project_feedback
-- Description: Creates the tables backing the in-app "Rate Your Experience"
-- ratings and the customer complaints box. These were only defined in the
-- local SQLite bootstrap, so on MySQL the inserts (and the admin panel that
-- reads them) had no table to hit. IF NOT EXISTS keeps this safe if a table
-- was already created manually in production.

CREATE TABLE IF NOT EXISTS qto_project_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    rating INT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qto_customer_complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    complaint_text TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
