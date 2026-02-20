import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest
from telegram.ext import ContextTypes
from bot.config import get_config, supabase

logger = logging.getLogger(__name__)


def sanitize_url(url: str, default: str = "https://t.me/") -> str:
    """
    Ensure a URL is valid for Telegram inline buttons.
    - Empty/None  → default
    - @username   → https://t.me/username
    - No scheme   → https:// prepended
    """
    if not url or not url.strip():
        return default
    url = url.strip()
    if url.startswith("@"):
        return f"https://t.me/{url[1:]}"
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


async def _safe_delete(message):
    """Delete a message silently — never crash."""
    try:
        await message.delete()
    except Exception:
        pass


async def _send_with_photo_fallback(context, chat_id, photo_url, text, reply_markup):
    """
    Try send_photo first. If URL is bad/empty, fall back to send_message.
    Never crashes regardless of what the admin sets.
    """
    if photo_url and photo_url.strip():
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo_url.strip(),
                caption=text or "‼️ No message configured.",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return
        except (TelegramError, BadRequest, Exception) as e:
            logger.warning(f"send_photo failed (url={photo_url!r}): {e} — falling back to text")

    # Fallback: send text only
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text or "‼️ No message configured.",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"send_message also failed: {e}")


async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bot_id = context.bot_data.get("bot_id", "default")
        welcome_text = get_config("welcome_text", bot_id, "👋 Welcome! Choose an option below.")
        welcome_media_url = get_config("welcome_media_url", bot_id, "")
        demo_url = sanitize_url(get_config("demo_button_url", bot_id, ""))
        how_to_url = sanitize_url(get_config("how_to_use_button_url", bot_id, ""))

        keyboard = [
            [InlineKeyboardButton("💎 Get Premium", callback_data="get_premium")],
            [InlineKeyboardButton("🎥 Premium Demo ↗", url=demo_url or "https://t.me/")],
            [InlineKeyboardButton("✅ How To Get Premium? ↗", url=how_to_url or "https://t.me/")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        chat_id = update.effective_chat.id
        await _send_with_photo_fallback(context, chat_id, welcome_media_url, welcome_text, reply_markup)
    except Exception as e:
        logger.error(f"send_welcome error: {e}")
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="👋 Welcome! Something went wrong loading the menu. Please try again.",
            )
        except Exception:
            pass



async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_id = context.bot_data.get("bot_id", "default")
    try:
        supabase.table("bot_users").upsert({
            "bot_id": bot_id,
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "updated_at": "now()"
        }, on_conflict="bot_id, user_id").execute()
    except Exception as e:
        logger.error(f"[{bot_id}] Failed to save user {user.id}: {e}")
    await send_welcome(update, context)


async def get_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    await _safe_delete(query.message)

    try:
        bot_id = context.bot_data.get("bot_id", "default")
        premium_photo_url = get_config("premium_photo_url", bot_id, "")
        premium_text = get_config("premium_text", bot_id, "🌟 <b>Get Premium Access!</b>\n\nChoose your payment method below.")

        keyboard = [
            [InlineKeyboardButton("💳 PAY VIA UPI", callback_data="pay_upi")],
            [InlineKeyboardButton("₿ PAY VIA CRYPTO", callback_data="pay_crypto")],
            [InlineKeyboardButton("⬅️ BACK", callback_data="back_home")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _send_with_photo_fallback(context, query.message.chat_id, premium_photo_url, premium_text, reply_markup)
    except Exception as e:
        logger.error(f"get_premium_callback error: {e}")


async def pay_upi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    await _safe_delete(query.message)

    try:
        bot_id = context.bot_data.get("bot_id", "default")
        upi_qr_url = get_config("upi_qr_url", bot_id, "")
        upi_message = get_config("upi_message", bot_id, "💳 <b>Pay via UPI</b>\n\nScan the QR code above.")

        keyboard = [
            [InlineKeyboardButton("✅ I HAVE PAID", callback_data="paid_upi")],
            [InlineKeyboardButton("⬅️ BACK", callback_data="get_premium")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _send_with_photo_fallback(context, query.message.chat_id, upi_qr_url, upi_message, reply_markup)
    except Exception as e:
        logger.error(f"pay_upi_callback error: {e}")


async def pay_crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    await _safe_delete(query.message)

    try:
        bot_id = context.bot_data.get("bot_id", "default")
        crypto_qr_url = get_config("crypto_qr_url", bot_id, "")
        crypto_message = get_config("crypto_message", bot_id, "₿ <b>Pay via Crypto</b>\n\nScan the QR code above.")

        keyboard = [
            [InlineKeyboardButton("✅ I HAVE PAID", callback_data="paid_crypto")],
            [InlineKeyboardButton("⬅️ BACK", callback_data="get_premium")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _send_with_photo_fallback(context, query.message.chat_id, crypto_qr_url, crypto_message, reply_markup)
    except Exception as e:
        logger.error(f"pay_crypto_callback error: {e}")


async def back_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    await _safe_delete(query.message)
    await send_welcome(update, context)
