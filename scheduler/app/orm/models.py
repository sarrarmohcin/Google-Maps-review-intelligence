from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    TIMESTAMP,
    VARCHAR
)

from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import declarative_base

from sqlalchemy.sql import func


Base = declarative_base()


class Review(Base):
    __tablename__ = "gm_reviews"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    business_id = Column(BigInteger, nullable=False)

    review_id = Column(Text, unique=True, nullable=False)

    reviewer_name = Column(Text)

    reviewer_url = Column(Text)

    reviewer_avatar = Column(Text)

    reviewer_id = Column(Text)

    reviewer_review_count = Column(Integer)

    reviewer_is_local_guide = Column(
        Boolean,
        default=False
    )

    review_rating = Column(
        SmallInteger,
        nullable=False
    )

    review_text = Column(Text)

    review_date = Column(TIMESTAMP(timezone=True))

    review_language = Column(VARCHAR(10))

    owner_reply = Column(Text)

    owner_reply_date = Column(TIMESTAMP(timezone=True))

    overall_sentiment = Column(VARCHAR(20))

    aspects = Column(JSONB)

    main_complaint = Column(Text)

    summary = Column(Text)

    scraped_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self):
        return f"<GMReview(id={self.id}, review_id={self.review_id})>"


class Place(Base):
    __tablename__ = "places"

    id = Column(BigInteger, primary_key=True)

    url = Column(Text, nullable=False)
    
    name = Column(Text, nullable=False)

    rating = Column(
        Numeric(3, 2),
        nullable=False,
        default=0
    )

    reviews = Column(
        Integer,
        nullable=False,
        default=0
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    def __repr__(self):
        return f"<Place(id={self.id}, rating={self.rating})>"