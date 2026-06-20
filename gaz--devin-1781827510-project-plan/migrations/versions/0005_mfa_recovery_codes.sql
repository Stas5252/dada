ALTER TABLE users
  ADD COLUMN mfa_recovery_code_hashes JSON NOT NULL DEFAULT '[]';
