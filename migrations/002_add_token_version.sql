-- Add token_version column to qto_users for instant session revocation.
-- Bumping token_version invalidates ALL active sessions for that user.
-- Default 0 so existing tokens (without version) are treated as version 0.

ALTER TABLE qto_users ADD COLUMN IF NOT EXISTS token_version INT DEFAULT 0;
