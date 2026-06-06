import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/bot/webhook", summary="Telegram webhook handler")
async def telegram_webhook(request: Request):
    """
    Receives an incoming Telegram Update and passes it to the
    python-telegram-bot Application defined in bot.main.

    The bot Application is lazily imported so that the API can start
    even when bot.main is not yet fully implemented.
    """
    try:
        data: Dict[str, Any] = await request.json()
    except Exception as exc:
        logger.error("Failed to parse webhook payload: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        from telegram import Update
        from bot.main import application

        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return JSONResponse(content={"ok": True})

    except ImportError as exc:
        # bot.main not implemented yet — log and return 200 to avoid Telegram retries
        logger.warning("bot.main not available: %s", exc)
        return JSONResponse(content={"ok": True, "warning": "bot not initialised"})

    except Exception as exc:
        logger.error("Error processing Telegram update: %s", exc, exc_info=True)
        # Still return 200 so Telegram does not retry the same update endlessly
        return JSONResponse(
            status_code=200,
            content={"ok": False, "error": str(exc)},
        )
