-- Migration: 005_ai_learning_memory
-- Description: Creates the qto_memory_rules table to store user-specific AI mappings and global rules.

CREATE TABLE IF NOT EXISTS qto_ai_category_mappings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    original_text TEXT NOT NULL,
    mapped_category TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
