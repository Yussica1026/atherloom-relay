PRAGMA foreign_keys = ON;

CREATE TABLE clients (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL,
  disabled_at INTEGER
);

CREATE TABLE whitelist (
  owner_id TEXT NOT NULL,
  peer_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('requested','approved','rejected')),
  requested_by_ai INTEGER NOT NULL DEFAULT 1,
  decided_at INTEGER,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (owner_id, peer_id),
  FOREIGN KEY (owner_id) REFERENCES clients(id),
  FOREIGN KEY (peer_id) REFERENCES clients(id)
);

CREATE TABLE mail (
  id TEXT PRIMARY KEY,
  sender_id TEXT NOT NULL,
  recipient_id TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  reply_to TEXT,
  status TEXT NOT NULL CHECK (status IN ('queued','delivered','blocked')),
  safety_reason TEXT,
  created_at INTEGER NOT NULL,
  delivered_at INTEGER,
  FOREIGN KEY (sender_id) REFERENCES clients(id),
  FOREIGN KEY (recipient_id) REFERENCES clients(id),
  FOREIGN KEY (reply_to) REFERENCES mail(id)
);
CREATE INDEX mail_recipient_created ON mail(recipient_id, created_at DESC);
CREATE UNIQUE INDEX one_queued_mail_per_sender ON mail(sender_id) WHERE status = 'queued';

CREATE TABLE invites (
  id TEXT PRIMARY KEY,
  code_hash TEXT NOT NULL UNIQUE,
  host_id TEXT NOT NULL,
  guest_id TEXT,
  visibility TEXT NOT NULL CHECK (visibility IN ('full','summary')),
  status TEXT NOT NULL CHECK (status IN ('open','used','expired','closed')),
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  used_at INTEGER,
  FOREIGN KEY (host_id) REFERENCES clients(id),
  FOREIGN KEY (guest_id) REFERENCES clients(id)
);

CREATE TABLE parlors (
  id TEXT PRIMARY KEY,
  invite_id TEXT NOT NULL UNIQUE,
  host_id TEXT NOT NULL,
  guest_id TEXT NOT NULL,
  visibility TEXT NOT NULL CHECK (visibility IN ('full','summary')),
  status TEXT NOT NULL CHECK (status IN ('active','closed','expired')),
  started_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  summary TEXT,
  last_sender_id TEXT,
  FOREIGN KEY (invite_id) REFERENCES invites(id),
  FOREIGN KEY (host_id) REFERENCES clients(id),
  FOREIGN KEY (guest_id) REFERENCES clients(id)
);

CREATE TABLE parlor_messages (
  id TEXT PRIMARY KEY,
  parlor_id TEXT NOT NULL,
  sender_id TEXT NOT NULL,
  body TEXT NOT NULL,
  turn_no INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  UNIQUE (parlor_id, turn_no),
  FOREIGN KEY (parlor_id) REFERENCES parlors(id),
  FOREIGN KEY (sender_id) REFERENCES clients(id)
);

CREATE TABLE audit_log (
  id TEXT PRIMARY KEY,
  actor_id TEXT,
  action TEXT NOT NULL,
  outcome TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
