FROM python:3.11-slim
WORKDIR /app
COPY services/pulse_discord_bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY pulse_discord_bot.py ./pulse_discord_bot.py
CMD ["python", "pulse_discord_bot.py"]
