-- ============================================================
-- SUPABASE SCHEMA — Single Bot
-- Run this entire script in Supabase SQL Editor
-- ============================================================

-- Bot configuration (welcome text, photo URLs, payment messages, etc.)
CREATE TABLE IF NOT EXISTS bot_config (
    id         BIGSERIAL PRIMARY KEY,
    bot_id     TEXT NOT NULL DEFAULT 'default',
    key        TEXT NOT NULL,
    value      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (bot_id, key)
);

-- All users who clicked /start
CREATE TABLE IF NOT EXISTS bot_users (
    id         BIGSERIAL PRIMARY KEY,
    bot_id     TEXT NOT NULL DEFAULT 'default',
    user_id    BIGINT NOT NULL,
    username   TEXT,
    first_name TEXT,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (bot_id, user_id)
);

-- Payment submissions
CREATE TABLE IF NOT EXISTS payments (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id               TEXT NOT NULL DEFAULT 'default',
    user_id              BIGINT NOT NULL,
    username             TEXT,
    payment_type         TEXT NOT NULL,      -- 'upi' or 'crypto'
    screenshot_file_id   TEXT,
    status               TEXT NOT NULL DEFAULT 'pending',  -- pending / confirmed / rejected
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Indexes for performance ──────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_bot_config_bot    ON bot_config (bot_id, key);
CREATE INDEX IF NOT EXISTS idx_bot_users_bot     ON bot_users  (bot_id, user_id);
CREATE INDEX IF NOT EXISTS idx_payments_bot      ON payments   (bot_id, status);
CREATE INDEX IF NOT EXISTS idx_payments_user     ON payments   (user_id);
