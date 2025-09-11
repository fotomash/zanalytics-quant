FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# The mcp2 service dependencies are handled in its own image, so we do not
# need to copy or install them here.
# COPY services/mcp2/requirements.txt services/mcp2/
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "services/tick_to_bar.py"]
