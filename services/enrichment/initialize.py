import os
from typing import Any, Dict

from confluent_kafka import Consumer, Producer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
RAW_TOPIC = os.getenv("RAW_MARKET_DATA_TOPIC", "raw-market-data")
ENRICHED_TOPIC = os.getenv("ENRICHED_TOPIC", "enriched-analysis-payloads")
GROUP_ID = os.getenv("ENRICHMENT_GROUP", "analysis-enrichment")


def on_init() -> Dict[str, Any]:
    """Set up Kafka consumer/producer for the enrichment service."""
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
        }
    )
    producer = Producer({"bootstrap.servers": KAFKA_BROKER})
    consumer.subscribe([RAW_TOPIC])
    return {
        "consumer": consumer,
        "producer": producer,
        "enriched_topic": ENRICHED_TOPIC,
    }
