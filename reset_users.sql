-- ============================================================
-- RESET ALL USER DATA (keeps bot config/settings)
-- Run in Supabase SQL Editor when you want a fresh start
-- ============================================================

TRUNCATE TABLE bot_users RESTART IDENTITY CASCADE;
TRUNCATE TABLE payments  RESTART IDENTITY CASCADE;

-- Verify (both should return 0)
SELECT COUNT(*) AS users_count    FROM bot_users;
SELECT COUNT(*) AS payments_count FROM payments;
