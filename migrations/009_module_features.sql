-- Per-feature one-time credits for the Work Programme & Cash Flow tools (50 AED each).
ALTER TABLE qto_users ADD COLUMN IF NOT EXISTS programme_credits INT DEFAULT 0;
ALTER TABLE qto_users ADD COLUMN IF NOT EXISTS cashflow_credits INT DEFAULT 0;

-- Saved history for the module tools (feature = 'programme' | 'cashflow').
CREATE TABLE IF NOT EXISTS qto_module_projects (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  feature VARCHAR(20) NOT NULL,
  name VARCHAR(255) NOT NULL,
  date VARCHAR(32),
  config_data LONGTEXT,
  summary_data LONGTEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
