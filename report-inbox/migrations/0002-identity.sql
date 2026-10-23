ALTER TABLE verified_hardware ADD COLUMN identity_source TEXT NOT NULL DEFAULT 'detected';
ALTER TABLE verified_hardware ADD COLUMN detected_gpu_name TEXT NOT NULL DEFAULT '';
