"""
Admin panel for the single-bot project.
Command: /manage
Features: Stats, Users (All/Approved), Payments, Broadcast,
          Admin Control, Settings (Welcome/Premium/UPI/Crypto/Join Link).
"""

import os
import logging
import asyncio
import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CommandHandler, CallbackQueryHandler, MessageHandler, filters,
)
from bot.config import supabase, get_config, set_config, BOT_ID

logger = logging.getLogger(__name__)

# ── Conversation states ────────────────────────────────────────────────────────
MAIN_MENU       = 0
AWAIT_BROADCAST = 1
AWAIT_SETTING   = 2
AWAIT_ADD_ADMIN = 3
AWAIT_JOIN_LINK = 4

# ── Helpers ────────────────────────────────────────────────────────────────────

def _owner_ids() -> set[int]:
    try:
        raw = os.getenv("ADMIN_TELEGRAM_ID", "0")
        return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
    except Exception:
        return {0}


def is_admin(user_id: int) -> bool:
    if user_id in _owner_ids():
        return True
    try:
        raw = get_config("extra_admins", "")
        if raw:
            ids = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
            return user_id in ids
    except Exception:
        pass
    return False


def _back_kb(target: str = "mgr_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=target)]])


async def _confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        await update.message.reply_text(text)
    except Exception:
        pass
    return ConversationHandler.END


# ── Entry point ────────────────────────────────────────────────────────────────

async def manage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        try:
            await update.message.reply_text("⛔ Access denied.")
        except Exception:
            pass
        return ConversationHandler.END
    await _send_main_menu(update, context)
    return MAIN_MENU


async def _send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats",         callback_data="mgr_stats"),
         InlineKeyboardButton("👥 Users",         callback_data="mgr_users")],
        [InlineKeyboardButton("💳 Payments",       callback_data="mgr_payments"),
         InlineKeyboardButton("📢 Broadcast",      callback_data="mgr_broadcast")],
        [InlineKeyboardButton("👤 Admin Control",  callback_data="mgr_admin_control"),
         InlineKeyboardButton("⚙️ Settings",       callback_data="mgr_settings")],
        [InlineKeyboardButton("🔗 Join Link",      callback_data="mgr_join_link")],
    ])
    text = "🤖 <b>Admin Panel</b>\n\nChoose an option:"
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        else:
            await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


async def cb_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await _send_main_menu(update, context)
    return MAIN_MENU


# ── Stats ──────────────────────────────────────────────────────────────────────

async def cb_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        total = supabase.table("payments").select("id", count="exact").eq("bot_id", BOT_ID).execute().count or 0
        pending   = supabase.table("payments").select("id", count="exact").eq("bot_id", BOT_ID).eq("status", "pending").execute().count or 0
        confirmed = supabase.table("payments").select("id", count="exact").eq("bot_id", BOT_ID).eq("status", "confirmed").execute().count or 0
        rejected  = supabase.table("payments").select("id", count="exact").eq("bot_id", BOT_ID).eq("status", "rejected").execute().count or 0
        unique    = supabase.table("bot_users").select("user_id", count="exact").eq("bot_id", BOT_ID).execute().count or 0
    except Exception as e:
        logger.error(f"Stats error: {e}")
        total = pending = confirmed = rejected = unique = 0

    text = (
        f"📊 <b>Stats</b>\n\n"
        f"👥 Unique Users (Start): <b>{unique}</b>\n"
        f"📋 Total Payments: <b>{total}</b>\n"
        f"⏳ Pending: <b>{pending}</b>\n"
        f"✅ Confirmed: <b>{confirmed}</b>\n"
        f"❌ Rejected: <b>{rejected}</b>"
    )
    try:
        await update.callback_query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")
    except Exception:
        pass
    return MAIN_MENU


# ── Users ──────────────────────────────────────────────────────────────────────

async def cb_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 All Users",      callback_data="mgr_users_all")],
        [InlineKeyboardButton("✅ Approved Users", callback_data="mgr_users_approved")],
        [InlineKeyboardButton("⬅️ Back",           callback_data="mgr_main")],
    ])
    try:
        await update.callback_query.edit_message_text(
            "👥 <b>Users</b>\n\nChoose a list to view:",
            reply_markup=kb, parse_mode="HTML"
        )
    except Exception:
        pass
    return MAIN_MENU


