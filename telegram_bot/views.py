"""
Django views for Telegram Bot webhook
"""
import json
import asyncio
import importlib
from contextlib import suppress
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from utils.logger import logger

# Global bot and dispatcher instances (singletons for the process)
bot = None
dp = None

async def _safe_feed_update(bot_instance, dp_instance, update):
    """Run dp.feed_update with graceful handling of closed-loop errors."""
    try:
        await dp_instance.feed_update(bot_instance, update)
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            logger.warning("Skipping update due to closed event loop (likely during reload/shutdown)")
        else:
            raise
    except Exception as e:
        # Re-raise non-loop errors so they are logged as usual
        raise

ROUTER_MODULES = [
    "features.onboarding",
    "features.products",
    "features.inline_search",
    "features.engagement",
    "features.scheduler",
]


def build_dispatcher():
    from aiogram import Dispatcher

    dispatcher = Dispatcher()
    for module_path in ROUTER_MODULES:
        module = importlib.import_module(module_path)
        module = importlib.reload(module)
        dispatcher.include_router(module.router)

    return dispatcher


async def _cleanup_bot():
    """Close the global bot session if it exists."""
    global bot
    if bot is not None:
        try:
            await bot.session.close()
            logger.info("✅ Previous bot session closed")
        except Exception as e:
            logger.warning(f"Could not close previous bot session: {e}")
        finally:
            bot = None

async def init_bot():
    """Initialize bot and dispatcher once and reuse them across webhook requests."""
    global bot, dp

    # If we've already created the bot/dispatcher in this process, just reuse them.
    if bot is not None and dp is not None:
        return bot, dp

    # Clean up any previous session (helps during Django reloads)
    await _cleanup_bot()

    try:
        from aiogram import Bot as AiogramBot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
    except ImportError:  # pragma: no cover
        logger.error("aiogram not installed. Please install it: pip install aiogram>=3.0.0")
        raise

    bot = AiogramBot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    dp = build_dispatcher()

    logger.info("✅ Bot and dispatcher initialized for webhook")

    return bot, dp


@csrf_exempt
@require_POST
async def telegram_webhook(request):
    """
    Handle Telegram webhook updates (async view)
    """
    try:
        # Initialize bot if not already done
        bot_instance, dp_instance = await init_bot()
        
        # Parse update from request body
        # request.body is a property (bytes), not a method, so no await or parentheses
        body = request.body
        # json.loads can handle bytes directly in Python 3.6+
        update_dict = json.loads(body)
        from aiogram.types import Update
        
        # Use model_validate for aiogram 3.x (Pydantic v2)
        try:
            update = Update.model_validate(update_dict)
        except AttributeError:
            # Fallback for older aiogram versions
            update = Update(**update_dict)
        
        # Process update asynchronously (safe against closed-loop errors)
        try:
            await _safe_feed_update(bot_instance, dp_instance, update)
        except Exception as e:
            logger.error(f"Error processing update: {e}", exc_info=True)
        
        return JsonResponse({"ok": True})
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook request")
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error in webhook handler: {e}", exc_info=True)
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

