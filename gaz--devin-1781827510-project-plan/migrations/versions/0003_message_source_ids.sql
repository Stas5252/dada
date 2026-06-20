ALTER TABLE messages ADD COLUMN source_ids JSONB NOT NULL DEFAULT '[]'::jsonb;
