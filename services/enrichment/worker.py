import json
import os
from typing import Any

from confluent_kafka import Consumer, Producer, KafkaError

from utils.analysis_engines import build_unified_analysis

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
RAW_TOPIC = os.getenv("RAW_MARKET_DATA_TOPIC", "raw-market-data")
ENRICHED_TOPIC = os.getenv("ENRICHED_TOPIC", "enriched-analysis-payloads")
GROUP_ID = os.getenv("ENRICHMENT_GROUP", "analysis-enrichment")


def main() -> None:
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
        }
    )
    producer = Producer({"bootstrap.servers": KAFKA_BROKER})
    consumer.subscribe([RAW_TOPIC])

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(msg.error())
                    break
            tick: Any = json.loads(msg.value().decode("utf-8"))
            try:
                payload = build_unified_analysis(tick)
                producer.produce(ENRICHED_TOPIC, value=payload.model_dump_json())
            except Exception as e:
                print(f"analysis error: {e}")
            consumer.commit(msg)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        producer.flush()


if __name__ == "__main__":
    main()
