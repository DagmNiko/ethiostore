"""
Custom middleware for ethiostore project
"""
import os
import re
from django.conf import settings
from django.middleware.common import CommonMiddleware
from django.http import HttpRequest


class NgrokHostMiddleware(CommonMiddleware):
    """
    Middleware to allow ngrok domains in DEBUG mode.
    This extends CommonMiddleware to allow ngrok domains without needing to
    update ALLOWED_HOSTS every time the ngrok domain changes.
    """
    def __init__(self, get_response):
        super().__init__(get_response)
        # Pattern to match ngrok domains
        self.ngrok_pattern = re.compile(r'.*\.ngrok-free\.dev$|.*\.ngrok\.io$|.*\.ngrok-free\.app$')

    def process_request(self, request):
        # Allow ngrok in DEBUG mode OR when explicitly enabled via env var
        # This allows webhook testing even when DEBUG=False
        allow_ngrok = settings.DEBUG or os.getenv('ALLOW_NGROK', 'False').lower() == 'true'
        
        if allow_ngrok:
            # Extract host from headers before get_host() validates it
            host_header = request.META.get('HTTP_HOST', '')
            if not host_header:
                # Fallback to SERVER_NAME if HTTP_HOST is not available
                host_header = request.META.get('SERVER_NAME', '')
            
            # Remove port if present
            host = host_header.split(':')[0] if host_header else ''
            
            # Check if it's an ngrok domain and not already in ALLOWED_HOSTS
            if host and self.ngrok_pattern.match(host) and host not in settings.ALLOWED_HOSTS:
                # Add to allowed hosts before validation
                settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + [host]
        
        # Call parent's process_request which does the host validation
        return super().process_request(request)

