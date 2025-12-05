"""
Django management command to set up Telegram webhook for localhost using ngrok
"""
import asyncio
import subprocess
import time
try:
    import requests
except ImportError:
    requests = None
from django.core.management.base import BaseCommand
from django.conf import settings
from aiogram import Bot
from utils.logger import logger


class Command(BaseCommand):
    help = 'Set up Telegram webhook for localhost using ngrok'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Local port (default: 8000)',
        )
        parser.add_argument(
            '--ngrok-port',
            type=int,
            default=4040,
            help='Ngrok web interface port (default: 4040)',
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove webhook (switch back to polling)',
        )

    def handle(self, *args, **options):
        if options['remove']:
            asyncio.run(self.remove_webhook())
        else:
            self.setup_local_webhook(options)

    def get_ngrok_url(self, ngrok_port=4040):
        """Get the public URL from ngrok"""
        if requests is None:
            self.stdout.write(self.style.WARNING(
                '⚠️  requests library not installed. Install it with: pip install requests'
            ))
            return None
        
        try:
            response = requests.get(f'http://localhost:{ngrok_port}/api/tunnels', timeout=2)
            if response.status_code == 200:
                tunnels = response.json().get('tunnels', [])
                for tunnel in tunnels:
                    if tunnel.get('proto') == 'https':
                        return tunnel.get('public_url')
                # Fallback to http if https not available
                for tunnel in tunnels:
                    if tunnel.get('proto') == 'http':
                        return tunnel.get('public_url')
        except Exception as e:
            logger.error(f"Error getting ngrok URL: {e}")
        return None

    def setup_local_webhook(self, options):
        """Set up webhook using ngrok"""
        port = options['port']
        ngrok_port = options['ngrok_port']
        
        self.stdout.write(self.style.WARNING(
            '\n⚠️  Setting up webhook for localhost requires ngrok or similar tunneling service.\n'
        ))
        
        # Check if ngrok is running
        ngrok_url = self.get_ngrok_url(ngrok_port)
        
        if not ngrok_url:
            self.stdout.write(self.style.ERROR(
                '❌ Ngrok is not running or not accessible.\n'
            ))
            self.stdout.write(
                '📝 To set up ngrok:\n'
                '   1. Install ngrok: https://ngrok.com/download\n'
                f'   2. Run: ngrok http {port}\n'
                '   3. Then run this command again\n\n'
                '   Or use an alternative like:\n'
                '   - localtunnel: npx localtunnel --port 8000\n'
                '   - cloudflared: cloudflared tunnel --url http://localhost:8000\n'
            )
            return
        
        # Ensure ngrok URL ends with /
        if not ngrok_url.endswith('/'):
            ngrok_url += '/'
        
        webhook_url = f"{ngrok_url}webhook/telegram/"
        
        self.stdout.write(self.style.SUCCESS(f'✅ Found ngrok URL: {ngrok_url}'))
        self.stdout.write(f'   Webhook URL: {webhook_url}\n')
        
        # Set webhook
        asyncio.run(self.set_webhook(webhook_url))

    async def set_webhook(self, webhook_url):
        """Set the webhook URL"""
        bot = Bot(token=settings.BOT_TOKEN)
        
        try:
            result = await bot.set_webhook(
                url=webhook_url,
                secret_token=settings.WEBHOOK_SECRET if hasattr(settings, 'WEBHOOK_SECRET') else None,
                drop_pending_updates=True
            )
            
            # Get webhook info
            webhook_info = await bot.get_webhook_info()
            
            self.stdout.write(self.style.SUCCESS('✅ Webhook set successfully!'))
            self.stdout.write(f'   URL: {webhook_info.url}')
            self.stdout.write(f'   Pending updates: {webhook_info.pending_update_count}')
            self.stdout.write(
                '\n💡 Make sure your Django server is running:\n'
                '   python manage.py runserver\n'
            )
            logger.info(f"Webhook set to: {webhook_url}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error setting webhook: {e}')
            )
            logger.error(f"Error setting webhook: {e}", exc_info=True)
        finally:
            await bot.session.close()

    async def remove_webhook(self):
        """Remove webhook"""
        bot = Bot(token=settings.BOT_TOKEN)
        
        try:
            result = await bot.delete_webhook(drop_pending_updates=True)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Webhook removed: {result}')
            )
            logger.info("Webhook removed successfully")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error removing webhook: {e}')
            )
            logger.error(f"Error removing webhook: {e}", exc_info=True)
        finally:
            await bot.session.close()

