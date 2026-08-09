-- Migration 011: Create Visitor Logs Table for Web Traffic Analytics
CREATE TABLE IF NOT EXISTS qto_visitor_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    path VARCHAR(255) NOT NULL,
    user_agent VARCHAR(512),
    referer VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_visitor_created ON qto_visitor_logs(created_at);
