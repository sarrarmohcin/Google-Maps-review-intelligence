PLACES_QUERY = """
SELECT id, name, rating, reviews, url
FROM public.places
ORDER BY name
"""

REVIEWS_QUERY = """
SELECT *
FROM public.gm_reviews
WHERE business_id = %(business_id)s
ORDER BY review_date DESC
"""

REVIEWERS_QUERY = """
SELECT *
FROM public.mv_reviewer_stats
WHERE business_id = %(business_id)s
ORDER BY total_reviews DESC
"""

BUSINESS_STATS_QUERY = """
SELECT *
FROM public.mv_business_stats
WHERE business_id = %(business_id)s
"""

ASPECTS_QUERY = """
SELECT *
FROM public.mv_business_aspects
WHERE business_id = %(business_id)s
ORDER BY total_mentions DESC
"""