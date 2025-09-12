API_PORT ?= 8080
BOT_PORT ?= 8081

up:
	docker compose up -d

down:
	docker compose down

# Tail important service logs
logs:
	docker compose logs -f django mt5 redis

# Run Django migrations (create + apply)
migrate:
	docker compose exec django python manage.py makemigrations nexus
	docker compose exec django python manage.py migrate

api:
	uvicorn services.pyrest.app:app --host 0.0.0.0 --port $(API_PORT) --reload

bot:
	python services/pulse_bot/bot.py

# Run Streamlit dashboard locally (multi-page)
dashboard:
	streamlit run app.py


# Run ML Streamlit dashboard locally
ml-dashboard:
	streamlit run dashboard/ml_dashboard.py

# Lint Python docstrings
lint-docs:
	pydocstyle src tests

