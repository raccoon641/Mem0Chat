-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    whatsapp_user_id VARCHAR(64) NOT NULL,
    phone_number VARCHAR(32),
    timezone VARCHAR(64) DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Interactions table
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    twilio_message_sid VARCHAR(64) UNIQUE,
    message_direction VARCHAR(16) NOT NULL DEFAULT 'inbound',
    message_type VARCHAR(16) NOT NULL,
    body_text TEXT,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_occurred ON interactions(occurred_at);

-- Media assets
CREATE TABLE IF NOT EXISTS media_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interaction_id INTEGER NOT NULL REFERENCES interactions(id) ON DELETE CASCADE,
    media_url TEXT,
    local_path TEXT,
    content_type VARCHAR(128),
    sha256_hash VARCHAR(128) NOT NULL UNIQUE,
    width_px INTEGER,
    height_px INTEGER,
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_media_sha ON media_assets(sha256_hash);

-- Memories
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    interaction_id INTEGER REFERENCES interactions(id) ON DELETE SET NULL,
    mem0_id VARCHAR(128),
    memory_type VARCHAR(16) NOT NULL,
    title VARCHAR(255),
    text TEXT,
    labels_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at); 