"""Healthcheck for vectorization service verifying Kafka and vector DB connectivity."""
import os
import requests
from confluent_kafka import Consumer

def main() -> None:
    brokers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    consumer = Consumer({"bootstrap.servers": brokers, "group.id": "healthcheck"})
    consumer.list_topics(timeout=5)
    consumer.close()
    url = os.environ["VECTOR_DB_URL"].rstrip("/") + "/health"
    headers = {}
    api_key = os.getenv("VECTOR_DB_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    response = requests.get(url, headers=headers, timeout=5)
    response.raise_for_status()

if __name__ == "__main__":
    main()
