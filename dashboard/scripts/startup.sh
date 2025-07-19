version: '3.8'

services:
  dashboard:
    build: .
    volumes:
      - ./dashboard:/app/dashboard
    working_dir: /app
    ports:
      - "8501:8501"
    environment:
      - PORT=8501
    command: ["./scripts/startup.sh"]