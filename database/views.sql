-- Reviewer aggregated materialized view
CREATE MATERIALIZED VIEW public.mv_reviewer_stats AS
SELECT
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
GROUP BY reviewer_id;

CREATE UNIQUE INDEX mv_reviewer_stats_reviewer_id_idx
ON public.mv_reviewer_stats(reviewer_id);

CREATE INDEX mv_reviewer_stats_total_reviews_idx
ON public.mv_reviewer_stats(total_reviews DESC);

CREATE INDEX mv_reviewer_stats_average_rating_idx
ON public.mv_reviewer_stats(average_rating DESC);