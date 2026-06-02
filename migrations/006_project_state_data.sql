-- Add state_data column to qto_projects to support resuming projects
ALTER TABLE qto_projects 
ADD COLUMN IF NOT EXISTS state_data JSON;
