from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

DATABASE_URL = "postgresql+psycopg2://root:root_password@localhost:5432/app_db"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(bind=engine)


def run_query(query: str, params=None):
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=params)
    return df