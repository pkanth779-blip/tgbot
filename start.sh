#!/bin/bash
# Start Telegram bot in background (non-blocking)
python -m bot.main &
BOT_PID=$!

echo "Bot started (PID: $BOT_PID)"

# Start API server in FOREGROUND so Render sees port binding
# This is the main process Render monitors
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
