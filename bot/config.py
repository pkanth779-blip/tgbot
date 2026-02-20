import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]
API_SECRET: str = os.getenv("API_SECRET", "changeme")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_config(key: str, bot_id: str = "default", default=None):
    """Fetch a single config value scoped to a BOT_ID."""
    try:
        res = (
            supabase.table("bot_config")
            .select("value")
            .eq("bot_id", bot_id)
            .eq("key", key)
            .single()
            .execute()
        )
        return res.data["value"] if res.data else default
    except Exception:
        return default


def set_config(key: str, value: str, bot_id: str = "default"):
    """Upsert a config value scoped to a BOT_ID."""
    supabase.table("bot_config").upsert(
        {"bot_id": bot_id, "key": key, "value": value}
    ).execute()


def get_all_bot_tokens() -> dict[str, str]:
    """
    Return a dict of {bot_id: token} from env vars.
    Reads BOT_TOKEN_1/BOT_ID_1, BOT_TOKEN_2/BOT_ID_2, etc.
    Also accepts a single BOT_TOKEN/BOT_ID for backward compat.
    """
    tokens = {}

    # Single bot mode (legacy)
    single_token = os.getenv("BOT_TOKEN", "")
    single_id = os.getenv("BOT_ID", "default")
    if single_token:
        tokens[single_id] = single_token

    # Multi-bot mode
    for i in range(1, 6):
        token = os.getenv(f"BOT_TOKEN_{i}", "")
        bot_id = os.getenv(f"BOT_ID_{i}", f"bot{i}")
        if token:
            tokens[bot_id] = token

    return tokens