async def cb_users_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        rows_u = (supabase.table("bot_users").select("user_id, username, first_name, updated_at")
                  .eq("bot_id", BOT_ID).execute()).data or []
        rows_p = (supabase.table("payments").select("user_id, username, created_at")
                  .eq("bot_id", BOT_ID).execute()).data or []

        seen = {}
        for r in rows_u:
            seen[r["user_id"]] = (r.get("username") or r.get("first_name") or str(r["user_id"]),
                                  r.get("updated_at", ""))
        for r in rows_p:
            uid = r["user_id"]
            if uid not in seen:
                seen[uid] = (r.get("username") or str(uid), r.get("created_at", ""))

        sorted_users = sorted(seen.items(), key=lambda x: x[1][1], reverse=True)

        if not sorted_users:
            text = "👥 <b>All Users</b>\n\nNo users yet."
        else:
            lines = [f"👥 <b>All Users</b> ({len(sorted_users)} total)\n"]
            for uid, (name, _) in sorted_users[:50]:
                name_str = f"@{name}" if name and not name.isdigit() else str(uid)
                lines.append(f"• <code>{uid}</code> {name_str}")
            if len(sorted_users) > 50:
                lines.append(f"\n…and {len(sorted_users) - 50} more.")
            text = "\n".join(lines)
    except Exception as e:
        text = f"❌ Error fetching users: {e}"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="mgr_users")]])
    try:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    return MAIN_MENU


async def cb_users_approved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        rows = (supabase.table("payments").select("user_id, username, created_at")
                .eq("bot_id", BOT_ID).eq("status", "confirmed")
                .order("created_at", desc=True).execute()).data or []

        if not rows:
            text = "✅ <b>Approved Users</b>\n\nNo approved users yet."
        else:
            seen = {}
            for r in rows:
                seen[r["user_id"]] = r.get("username") or str(r["user_id"])
            lines = [f"✅ <b>Approved Users</b> ({len(seen)} total)\n"]
            for uid, name in seen.items():
                name_str = f"@{name}" if name and not name.isdigit() else str(uid)
                lines.append(f"• <code>{uid}</code> {name_str}")
            text = "\n".join(lines)
    except Exception as e:
        text = f"❌ Error: {e}"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="mgr_users")]])
    try:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    return MAIN_MENU


# ── Payments ───────────────────────────────────────────────────────────────────

async def cb_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        rows = (supabase.table("payments").select("*")
                .eq("bot_id", BOT_ID).eq("status", "pending")
                .order("created_at", desc=True).limit(10).execute()).data or []
    except Exception as e:
        rows = []
        logger.error(f"Fetch payments error: {e}")

    if not rows:
        try:
            await update.callback_query.edit_message_text(
                "💳 <b>Payments</b>\n\nNo pending payments.",
                reply_markup=_back_kb(), parse_mode="HTML"
            )
        except Exception:
            pass
        return MAIN_MENU

    await update.callback_query.edit_message_text(
        f"💳 <b>Pending Payments</b> ({len(rows)} shown)\n\nSending screenshots…",
        parse_mode="HTML"
    )

    for p in rows:
        uid   = p["user_id"]
        uname = p.get("username") or str(uid)
        ptype = p.get("payment_type", "?").upper()
        pid   = p["id"]
        caption = (
            f"💳 <b>Payment Request</b>\n"
            f"👤 @{uname} (<code>{uid}</code>)\n"
            f"Method: {ptype}\n"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"mgr_approve_{pid}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"mgr_reject_{pid}"),
        ]])
        fid = p.get("screenshot_file_id", "")
        try:
            if fid:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id, photo=fid,
                    caption=caption, reply_markup=kb, parse_mode="HTML"
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=caption,
                    reply_markup=kb, parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Send payment screenshot error: {e}")
        await asyncio.sleep(0.3)

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⬆️ All pending payments shown above.\nTap ✅/❌ to approve or reject.",
            reply_markup=_back_kb()
        )
    except Exception:
        pass
    return MAIN_MENU


