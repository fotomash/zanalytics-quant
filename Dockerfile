FROM python:3.11-slim

WORKDIR /app

COPY requirements/base.txt requirements/prod.txt requirements/
RUN pip install --no-cache-dir -r requirements/base.txt -r requirements/prod.txt

ARG INCLUDE_DEV=false

COPY . .

RUN if [ "$INCLUDE_DEV" = "true" ]; then pip install --no-cache-dir -r requirements/dev.txt; fi

CMD ["python", "services/tick_to_bar.py"]
