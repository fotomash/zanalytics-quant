from confluent_kafka import Producer, Consumer, KafkaError
import os
import json

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPIC_TRADES = 'trades-stream'

def produce_trade(data):
    """Publish a trade event to Kafka."""
    producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
    producer.produce(TOPIC_TRADES, key=str(data['timestamp']), value=json.dumps(data))
    producer.flush()

def consume_trades(callback):
    """Consume trade events and invoke callback for each."""
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'enrichment-group',
        'auto.offset.reset': 'earliest'
    })
    consumer.subscribe([TOPIC_TRADES])
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
            data = json.loads(msg.value().decode('utf-8'))
            callback(data)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
