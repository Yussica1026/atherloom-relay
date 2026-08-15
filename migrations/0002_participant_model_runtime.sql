ALTER TABLE parlor_participants ADD COLUMN model_status TEXT NOT NULL DEFAULT 'idle';
ALTER TABLE parlor_participants ADD COLUMN model_status_mode TEXT;
ALTER TABLE parlor_participants ADD COLUMN model_status_detail TEXT;
ALTER TABLE parlor_participants ADD COLUMN model_status_updated_at INTEGER;
