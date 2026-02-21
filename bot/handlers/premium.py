import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import supabase, get_config, BOT_ID

logger = logging.getLogger(__name__)


def sanitize_url(url: str, default: str = "https://t.me/") -> str:
    """Ensure URL is valid for Telegram buttons."""
    if not url or not url.strip():
        return default
    url = url.strip()
    if url.startswith("@"):
        return f"https://t.me/{url[1:]}"
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


async def _safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the welcome message with photo and buttons."""
    welcome_text = get_config("welcome_text", "👋 Welcome! Tap below to explore.")
    welcome_photo = get_config("welcome_media_url", "")
    demo_url = sanitize_url(get_config("demo_button_url", ""))
    how_to_url = sanitize_url(get_config("how_to_use_button_url", ""))

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Get Premium", callback_data="get_premium")],
        [InlineKeyboardButton("🎥 Premium Demo ↗", url=demo_url)],
        [InlineKeyboardButton("✅ How To Get Premium? ↗", url=how_to_url)],
    ])

    chat_id = update.effective_chat.id
    try:
        if welcome_photo:
            await context.bot.send_photo(
                chat_id=chat_id, photo=welcome_photo,
                caption=welcome_text, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id, text=welcome_text,
                reply_markup=keyboard, parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"send_welcome error: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Track every user who clicks /start
    try:
        supabase.table("bot_users").upsert({
            "bot_id": BOT_ID,
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "updated_at": "now()",
        }, on_conflict="bot_id, user_id").execute()
    except Exception as e:
        logger.error(f"Failed to save user {user.id}: {e}")
    await send_welcome(update, context)


async def get_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
        await query.message.delete()
    except Exception:
        pass

    premium_text = get_config("premium_text", "💎 Go Premium to unlock exclusive content!")
    premium_photo = get_config("premium_photo_url", "")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 PAY VIA UPI",    callback_data="pay_upi")],
        [InlineKeyboardButton("₿ PAY VIA CRYPTO",  callback_data="pay_crypto")],
        [InlineKeyboardButton("⬅️ BACK",            callback_data="back_home")],
    ])
    try:
        if premium_photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, photo=premium_photo,
                caption=premium_text, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=premium_text,
                reply_markup=keyboard, parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"get_premium_callback error: {e}")


async def pay_upi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
        await query.message.delete()
    except Exception:
        pass

    upi_msg = get_config("upi_message", "Send payment to our UPI ID and tap I HAVE PAID.")
    upi_qr  = get_config("upi_qr_url", "")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I HAVE PAID", callback_data="paid_upi")],
        [InlineKeyboardButton("⬅️ BACK",        callback_data="get_premium")],
    ])
    try:
        if upi_qr:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, photo=upi_qr,
                caption=upi_msg, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=upi_msg,
                reply_markup=keyboard, parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"pay_upi_callback error: {e}")


async def pay_crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
        await query.message.delete()
    except Exception:
        pass

    crypto_msg = get_config("crypto_message", "Send payment to our crypto wallet and tap I HAVE PAID.")
    crypto_qr   = get_config("crypto_qr_url", "")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I HAVE PAID", callback_data="paid_crypto")],
        [InlineKeyboardButton("⬅️ BACK",        callback_data="get_premium")],
    ])
    try:
        if crypto_qr:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, photo=crypto_qr,
                caption=crypto_msg, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=crypto_msg,
                reply_markup=keyboard, parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"pay_crypto_callback error: {e}")


async def back_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
        await query.message.delete()
    except Exception:
        pass
    await send_welcome(update, context)
