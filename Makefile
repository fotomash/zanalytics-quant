API_PORT ?= 8080
BOT_PORT ?= 8081

up:
	docker compose up -d

down:
	docker compose down

api:
	uvicorn services.pyrest.app:app --host 0.0.0.0 --port $(API_PORT) --reload

bot:
	python services/telegram/bot.py
