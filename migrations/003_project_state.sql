-- Create table for saving active project states
CREATE TABLE IF NOT EXISTS qto_active_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    current_step INT DEFAULT 1,
    state_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES qto_users(id) ON DELETE CASCADE,
    UNIQUE KEY (user_id)
);
