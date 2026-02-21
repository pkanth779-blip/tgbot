# 🤖 Telegram Bot — Single Bot

A complete Telegram bot with premium payment flow, screenshot-based payment verification, and a full inline admin panel — all for a single bot instance.

## 📁 Project Structure

```
├── bot/
│   ├── config.py             # Supabase client + config helpers
│   ├── main.py               # Bot entry point
│   └── handlers/
│       ├── premium.py        # /start, welcome, premium, UPI, Crypto
│       ├── payment.py        # Screenshot collection + admin notification
│       └── manage.py         # /manage — full inline admin panel
├── api/
│   └── main.py               # FastAPI: auth, config, payments API
├── supabase_schema.sql        # Run in Supabase SQL Editor
├── reset_users.sql            # Clear users/payments (keeps settings)
├── Procfile                   # Render deployment
├── start.sh                   # Startup script (bot bg, uvicorn fg)
├── runtime.txt                # Python 3.11
├── requirements.txt
└── .env.example
```

## 🚀 Setup

### 1. Supabase
1. Create project at [supabase.com](https://supabase.com)
2. **SQL Editor** → paste & run `supabase_schema.sql`
3. Copy your **Project URL** and **service_role key**

### 2. Create `.env`
```env
BOT_TOKEN=your_telegram_bot_token
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
ADMIN_TELEGRAM_ID=your_telegram_user_id       # comma-separated for multiple owners
API_SECRET=any_random_string
ADMIN_PASSWORD=your_admin_panel_password
```

### 3. Deploy to Render
1. Push repo to GitHub
2. Render → **New Web Service** → connect your repo
3. Add all env vars
4. Deploy! (uses `Procfile` → `start.sh` automatically)

## 🤖 Bot Features

| Feature | Command/Action |
|---|---|
| Welcome screen | `/start` |
| Premium flow | Get Premium → UPI / Crypto |
| Payment submit | Screenshot → saved as "pending" |
| Admin panel | `/manage` |

## 🛠 Admin Panel (`/manage`)

| Section | What it does |
|---|---|
| 📊 Stats | Unique users, payments breakdown |
| 👥 Users | All Users / Approved Users |
| 💳 Payments | View & approve/reject pending screenshots |
| 📢 Broadcast | Send message to all users |
| 👤 Admin Control | Add/remove extra admins |
| ⚙️ Settings | Edit all text, photos, URLs from Telegram |
| 🔗 Join Link | Set your group/channel link |

## 🗄️ Database Reset

To wipe all users/payments for a fresh start:
```sql
-- Run in Supabase SQL Editor
TRUNCATE TABLE bot_users RESTART IDENTITY CASCADE;
TRUNCATE TABLE payments  RESTART IDENTITY CASCADE;
```
Or use the included `reset_users.sql` file.

## 📡 UptimeRobot (24/7)

Ping `https://your-render-app.onrender.com/health` every 5 minutes.
