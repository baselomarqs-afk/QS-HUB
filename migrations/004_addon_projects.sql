-- Add extra_projects_allowance column to qto_users
ALTER TABLE qto_users ADD COLUMN IF NOT EXISTS extra_projects_allowance INT DEFAULT 0;
