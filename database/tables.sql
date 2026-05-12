-- Reviews table
CREATE TABLE public.gm_reviews (
    id BIGSERIAL PRIMARY KEY,

    business_id BIGINT NOT NULL,

    review_id TEXT NOT NULL UNIQUE,

    reviewer_name TEXT,
    reviewer_url TEXT,
    reviewer_avatar TEXT,
    reviewer_id TEXT,
    reviewer_review_count INTEGER,
    reviewer_is_local_guide BOOLEAN DEFAULT FALSE,

    review_rating SMALLINT NOT NULL CHECK (review_rating BETWEEN 1 AND 5),
    review_text TEXT,
    review_date TIMESTAMPTZ,
    review_language VARCHAR(10),

    owner_reply TEXT,
    owner_reply_date TIMESTAMPTZ,

    overall_sentiment VARCHAR(20) null,
    aspects jsonb null,
    main_complaint text null,
    summary text null,

    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Useful indexes
CREATE INDEX idx_gm_reviews_business_id
ON public.gm_reviews(business_id);

CREATE INDEX idx_gm_reviews_reviewer_id
ON public.gm_reviews(reviewer_id);

CREATE INDEX idx_gm_reviews_review_date
ON public.gm_reviews(review_date);

CREATE INDEX idx_gm_reviews_rating
ON public.gm_reviews(review_rating);

CREATE INDEX idx_gm_reviews_overall_sentiment
ON public.gm_reviews(overall_sentiment);

CREATE INDEX idx_gm_reviews_aspects
ON public.gm_reviews
USING GIN(aspects);

-- places table
CREATE TABLE public.places (
    id BIGINT PRIMARY KEY,

    url TEXT NOT NULL,

    rating NUMERIC(3,2) NOT NULL DEFAULT 0,

    reviews INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_places_rating
ON public.places(rating DESC);

CREATE INDEX idx_places_reviews
ON public.places(reviews DESC);