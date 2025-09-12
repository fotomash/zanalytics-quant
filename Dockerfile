FROM python:3.11-slim

WORKDIR /app

ARG INSTALL_DEV=false

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install --no-cache-dir -r requirements/dev.txt -r requirements/optional.txt; fi

COPY . .

CMD ["python", "services/tick_to_bar.py"]
