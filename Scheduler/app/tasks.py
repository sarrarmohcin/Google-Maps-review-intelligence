from celery import Celery
from celery.schedules import crontab
import asyncio

from scraper.extractor import ReviewsExtractor
from orm.connection import SessionLocal
from orm.models import Place

import os
os.environ["DISPLAY"] = ":99"

app = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

app.conf.timezone = "UTC"


# ----------------------------
# SCHEDULE
# ----------------------------
app.conf.beat_schedule = {
    "run-every-hour": {
        "task": "tasks.review_collection",
        "schedule": crontab(hour="*", minute=0),
    },
}


# ----------------------------
# DB
# ----------------------------
def get_places(db):
    return db.query(Place).all()


# ----------------------------
# TASK
# ----------------------------
@app.task
def review_collection():

    db = SessionLocal()

    try:
        print("Starting review collection task...")
        places = get_places(db)

        for place in places:

            extractor = ReviewsExtractor(
                place.id,
                place.url
            )

            # run async safely
            asyncio.run(extractor.main())

    except Exception as e:
        print(f"Error in review_collection: {e}")

    finally:
        db.close()
        
        
review_collection.delay()    