import os
import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.config import supabase

logger = logging.getLogger(__name__)

WAITING_SCREENSHOT_UPI = 1
WAITING_SCREENSHOT_CRYPTO = 2


def _owner_ids() -> set[int]:
    try:
        raw = os.getenv("ADMIN_TELEGRAM_ID", "0")
        return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
    except Exception:
        return {0}


async def paid_upi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    try:
        await query.message.delete()
    except Exception:
        pass
    context.user_data["payment_type"] = "upi"
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📸 <b>Please send your payment screenshot now.</b>\n\nWe will verify it and activate your premium access shortly.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"paid_upi_callback send error: {e}")
    return WAITING_SCREENSHOT_UPI


async def paid_crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    try:
        await query.message.delete()
    except Exception:
        pass
    context.user_data["payment_type"] = "crypto"
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📸 <b>Please send your payment screenshot now.</b>\n\nWe will verify it and activate your premium access shortly.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"paid_crypto_callback send error: {e}")
    return WAITING_SCREENSHOT_CRYPTO


async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    payment_type = context.user_data.get("payment_type", "upi")
    bot_id = context.bot_data.get("bot_id", "default")

    # Accept photo or document image
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        try:
            await update.message.reply_text("❌ Please send a photo/screenshot of your payment.")
        except Exception:
            pass
        return WAITING_SCREENSHOT_UPI if payment_type == "upi" else WAITING_SCREENSHOT_CRYPTO

    # Save to Supabase
    payment_id = None
    try:
        result = supabase.table("payments").insert({
            "bot_id": bot_id,
            "user_id": user.id,
            "username": user.username or user.first_name or str(user.id),
            "payment_type": payment_type,
            "screenshot_file_id": file_id,
            "status": "pending",
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }).execute()
        if result.data:
            payment_id = result.data[0].get("id")
        logger.info(f"[{bot_id}] Payment saved for user {user.id} ({payment_type}) id={payment_id}")
    except Exception as e:
        logger.error(f"[{bot_id}] Supabase insert failed: {e}")
        try:
            await update.message.reply_text(
                "⚠️ We received your screenshot but had a temporary issue saving it. "
                "Please try again in a moment."
            )
        except Exception:
            pass
        return ConversationHandler.END

    # Confirm to user immediately
    try:
        await update.message.reply_text(
            "✅ <b>Screenshot received!</b>\n\nOur admin will verify your payment shortly. "
            "You'll be notified once it's confirmed. Thank you! 🙏",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"reply_text error: {e}")

    # ── Notify ALL admins — real-time payment card with Approve/Reject ─────────
    # ── Notify ALL admins — real-time payment card with Approve/Reject ─────────
    owners = _owner_ids()
    # Gather extra admins from Supabase for this bot
    extra_ids = []
    try:
        from bot.config import get_config as _get_cfg
        raw = _get_cfg("extra_admins", bot_id, "")
        if raw:
            extra_ids = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
    except Exception:
        pass

    all_admin_ids = list(owners | set(extra_ids))
    # Remove 0 or invalid IDs just in case
    all_admin_ids = [aid for aid in all_admin_ids if aid > 0]

    if all_admin_ids and payment_id:
        username_str = f"@{user.username}" if user.username else str(user.id)
        caption = (
            f"💰 <b>PAYMENT REQUEST</b>\n\n"
            f"🤖 Bot: <b>{bot_id.upper()}</b>\n"
            f"👤 User: {username_str}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"💳 Method: <b>{payment_type.upper()}</b>\n\n"
            f"<i>First admin action will be final.</i>"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ APPROVE", callback_data=f"mgr_approve_{payment_id}"),
            InlineKeyboardButton("❌ REJECT",  callback_data=f"mgr_reject_{payment_id}"),
        ]])
        for aid in all_admin_ids:
            try:
                await context.bot.send_photo(
                    chat_id=aid,
                    photo=file_id,
                    caption=caption,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"[{bot_id}] Photo notify to {aid} failed: {e} — trying text")
                try:
                    await context.bot.send_message(
                        chat_id=aid,
                        text=caption,
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                except Exception as e2:
                    logger.error(f"[{bot_id}] Notify to admin {aid} completely failed: {e2}")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    try:
        await update.message.reply_text("Cancelled. Send /start to begin again.")
    except Exception:
        pass
    return ConversationHandler.END
