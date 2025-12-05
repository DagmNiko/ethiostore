"""
Django management command to set up Telegram webhook
"""
import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from aiogram import Bot
from utils.logger import logger


class Command(BaseCommand):
    help = 'Set up Telegram webhook URL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='Webhook URL (e.g., https://yourdomain.com/webhook/telegram/)',
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove webhook (switch back to polling)',
        )

    def handle(self, *args, **options):
        asyncio.run(self.setup_webhook(options))

    async def setup_webhook(self, options):
        bot = Bot(token=settings.BOT_TOKEN)
        
        try:
            if options['remove']:
                # Remove webhook
                result = await bot.delete_webhook(drop_pending_updates=True)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Webhook removed: {result}')
                )
                logger.info("Webhook removed successfully")
            else:
                # Set webhook
                webhook_url = options.get('url') or settings.WEBHOOK_URL
                
                if not webhook_url:
                    self.stdout.write(
                        self.style.ERROR('❌ Webhook URL not provided. Use --url or set WEBHOOK_URL in settings.')
                    )
                    return
                
                # Set webhook
                result = await bot.set_webhook(
                    url=webhook_url,
                    secret_token=settings.WEBHOOK_SECRET if hasattr(settings, 'WEBHOOK_SECRET') else None,
                    drop_pending_updates=True
                )
                
                # Get webhook info
                webhook_info = await bot.get_webhook_info()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Webhook set successfully!')
                )
                self.stdout.write(f'   URL: {webhook_info.url}')
                self.stdout.write(f'   Pending updates: {webhook_info.pending_update_count}')
                logger.info(f"Webhook set to: {webhook_url}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error setting webhook: {e}')
            )
            logger.error(f"Error setting webhook: {e}", exc_info=True)
        finally:
            await bot.session.close()

