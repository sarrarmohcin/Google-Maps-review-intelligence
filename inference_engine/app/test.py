import asyncio
import json
import os
import logging
import hashlib
import sys
import signal

from aiokafka import AIOKafkaConsumer
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s"
)

logging.warning("### consumer STARTED ###")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "192.168.50.9:19092,192.168.50.8:19092")
ES_HOST = os.getenv("ES_HOST", "https://elastic-node1.van.local:9200,https://elastic-node2.van.local:9200,https://elastic-node3.van.local:9200")

BATCH_SIZE = 100
MAX_RETRIES = 5
FLUSH_INTERVAL = 10


# ----------------------------
# Helpers
# ----------------------------

def url_to_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def clean_doc(doc):
    return {k: v for k, v in doc.items() if k != "status"}


def build_update_action(doc, index_name):
    base_doc = clean_doc(doc)
    doc_id = url_to_id(doc["url"])

    return {
        "_op_type": "update",
        "_index": index_name,
        "_id": doc_id,
        "script": {
            "lang": "painless",
            "source": """
                for (entry in params.entrySet()) {
                    ctx._source[entry.getKey()] = entry.getValue();
                }
            """,
            "params": base_doc
        },
        "upsert": {
            **base_doc,
            "status": {
                "read_at": None,
                "pinned_at": None,
                "is_permanent": False
            }
        }
    }
    
async def save_batch(es: AsyncElasticsearch, documents: list):
        
    index_name = "feeds-write"
    actions = [
        build_update_action(msg.value, index_name)
        for msg in documents
    ]

    success, errors = await async_bulk(
        es.options(request_timeout=120),
        actions,
        chunk_size=200,
        raise_on_error=False
    )
    
    await asyncio.sleep(3)

    return success, errors


async def flush(es: AsyncElasticsearch, consumer: AIOKafkaConsumer, batch: list):
    for attempt in range(MAX_RETRIES):
        try:
            success, errors = await save_batch(es, batch)
            if errors:
                raise Exception(f"Bulk errors: {errors}")
            await consumer.commit()
            logging.warning(f"Indexed and committed {len(batch)} docs")
            batch.clear()
            return
        except Exception as e:
            logging.error(f"Flush attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2)

    logging.error("Flush failed permanently, exiting")
    sys.exit(1)


# ----------------------------
# Main
# ----------------------------

async def main():

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown():
        logging.warning("Shutdown signal received")
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, _shutdown)
    loop.add_signal_handler(signal.SIGINT, _shutdown)

    # Connect to Elasticsearch
    es = AsyncElasticsearch(
        hosts=ES_HOST.split(','),
        ca_certs="/app/elasticsearch-ca.crt",
        basic_auth=("elastic", "elastic"),
        request_timeout=300,
        retry_on_timeout=True,
        max_retries=3
    )

    try:
        if not await es.ping():
            raise Exception("Elasticsearch ping failed")
        logging.warning("Connected to Elasticsearch")
    except Exception as e:
        logging.error(f"Elasticsearch connection failed: {e}")
        await es.close()
        sys.exit(1)

    # Connect to Kafka
    consumer = AIOKafkaConsumer(
        "feeds",
        bootstrap_servers=KAFKA_BROKER.split(','),
        group_id="kafka-consumer",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        max_poll_records=500,
        session_timeout_ms=30000,
        max_poll_interval_ms=900000,
    )

    try:
        await consumer.start()
        logging.warning("Connected to Kafka")
    except Exception as e:
        logging.error(f"Kafka connection failed: {e}")
        await es.close()
        sys.exit(1)

    batch = []
    last_flush = loop.time()

    try:
        logging.warning("Consumer loop started")

        async for msg in consumer:

            if stop_event.is_set():
                break

            batch.append(msg)

            now = loop.time()
            should_flush = len(batch) >= BATCH_SIZE or (batch and now - last_flush >= FLUSH_INTERVAL)

            if should_flush:
                await flush(es, consumer, batch)
                last_flush = loop.time()

    finally:
        if batch:
            logging.warning(f"Flushing remaining {len(batch)} docs before shutdown")
            await flush(es, consumer, batch)

        await consumer.stop()
        await es.close()
        logging.warning("### consumer STOPPED ###")


if __name__ == "__main__":
    asyncio.run(main())