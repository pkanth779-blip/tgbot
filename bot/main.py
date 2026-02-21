import asyncio
import logging
import os
from telegram import Update
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ConversationHandler,
    MessageHandler, filters,
)
from bot.handlers.premium import (
    start_command, get_premium_callback, pay_upi_callback,
    pay_crypto_callback, back_home_callback,
)
from bot.handlers.payment import (
    paid_upi_callback, paid_crypto_callback, receive_screenshot, cancel,
    WAITING_SCREENSHOT_UPI, WAITING_SCREENSHOT_CRYPTO,
)
from bot.handlers.manage import build_manage_handler, cb_approve, cb_reject

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]


async def error_handler(update: object, context) -> None:
    err = context.error
    if isinstance(err, Conflict):
        logger.warning("Conflict: another instance polling. Retrying…")
        return
    if isinstance(err, (NetworkError, TimedOut)):
        logger.warning(f"Network issue: {err}. Auto-retrying…")
        return
    logger.error(f"Handler error: {err}", exc_info=err)


def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(error_handler)

    payment_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(paid_upi_callback,    pattern="^paid_upi$"),
            CallbackQueryHandler(paid_crypto_callback, pattern="^paid_crypto$"),
        ],
        states={
            WAITING_SCREENSHOT_UPI:    [MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_screenshot)],
            WAITING_SCREENSHOT_CRYPTO: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_screenshot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(build_manage_handler())
    app.add_handler(CallbackQueryHandler(cb_approve, pattern="^mgr_approve_.+$"))
    app.add_handler(CallbackQueryHandler(cb_reject,  pattern="^mgr_reject_.+$"))
    app.add_handler(payment_conv)
    app.add_handler(CallbackQueryHandler(get_premium_callback,  pattern="^get_premium$"))
    app.add_handler(CallbackQueryHandler(pay_upi_callback,      pattern="^pay_upi$"))
    app.add_handler(CallbackQueryHandler(pay_crypto_callback,   pattern="^pay_crypto$"))
    app.add_handler(CallbackQueryHandler(back_home_callback,    pattern="^back_home$"))
    return app


async def main():
    RETRY_DELAY = 15

    while True:
        app = None
        try:
            logger.info("Starting bot…")
            app = build_app()
            await app.initialize()

            # Clear any stale webhook / previous polling session
            try:
                await app.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Webhook cleared.")
            except Exception as e:
                logger.warning(f"delete_webhook failed (non-fatal): {e}")

            await app.start()
            await app.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
            )
            logger.info("✅ Bot running!")
            await asyncio.Event().wait()

        except Conflict:
            logger.warning(f"Conflict — another instance running. Waiting {RETRY_DELAY}s…")
            await asyncio.sleep(RETRY_DELAY)

        except (NetworkError, TimedOut) as e:
            logger.warning(f"Network error: {e}. Retrying in {RETRY_DELAY}s…")
            await asyncio.sleep(RETRY_DELAY)

        except Exception as e:
            logger.error(f"Crash: {e}. Restarting in {RETRY_DELAY}s…")
            await asyncio.sleep(RETRY_DELAY)

        finally:
            if app:
                try:
                    if app.updater and app.updater.running:
                        await app.updater.stop()
                    if app.running:
                        await app.stop()
                    await app.shutdown()
                except Exception:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
