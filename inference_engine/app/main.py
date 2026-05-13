import json
import logging
import signal
import sys
import time

from kafka import KafkaConsumer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from models import Review
from inference import ReviewAnalyzer


# ----------------------------
# CONFIG
# ----------------------------

DATABASE_URL = "postgresql+psycopg2://root:root_password@postgres:5432/app_db"
KAFKA_BROKER = "kafka:9092"
TOPIC = "reviews"

RATE_LIMIT_DELAY = 5  # 👈 prevents Groq 429

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logging.info("Consumer starting...")


# ----------------------------
# DB SETUP
# ----------------------------

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)


# ----------------------------
# KAFKA CONSUMER
# ----------------------------

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    group_id="reviews-consumer",
    auto_offset_reset="earliest",
    enable_auto_commit=False,
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)


# ----------------------------
# SHUTDOWN
# ----------------------------

def shutdown(sig, frame):
    logging.warning("Shutdown signal received")
    try:
        consumer.close()
    finally:
        sys.exit(0)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


# ----------------------------
# PROCESS SINGLE MESSAGE
# ----------------------------

def process_message(msg, inference, db):
    review = msg.value

    review_text = review.get("review_text", "")

    # ----------------------------
    # AI inference (RATE LIMITED)
    # ----------------------------
    if review_text:
        result = inference.inference(review_text)

        review["overall_sentiment"] = result.get("overall_sentiment", "")
        review["aspects"] = result.get("aspects", [])
        review["main_complaint"] = result.get("main_complaint", "")
        review["summary"] = result.get("summary", "")

    # ----------------------------
    # UPSERT
    # ----------------------------
    stmt = insert(Review).values(review)

    update_dict = {
        c.name: getattr(stmt.excluded, c.name)
        for c in Review.__table__.columns
        if c.name != "id"
    }

    stmt = stmt.on_conflict_do_update(
        index_elements=["review_id"],
        set_=update_dict
    )

    db.execute(stmt)
    db.commit()


# ----------------------------
# MAIN LOOP (STREAMING)
# ----------------------------

def main():
    logging.info("Consumer loop started")

    inference = ReviewAnalyzer()
    db = SessionLocal()

    try:
        for msg in consumer:

            try:
                logging.info(f"Processing message: {msg.value.get('review_id')}")

                process_message(msg, inference, db)

                consumer.commit()

                # ----------------------------
                # RATE LIMIT SAFETY
                # ----------------------------
                time.sleep(RATE_LIMIT_DELAY)

            except Exception as e:
                logging.error(f"Message failed: {e}")
                db.rollback()

    finally:
        db.close()
        consumer.close()


# ----------------------------
# ENTRY POINT
# ----------------------------

if __name__ == "__main__":
    main()