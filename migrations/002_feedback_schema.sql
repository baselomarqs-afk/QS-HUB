CREATE TABLE IF NOT EXISTS qto_ai_corrections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    drawing_type VARCHAR(50),
    item_key VARCHAR(100),
    original_value VARCHAR(255),
    corrected_value VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES qto_users(id) ON DELETE SET NULL
);
