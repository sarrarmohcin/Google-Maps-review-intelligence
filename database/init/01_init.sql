-- =========================
-- EXTENSIONS
-- =========================
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- =========================
-- TABLES
-- =========================

CREATE TABLE IF NOT EXISTS public.gm_reviews (
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

    overall_sentiment VARCHAR(20),
    aspects JSONB,
    main_complaint TEXT,
    summary TEXT,

    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.places (
    id BIGINT PRIMARY KEY,
    url TEXT NOT NULL,
    name TEXT NOT NULL,
    rating NUMERIC(3,2) NOT NULL DEFAULT 0,
    reviews INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- =========================
-- INDEXES
-- =========================

CREATE INDEX IF NOT EXISTS idx_gm_reviews_business_id
ON public.gm_reviews(business_id);

CREATE INDEX IF NOT EXISTS idx_gm_reviews_reviewer_id
ON public.gm_reviews(reviewer_id);

CREATE INDEX IF NOT EXISTS idx_gm_reviews_review_date
ON public.gm_reviews(review_date);

CREATE INDEX IF NOT EXISTS idx_gm_reviews_rating
ON public.gm_reviews(review_rating);

CREATE INDEX IF NOT EXISTS idx_gm_reviews_overall_sentiment
ON public.gm_reviews(overall_sentiment);

CREATE INDEX IF NOT EXISTS idx_gm_reviews_aspects
ON public.gm_reviews USING GIN(aspects);

CREATE INDEX IF NOT EXISTS idx_places_rating
ON public.places(rating DESC);

CREATE INDEX IF NOT EXISTS idx_places_reviews
ON public.places(reviews DESC);

-- =========================
-- MATERIALIZED VIEW
-- =========================

CREATE MATERIALIZED VIEW public.mv_reviewer_stats AS
SELECT
    business_id,
    reviewer_id,

    MAX(reviewer_name) AS reviewer_name,
    MAX(reviewer_url) AS reviewer_url,
    MAX(reviewer_avatar) AS reviewer_avatar,

    COUNT(*) AS total_reviews,

    AVG(review_rating)::NUMERIC(10,2) AS average_rating,

    MIN(review_date) AS first_review_date,
    MAX(review_date) AS last_review_date,

    BOOL_OR(reviewer_is_local_guide) AS is_local_guide,

    MAX(reviewer_review_count) AS google_review_count

FROM public.gm_reviews
WHERE reviewer_id IS NOT NULL
GROUP BY business_id, reviewer_id;

-- required for CONCURRENT refresh
CREATE UNIQUE INDEX IF NOT EXISTS mv_reviewer_stats_reviewer_id_idx
ON public.mv_reviewer_stats(reviewer_id);

CREATE INDEX IF NOT EXISTS mv_reviewer_stats_total_reviews_idx
ON public.mv_reviewer_stats(total_reviews DESC);

CREATE INDEX IF NOT EXISTS mv_reviewer_stats_average_rating_idx
ON public.mv_reviewer_stats(average_rating DESC);


-- =========================
-- BUSINESS GLOBAL STATS
-- =========================

DROP MATERIALIZED VIEW IF EXISTS public.mv_business_stats CASCADE;

CREATE MATERIALIZED VIEW public.mv_business_stats AS
SELECT
    business_id,

    COUNT(*) AS total_reviews,

    AVG(review_rating)::NUMERIC(10,2) AS average_rating,

    COUNT(*) FILTER (
        WHERE overall_sentiment = 'positive'
    ) AS positive_reviews,

    COUNT(*) FILTER (
        WHERE overall_sentiment = 'neutral'
    ) AS neutral_reviews,

    COUNT(*) FILTER (
        WHERE overall_sentiment = 'negative'
    ) AS negative_reviews,

    MIN(review_date) AS first_review_date,
    MAX(review_date) AS last_review_date

FROM public.gm_reviews
GROUP BY business_id;

-- unique index required for CONCURRENT refresh
CREATE UNIQUE INDEX mv_business_stats_business_id_idx
ON public.mv_business_stats(business_id);


-- =========================
-- BUSINESS ASPECT ANALYTICS
-- =========================

DROP MATERIALIZED VIEW IF EXISTS public.mv_business_aspects CASCADE;

CREATE MATERIALIZED VIEW public.mv_business_aspects AS
SELECT
    r.business_id,

    aspect_item->>'aspect' AS aspect,

    COUNT(*) AS total_mentions,

    COUNT(*) FILTER (
        WHERE aspect_item->>'sentiment' = 'positive'
    ) AS positive_mentions,

    COUNT(*) FILTER (
        WHERE aspect_item->>'sentiment' = 'neutral'
    ) AS neutral_mentions,

    COUNT(*) FILTER (
        WHERE aspect_item->>'sentiment' = 'negative'
    ) AS negative_mentions

FROM public.gm_reviews r,

LATERAL jsonb_array_elements(r.aspects) AS aspect_item

WHERE r.aspects IS NOT NULL

GROUP BY
    r.business_id,
    aspect_item->>'aspect';

-- required for concurrent refresh
CREATE UNIQUE INDEX mv_business_aspects_unique_idx
ON public.mv_business_aspects(business_id, aspect);


-- =========================
-- REFRESH FUNCTION
-- =========================

CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_reviewer_stats;

    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_business_stats;

    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_business_aspects;
END;
$$ LANGUAGE plpgsql;

-- =========================
-- CRON JOB (IDEMPOTENT)
-- =========================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM cron.job
        WHERE jobname = 'refresh_all_materialized_views'
    ) THEN

        PERFORM cron.schedule(
            'refresh_all_materialized_views',
            '0 0 * * *',
            $cron$
            SELECT refresh_all_materialized_views();
            $cron$
        );

    END IF;
END;
$$;