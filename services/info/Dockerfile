FROM python:3.12-slim

WORKDIR /app

# Copy docs and dashboards if available
COPY docs /tmp/docs
COPY dashboards /tmp/dashboards

ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir streamlit==1.37.1 markdown==3.6

# Move optional content into place
RUN if [ -d /tmp/docs/wiki ]; then mv /tmp/docs/wiki /app/wiki; fi \
    && if [ -d /tmp/dashboards/info ]; then mkdir -p /app/dashboards && mv /tmp/dashboards/info /app/dashboards/info; fi

CMD ["streamlit", "run", "/app/dashboards/info/main.py", "--server.port=${WIKI_DASHBOARD_PORT}", "--server.address=0.0.0.0"]
