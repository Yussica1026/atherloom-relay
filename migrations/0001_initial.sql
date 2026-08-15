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
  topic TEXT,
  web_search_allowed INTEGER NOT NULL DEFAULT 1,
  phase TEXT NOT NULL DEFAULT 'topic',
  phase_started_at INTEGER NOT NULL DEFAULT 0,
  topic_proposer_id TEXT,
  topic_cursor INTEGER NOT NULL DEFAULT 0,
  host_transfer_used INTEGER NOT NULL DEFAULT 0,
  turn_owner_id TEXT,
  turn_started_at INTEGER NOT NULL DEFAULT 0,
  waiting_seconds_excluded INTEGER NOT NULL DEFAULT 0,
  formal_duration_seconds INTEGER NOT NULL DEFAULT 300,
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

CREATE TABLE parlor_participants (
  parlor_id TEXT NOT NULL,
  client_id TEXT NOT NULL,
  role TEXT NOT NULL,
  joined_at INTEGER NOT NULL,
  seat_no INTEGER NOT NULL DEFAULT 0,
  persona_name TEXT,
  species TEXT,
  gender TEXT,
  identity_declared_at INTEGER,
  model_status TEXT NOT NULL DEFAULT 'idle',
  model_status_mode TEXT,
  model_status_detail TEXT,
  model_status_updated_at INTEGER,
  PRIMARY KEY (parlor_id, client_id)
);
CREATE INDEX parlor_participant_room ON parlor_participants(parlor_id, joined_at);

CREATE TABLE parlor_votes (
  id TEXT PRIMARY KEY,
  parlor_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  value TEXT NOT NULL,
  proposer_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  resolved_at INTEGER,
  expires_at INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX parlor_votes_active ON parlor_votes(parlor_id, status);

CREATE TABLE parlor_vote_choices (
  vote_id TEXT NOT NULL,
  client_id TEXT NOT NULL,
  choice TEXT NOT NULL,
  roll INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (vote_id, client_id)
);

CREATE TABLE parlor_interruptions (
  id TEXT PRIMARY KEY,
  parlor_id TEXT NOT NULL,
  requester_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  resolved_at INTEGER
);

CREATE TABLE parlor_client_bans (
  client_id TEXT PRIMARY KEY,
  reason TEXT NOT NULL,
  parlor_id TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE audit_log (
  id TEXT PRIMARY KEY,
  actor_id TEXT,
  action TEXT NOT NULL,
  outcome TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
