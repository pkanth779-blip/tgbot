#!/bin/bash
# Run bot in background
python -m bot.main &
BOT_PID=$!
echo "Bot started (PID: $BOT_PID)"

# Run API server in foreground (Render binds the port to this)
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
