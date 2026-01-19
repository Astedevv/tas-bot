#!/bin/sh
echo "--- entrypoint debug start ---"
echo "WORKDIR: $(pwd)"
echo "/app contents:"
ls -la /app || true
echo "/app/bot contents:"
ls -la /app/bot || true
echo "/app/bot/cogs contents:"
ls -la /app/bot/cogs || true
echo "BOT_TOKEN set: ${BOT_TOKEN:+yes}${BOT_TOKEN:+'yes'}"
if [ -n "$BOT_TOKEN" ]; then
  echo "BOT_TOKEN present"
else
  echo "BOT_TOKEN not present"
fi
if [ -n "$DATABASE_URL" ]; then
  echo "DATABASE_URL present"
else
  echo "DATABASE_URL not present"
fi
echo "--- starting bot ---"
cd /app/bot
exec python main.py
