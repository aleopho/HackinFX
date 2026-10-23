CREATE TABLE IF NOT EXISTS reports (
 id TEXT PRIMARY KEY,
 submission_id TEXT NOT NULL UNIQUE,
 created_at TEXT NOT NULL,
 fingerprint TEXT NOT NULL,
 outcome TEXT NOT NULL,
 payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS reports_created ON reports(created_at);
CREATE INDEX IF NOT EXISTS reports_fingerprint ON reports(fingerprint);

CREATE TABLE IF NOT EXISTS verified_hardware (
 id TEXT PRIMARY KEY,
 installation_id TEXT NOT NULL,
 hardware_key TEXT NOT NULL,
 gpu_name TEXT NOT NULL,
 gpu_vendor TEXT NOT NULL,
 board_vendor TEXT NOT NULL,
 profile TEXT NOT NULL,
 confirmed_effects TEXT NOT NULL,
 macos TEXT NOT NULL,
 arch TEXT NOT NULL,
 driver_version TEXT NOT NULL,
 confirmed_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 identity_source TEXT NOT NULL DEFAULT 'detected',
 detected_gpu_name TEXT NOT NULL DEFAULT '',
 UNIQUE(installation_id, hardware_key)
);
CREATE INDEX IF NOT EXISTS verified_hardware_key ON verified_hardware(hardware_key);
