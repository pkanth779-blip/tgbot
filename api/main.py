from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, datetime
import httpx
from supabase import create_client
from dotenv import load_dotenv
from telegram import Bot as TelegramBot

load_dotenv()

SUPABASE_URL   = os.environ["SUPABASE_URL"]
SUPABASE_KEY   = os.environ["SUPABASE_KEY"]
API_SECRET     = os.getenv("API_SECRET", "changeme")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
BOT_ID         = "default"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="TG Bot Admin API — Single Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"status": "ok", "bot": BOT_ID}


# ── Auth ───────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str


@app.post("/auth/login")
def login(req: LoginRequest):
    if req.password == ADMIN_PASSWORD:
        return {"token": API_SECRET}
    raise HTTPException(status_code=401, detail="Invalid password")


def verify_token(x_api_key: str = Header(...)):
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Bot info ───────────────────────────────────────────────────────────────────

@app.get("/bot", dependencies=[Depends(verify_token)])
async def get_bot_info():
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            r = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
            data = r.json().get("result", {})
            return {
                "bot_id": BOT_ID,
                "username": data.get("username", "unknown"),
                "first_name": data.get("first_name", "Bot"),
            }
        except Exception:
            return {"bot_id": BOT_ID, "username": "unknown", "first_name": "Bot"}


# ── Config helpers ─────────────────────────────────────────────────────────────

def _get_config(key: str, default=""):
    try:
        res = (supabase.table("bot_config")
               .select("value").eq("bot_id", BOT_ID).eq("key", key)
               .single().execute())
        return res.data["value"] if res.data else default
    except Exception:
        return default


def _set_config(key: str, value: str):
    supabase.table("bot_config").upsert(
        {"bot_id": BOT_ID, "key": key, "value": value}
    ).execute()


# ── Config endpoints ───────────────────────────────────────────────────────────

class ConfigUpdate(BaseModel):
    value: str


@app.get("/config", dependencies=[Depends(verify_token)])
def get_all_config():
    res = (supabase.table("bot_config").select("key, value")
           .eq("bot_id", BOT_ID).execute())
    return {row["key"]: row["value"] for row in (res.data or [])}


@app.get("/config/{key}", dependencies=[Depends(verify_token)])
def get_config(key: str):
    return {"key": key, "value": _get_config(key)}


@app.put("/config/{key}", dependencies=[Depends(verify_token)])
def update_config(key: str, body: ConfigUpdate):
    _set_config(key, body.value)
    return {"key": key, "value": body.value}


# ── Image Upload ───────────────────────────────────────────────────────────────

from fastapi import UploadFile, File
import uuid

STORAGE_BUCKET = "bot-images"


@app.post("/upload", dependencies=[Depends(verify_token)])
async def upload_image(file: UploadFile = File(...)):
    content = await file.read()
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
        raise HTTPException(status_code=400, detail="Only image files allowed")
    filename = f"{BOT_ID}/{uuid.uuid4()}.{ext}"
    content_type = file.content_type or f"image/{ext}"
    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(
            filename, content,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(filename)
        return {"url": public_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ── Telegram file URL ──────────────────────────────────────────────────────────

@app.get("/file/{file_id}", dependencies=[Depends(verify_token)])
async def get_telegram_file_url(file_id: str):
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id}
        )
        data = r.json()
        if not data.get("ok"):
            raise HTTPException(status_code=400, detail="Could not fetch file from Telegram")
        file_path = data["result"]["file_path"]
        return {"url": f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"}


# ── Payments ───────────────────────────────────────────────────────────────────

@app.get("/payments", dependencies=[Depends(verify_token)])
def get_payments():
    res = (supabase.table("payments").select("*")
           .eq("bot_id", BOT_ID).order("created_at", desc=True).execute())
    return res.data or []


class PaymentAction(BaseModel):
    status: str  # "confirmed" or "rejected"


@app.patch("/payments/{payment_id}", dependencies=[Depends(verify_token)])
async def update_payment(payment_id: str, body: PaymentAction):
    if body.status not in ("confirmed", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status")

    res = (supabase.table("payments").select("*")
           .eq("id", payment_id).single().execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment = res.data
    user_id = payment["user_id"]

    supabase.table("payments").update({
        "status": body.status,
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }).eq("id", payment_id).execute()

    if BOT_TOKEN:
        bot = TelegramBot(token=BOT_TOKEN)
        try:
            if body.status == "confirmed":
                msg = _get_config(
                    "payment_confirmed_message",
                    "🎉 <b>Payment Confirmed!</b>\n\nYour premium access has been activated. Welcome! 🌟"
                )
            else:
                msg = (
                    "❌ <b>Payment Rejected</b>\n\n"
                    "We could not verify your payment screenshot.\n"
                    "Please send a clear screenshot and try again with /start."
                )
            await bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
        except Exception:
            pass

    return {"id": payment_id, "status": body.status}