async def cb_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.answer("⛔ Access denied.", show_alert=True)
        return

    await query.answer("Processing…")
    payment_id = query.data.split("_", 2)[2]

    try:
        res = supabase.table("payments").select("*").eq("id", payment_id).single().execute()
        payment = res.data
        if not payment:
            await query.edit_message_caption("❌ Payment not found.")
            return MAIN_MENU
        if payment["status"] != "pending":
            await query.answer(f"Already {payment['status']}.", show_alert=True)
            return MAIN_MENU

        supabase.table("payments").update({
            "status": "confirmed",
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }).eq("id", payment_id).execute()

        msg = get_config("payment_confirmed_message",
                         "🎉 <b>Payment Confirmed!</b>\n\nYour premium access has been activated. Welcome! 🌟")
        
        # Add join link button if configured
        reply_markup_user = None
        jlink = get_config("join_link", "")
        if jlink:
            reply_markup_user = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔗 JOIN NOW", url=jlink)
            ]])

        try:
            await context.bot.send_message(
                chat_id=payment["user_id"], 
                text=msg, 
                parse_mode="HTML",
                reply_markup=reply_markup_user
            )
        except Exception as e:
            logger.error(f"Failed to send confirmation to user {payment['user_id']}: {e}")

        try:
            # Clear buttons and update caption on admin side
            new_caption = (query.message.caption or "") + "\n\n✅ <b>APPROVED</b>"
            await query.edit_message_caption(
                caption=new_caption,
                parse_mode="HTML",
                reply_markup=None
            )
        except Exception as e:
            logger.warning(f"edit_message_caption failed: {e}")
            try:
                await query.edit_message_text(text="✅ Payment approved.", reply_markup=None)
            except Exception:
                # Last resort: just remove buttons
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"cb_approve error: {e}")
        await query.answer("Error approving. Try again.", show_alert=True)
    return MAIN_MENU


