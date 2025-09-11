FROM python:3.12-slim

WORKDIR /app

# COPY docs/wiki /app/wiki
# COPY dashboards/info /app/dashboards/info

ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir streamlit==1.37.1 markdown==3.6

CMD ["streamlit", "run", "/app/dashboards/info/main.py", "--server.port=${WIKI_DASHBOARD_PORT}", "--server.address=0.0.0.0"]
