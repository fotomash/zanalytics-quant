import os
from pathlib import Path
from typing import Any, Dict

from confluent_kafka import Consumer, Producer

from core.session_journal import SessionJournal

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
RAW_TOPIC = os.getenv("RAW_MARKET_DATA_TOPIC", "raw-market-data")
ENRICHED_TOPIC = os.getenv("ENRICHED_TOPIC", "enriched-analysis-payloads")
GROUP_ID = os.getenv("ENRICHMENT_GROUP", "analysis-enrichment")


def on_init(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Set up Kafka consumer/producer for the enrichment service."""
    topics = manifest.get("topics", {})
    consume_topics = topics.get("consume", [RAW_TOPIC])
    produce_topic = topics.get("produce", ENRICHED_TOPIC)
    instrument_pair = manifest.get("instrument_pair")
    timeframe = manifest.get("timeframe")

    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
        }
    )
    producer = Producer({"bootstrap.servers": KAFKA_BROKER})
    consumer.subscribe(consume_topics)
    journal = SessionJournal(Path("session_journal.json"))
    return {
        "consumer": consumer,
        "producer": producer,
        "enriched_topic": produce_topic,
        "instrument_pair": instrument_pair,
        "timeframe": timeframe,
        "journal": journal,
    }
