#!/bin/bash
# Script to start Django server and set up webhook for localhost development

PORT=${1:-8000}
NGROK_PORT=${2:-4040}

echo "🚀 Starting Django server on port $PORT..."
echo ""

# Start Django server in background
python manage.py runserver 0.0.0.0:$PORT &
DJANGO_PID=$!

# Wait a bit for server to start
sleep 3

echo ""
echo "📡 Setting up webhook..."
echo ""

# Set up webhook (this will check for ngrok automatically)
python manage.py setup_webhook_local --port $PORT --ngrok-port $NGROK_PORT

echo ""
echo "✅ Django server is running (PID: $DJANGO_PID)"
echo "💡 To stop the server, run: kill $DJANGO_PID"
echo ""
echo "📝 To set up ngrok, run in another terminal:"
echo "   ngrok http $PORT"
echo ""
echo "   Then run: python manage.py setup_webhook_local"
echo ""

# Wait for user interrupt
wait $DJANGO_PID