async def cb_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.answer("⛔ Access denied.", show_alert=True)
        return

    await query.answer("Processing…")
    payment_id = query.data.split("_", 2)[2]

    try:
        res = supabase.table("payments").select("*").eq("id", payment_id).single().execute()
        payment = res.data
        if not payment:
            await query.edit_message_caption("❌ Payment not found.")
            return MAIN_MENU
        if payment["status"] != "pending":
            await query.answer(f"Already {payment['status']}.", show_alert=True)
            return MAIN_MENU

        supabase.table("payments").update({
            "status": "rejected",
            "updated_at": datetime.datetime.utcnow().isoformat(),
        }).eq("id", payment_id).execute()

        try:
            await context.bot.send_message(
                chat_id=payment["user_id"],
                text=(
                    "❌ <b>Payment Rejected</b>\n\n"
                    "We could not verify your payment screenshot.\n"
                    "Please send a clear screenshot and try again with /start."
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

        try:
            # Clear buttons and update caption on admin side
            new_caption = (query.message.caption or "") + "\n\n❌ <b>REJECTED</b>"
            await query.edit_message_caption(
                caption=new_caption,
                parse_mode="HTML",
                reply_markup=None
            )
        except Exception as e:
            logger.warning(f"edit_message_caption failed: {e}")
            try:
                await query.edit_message_text(text="❌ Payment rejected.", reply_markup=None)
            except Exception:
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"cb_reject error: {e}")
        await query.answer("Error rejecting. Try again.", show_alert=True)
    return MAIN_MENU


# ── Broadcast ──────────────────────────────────────────────────────────────────

async def cb_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        total_u = supabase.table("bot_users").select("user_id", count="exact").eq("bot_id", BOT_ID).execute().count or 0
        total_p = supabase.table("payments").select("user_id", count="exact").eq("bot_id", BOT_ID).execute().count or 0
        total_users = max(total_u, total_p)
    except Exception:
        total_users = "?"

    try:
        await update.callback_query.edit_message_text(
            f"📢 <b>Broadcast Message</b>\n\n"
            f"👥 Approx. recipients: <b>{total_users}+</b>\n\n"
            "Send the message you want to broadcast.\n"
            "HTML formatting supported.\n\n"
            "Send /cancel to abort.",
            reply_markup=_back_kb(),
            parse_mode="HTML"
        )
    except Exception:
        pass
    return AWAIT_BROADCAST


async def recv_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text and text.strip() == "/cancel":
        await update.message.reply_text("📢 Broadcast cancelled.")
        return ConversationHandler.END

    try:
        rows_u = (supabase.table("bot_users").select("user_id, username")
                  .eq("bot_id", BOT_ID).execute()).data or []
        rows_p = (supabase.table("payments").select("user_id, username")
                  .eq("bot_id", BOT_ID).execute()).data or []
        all_rows = rows_u + rows_p
    except Exception as e:
        logger.error(f"Broadcast fetch error: {e}")
        await update.message.reply_text("❌ Failed to fetch users. Please try again.")
        return ConversationHandler.END

    seen = {}
    for r in all_rows:
        seen[r["user_id"]] = r.get("username", str(r["user_id"]))

    # Add admins
    try:
        raw = get_config("extra_admins", "")
        for x in (raw or "").split(","):
            if x.strip().isdigit():
                uid = int(x.strip())
                if uid not in seen:
                    seen[uid] = str(uid)
    except Exception:
        pass
    for owner_id in _owner_ids():
        if owner_id and owner_id not in seen and owner_id != 0:
            seen[owner_id] = "Admin"

    user_ids = list(seen.keys())
    total = len(user_ids)

    if total == 0:
        await update.message.reply_text("❌ No users to broadcast to.")
        return ConversationHandler.END

    status_msg = await update.message.reply_text(
        f"📢 <b>Broadcasting…</b>\n\n👥 Total: <b>{total}</b>",
        parse_mode="HTML"
    )

    sent = failed = blocked = 0
    for i, uid in enumerate(user_ids, 1):
        try:
            await context.bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "forbidden" in err or "deactivated" in err:
                blocked += 1
            else:
                failed += 1

        if i % 20 == 0:
            try:
                await status_msg.edit_text(
                    f"📢 <b>Broadcasting…</b>\n\n"
                    f"Progress: {i}/{total}\n"
                    f"✅ Sent: {sent}  ❌ Blocked: {blocked}  ⚠️ Failed: {failed}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await asyncio.sleep(0.05)

    try:
        await status_msg.edit_text(
            f"📢 <b>Broadcast Complete!</b>\n\n"
            f"👥 Total: {total}\n"
            f"✅ Sent: {sent}\n"
            f"🚫 Blocked: {blocked}\n"
            f"⚠️ Failed: {failed}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    return ConversationHandler.END


# ── Admin Control ──────────────────────────────────────────────────────────────

async def cb_admin_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if update.effective_user.id not in _owner_ids():
        await update.callback_query.answer("⛔ Only owners can manage admins.", show_alert=True)
        return MAIN_MENU

    raw = get_config("extra_admins", "")
    extra_ids = [x.strip() for x in raw.split(",") if x.strip().isdigit()] if raw else []

    lines = [f"👤 <b>Admin Control</b>\n"]
    lines.append(f"<b>Owners:</b> {', '.join(f'<code>{x}</code>' for x in _owner_ids())}\n")
    if extra_ids:
        lines.append("<b>Extra Admins:</b>")
        for uid in extra_ids:
            lines.append(f"  • <code>{uid}</code>")
    else:
        lines.append("<b>Extra Admins:</b> None")

    buttons = []
    for uid in extra_ids:
        buttons.append([InlineKeyboardButton(f"🗑 Remove {uid}", callback_data=f"mgr_rm_admin_{uid}")])
    buttons.append([InlineKeyboardButton("➕ Add Admin", callback_data="mgr_add_admin")])
    buttons.append([InlineKeyboardButton("⬅️ Back",      callback_data="mgr_main")])

    try:
        await update.callback_query.edit_message_text(
            "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML"
        )
    except Exception:
        pass
    return MAIN_MENU


async def cb_rm_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if update.effective_user.id not in _owner_ids():
        return MAIN_MENU
    uid_to_remove = update.callback_query.data.replace("mgr_rm_admin_", "")
    raw = get_config("extra_admins", "")
    ids = [x.strip() for x in raw.split(",") if x.strip().isdigit() and x.strip() != uid_to_remove]
    set_config("extra_admins", ",".join(ids))
    await cb_admin_control(update, context)
    return MAIN_MENU


async def cb_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if update.effective_user.id not in _owner_ids():
        return MAIN_MENU
    try:
        await update.callback_query.edit_message_text(
            "👤 <b>Add Admin</b>\n\nSend the Telegram <b>User ID</b> of the new admin.",
            reply_markup=_back_kb("mgr_admin_control"), parse_mode="HTML"
        )
    except Exception:
        pass
    return AWAIT_ADD_ADMIN


async def recv_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid_text = (update.message.text or "").strip()
    if not uid_text.isdigit():
        await update.message.reply_text("❌ Please send a valid numeric Telegram User ID.")
        return AWAIT_ADD_ADMIN
    raw = get_config("extra_admins", "")
    ids = [x.strip() for x in raw.split(",") if x.strip().isdigit()] if raw else []
    if uid_text not in ids:
        ids.append(uid_text)
        set_config("extra_admins", ",".join(ids))
    await update.message.reply_text(f"✅ Admin <code>{uid_text}</code> added!", parse_mode="HTML")
    return ConversationHandler.END


# ── Settings ───────────────────────────────────────────────────────────────────

SETTINGS_KEYS = {
    "mgr_set_welcome_text":      ("welcome_text",              "Welcome message text"),
    "mgr_set_welcome_media":     ("welcome_media_url",         "Welcome photo URL"),
    "mgr_set_premium_text":      ("premium_text",              "Premium section text"),
    "mgr_set_premium_photo":     ("premium_photo_url",         "Premium photo URL"),
    "mgr_set_upi_msg":           ("upi_message",               "UPI payment message"),
    "mgr_set_upi_qr":            ("upi_qr_url",                "UPI QR image URL"),
    "mgr_set_crypto_msg":        ("crypto_message",            "Crypto payment message"),
    "mgr_set_crypto_qr":         ("crypto_qr_url",             "Crypto QR image URL"),
    "mgr_set_confirm_msg":       ("payment_confirmed_message", "Payment confirmed message"),
    "mgr_set_demo_url":          ("demo_button_url",           "Demo button URL"),
    "mgr_set_howto_url":         ("how_to_use_button_url",     "How To Use button URL"),
}


async def cb_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Welcome Text",    callback_data="mgr_set_welcome_text"),
         InlineKeyboardButton("🖼 Welcome Photo",   callback_data="mgr_set_welcome_media")],
        [InlineKeyboardButton("💎 Premium Text",    callback_data="mgr_set_premium_text"),
         InlineKeyboardButton("🖼 Premium Photo",   callback_data="mgr_set_premium_photo")],
        [InlineKeyboardButton("💳 UPI Message",     callback_data="mgr_set_upi_msg"),
         InlineKeyboardButton("🖼 UPI QR",          callback_data="mgr_set_upi_qr")],
        [InlineKeyboardButton("₿ Crypto Message",   callback_data="mgr_set_crypto_msg"),
         InlineKeyboardButton("🖼 Crypto QR",       callback_data="mgr_set_crypto_qr")],
        [InlineKeyboardButton("✅ Confirm Message",  callback_data="mgr_set_confirm_msg")],
        [InlineKeyboardButton("🎥 Demo URL",        callback_data="mgr_set_demo_url"),
         InlineKeyboardButton("📖 HowTo URL",       callback_data="mgr_set_howto_url")],
        [InlineKeyboardButton("⬅️ Back",            callback_data="mgr_main")],
    ])
    try:
        await update.callback_query.edit_message_text(
            "⚙️ <b>Settings</b>\n\nChoose what to edit:",
            reply_markup=kb, parse_mode="HTML"
        )
    except Exception:
        pass
    return MAIN_MENU


