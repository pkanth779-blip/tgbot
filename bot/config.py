import os
import logging
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_ID = "default"  # Single-bot — always "default"


def get_config(key: str, default=None):
    """Fetch a single config value for this bot."""
    try:
        res = (
            supabase.table("bot_config")
            .select("value")
            .eq("bot_id", BOT_ID)
            .eq("key", key)
            .single()
            .execute()
        )
        return res.data["value"] if res.data else default
    except Exception:
        return default


def set_config(key: str, value: str):
    """Upsert a config value for this bot."""
    supabase.table("bot_config").upsert(
        {"bot_id": BOT_ID, "key": key, "value": value}
    ).execute()
