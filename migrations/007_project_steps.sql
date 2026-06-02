-- Add current_step column to qto_projects to support resuming projects from specific steps
ALTER TABLE qto_projects 
ADD COLUMN IF NOT EXISTS current_step INT DEFAULT 1;