async def cb_setting_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cbd = update.callback_query.data
    key, label = SETTINGS_KEYS[cbd]
    context.user_data["setting_key"] = key
    context.user_data["setting_label"] = label
    current = get_config(key, "(not set)")
    try:
        await update.callback_query.edit_message_text(
            f"⚙️ <b>{label}</b>\n\n"
            f"Current: <code>{current[:200]}</code>\n\n"
            "Send the new value (or /cancel to abort):",
            reply_markup=_back_kb("mgr_settings"), parse_mode="HTML"
        )
    except Exception:
        pass
    return AWAIT_SETTING


async def recv_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "/cancel":
        await update.message.reply_text("Cancelled.")
        return ConversationHandler.END
    key   = context.user_data.get("setting_key")
    label = context.user_data.get("setting_label", key)
    if not key:
        return ConversationHandler.END
    set_config(key, text)
    await update.message.reply_text(f"✅ <b>{label}</b> updated!", parse_mode="HTML")
    context.user_data.clear()
    return ConversationHandler.END


# ── Join Link ──────────────────────────────────────────────────────────────────

async def cb_join_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    current = get_config("join_link", "(not set)")
    try:
        await update.callback_query.edit_message_text(
            f"🔗 <b>Join Link</b>\n\nCurrent: <code>{current}</code>\n\n"
            "Send the new join link (URL or @username), or /cancel to abort.",
            reply_markup=_back_kb(), parse_mode="HTML"
        )
    except Exception:
        pass
    return AWAIT_JOIN_LINK


