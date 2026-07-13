CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  repo TEXT,
  status TEXT,
  payload TEXT,
  created_at TEXT,
  updated_at TEXT
);
