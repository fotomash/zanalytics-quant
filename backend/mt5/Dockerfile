tick-to-bar:
  build:
    context: .
    dockerfile: backend/django/Dockerfile
  command: python services/tick_to_bar.py
  environment:
    - REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
    - SYMBOL=EURUSD
  depends_on:
    - redis
  restart: unless-stopped