async def recv_join_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "/cancel":
        await update.message.reply_text("Cancelled.")
        return ConversationHandler.END
    if text.startswith("@"):
        text = f"https://t.me/{text[1:]}"
    elif not text.startswith(("http://", "https://")):
        text = f"https://{text}"
    set_config("join_link", text)
    await update.message.reply_text(f"✅ Join link updated to:\n{text}")
    return ConversationHandler.END


# ── ConversationHandler builder ────────────────────────────────────────────────

def build_manage_handler() -> ConversationHandler:
    setting_patterns = "|".join(SETTINGS_KEYS.keys())

    return ConversationHandler(
        entry_points=[CommandHandler("manage", manage_command)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(cb_main,           pattern="^mgr_main$"),
                CallbackQueryHandler(cb_stats,          pattern="^mgr_stats$"),
                CallbackQueryHandler(cb_users,          pattern="^mgr_users$"),
                CallbackQueryHandler(cb_users_all,      pattern="^mgr_users_all$"),
                CallbackQueryHandler(cb_users_approved, pattern="^mgr_users_approved$"),
                CallbackQueryHandler(cb_payments,       pattern="^mgr_payments$"),
                CallbackQueryHandler(cb_approve,        pattern="^mgr_approve_.+$"),
                CallbackQueryHandler(cb_reject,         pattern="^mgr_reject_.+$"),
                CallbackQueryHandler(cb_broadcast,      pattern="^mgr_broadcast$"),
                CallbackQueryHandler(cb_admin_control,  pattern="^mgr_admin_control$"),
                CallbackQueryHandler(cb_rm_admin,       pattern="^mgr_rm_admin_.+$"),
                CallbackQueryHandler(cb_add_admin,      pattern="^mgr_add_admin$"),
                CallbackQueryHandler(cb_settings,       pattern="^mgr_settings$"),
                CallbackQueryHandler(cb_setting_select, pattern=f"^({setting_patterns})$"),
                CallbackQueryHandler(cb_join_link,      pattern="^mgr_join_link$"),
            ],
            AWAIT_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recv_broadcast),
                CommandHandler("cancel", lambda u, c: ConversationHandler.END),
            ],
            AWAIT_SETTING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recv_setting),
                CommandHandler("cancel", lambda u, c: ConversationHandler.END),
            ],
            AWAIT_ADD_ADMIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recv_add_admin),
            ],
            AWAIT_JOIN_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recv_join_link),
                CommandHandler("cancel", lambda u, c: ConversationHandler.END),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )
