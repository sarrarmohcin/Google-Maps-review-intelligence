import json
from dataclasses import dataclass, field
import dateparser
from datetime import datetime, timezone

@dataclass
class Reviewer:
    name: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    user_id: str = ""
    review_count: int = 0
    is_local_guide: bool = False


@dataclass
class Review:
    reviewer: Reviewer = field(default_factory=Reviewer)
    rating: int = 0
    text: str = ""
    date: int = 0
    language: str = ""
    owner_reply: str = ""
    owner_reply_date: int = 0
    review_id: str = ""
    
    

    def to_dict(self):
        return {
            "review_id": self.review_id,
            "reviewer_name": self.reviewer.name,
            "reviewer_url": self.reviewer.profile_url,
            "reviewer_avatar": self.reviewer.avatar_url,
            "reviewer_id": self.reviewer.user_id,
            "reviewer_review_count": self.reviewer.review_count,
            "reviewer_is_local_guide": self.reviewer.is_local_guide,
            "review_rating": self.rating,
            "review_text": self.text,
            "review_date": datetime.fromtimestamp(self.date, tz=timezone.utc).isoformat(),
            "review_language": self.language,
            "owner_reply": self.owner_reply,
            "owner_reply_date": datetime.fromtimestamp(self.owner_reply_date, tz=timezone.utc).isoformat(),
            "scraped_at": datetime.now(timezone.utc).isoformat()
        }


def relative_to_datetime(date_str, language='en'):
    if not date_str:
        return int(datetime.now(timezone.utc).timestamp())
    
    date_language = {
            'en' : 'Edited',
            'fr' : 'Modifié'
        }

    try:
        date_str = date_str.replace(date_language[language], ' ').strip()
        parsed_time = dateparser.parse(date_str, languages=[language])
        return int(parsed_time.timestamp()) 
    except (ValueError, TypeError):
        return int(datetime.now(timezone.utc).timestamp())

def get_review_count(review_count, language='en'):
    
    review_language = {
            'en' : ['reviews', 'review'],
            'fr' : ['avis', 'avis']
        }
    
    review_count_str = ""
    if '·' in review_count:
        review_count_str = review_count.split('·')[1].strip()
    review_count_str = review_count.strip()
    
    if review_count_str:
        review_count_str = review_count_str.replace(review_language[language][0], '').replace(review_language[language][1], '').strip()
        review_count_str = review_count_str.replace(',', '')
        try:
            return int(review_count_str)
        except ValueError:
            return 0
    
    return 0
    
def parse_reviews_response(text, language='en'):
    """Parse reviews response. Returns (reviews, next_cursor)."""
    text = _strip_xssi(text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [], None

    next_cursor = _get(data, 1)
    entries = _get(data, 2, default=[])
    if not isinstance(entries, list):
        return [], next_cursor if next_cursor else None

    reviews = []
    for entry in entries:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        review = _parse_single_review(entry, language)
        if review:
            reviews.append(review)
    return reviews

def _strip_xssi(text):
    if text.startswith(")]}'"):
        text = text[4:].lstrip("\n")
    return text


def _get(data, *indices, default=None):
    current = data
    for idx in indices:
        if not isinstance(current, (list, tuple)):
            return default
        if idx < 0 or idx >= len(current):
            return default
        current = current[idx]
    return current if current is not None else default


def _parse_single_review(entry, language='en'):
    """Parse a single review entry."""
    review = Review()
    inner = _get(entry, 0, default=[])
    if not isinstance(inner, list) or len(inner) < 3:
        return None

    review.review_id = _get(inner, 0, default="")
    if not isinstance(review.review_id, str):
        return None

    meta = _get(inner, 1, default=[])
    if isinstance(meta, list):
        author_block = _get(meta, 4, default=[])
        author_info = _get(author_block, 5, default=[])
        if isinstance(author_info, list) and len(author_info) > 3:
            r = Reviewer()
            r.name = _get(author_info, 0, default="") or ""
            r.avatar_url = _get(author_info, 1, default="") or ""
            profile_urls = _get(author_info, 2, default=[])
            if isinstance(profile_urls, list) and profile_urls:
                r.profile_url = profile_urls[0] if isinstance(profile_urls[0], str) else ""
            r.user_id = _get(author_info, 3, default="") or ""
            guide_level = _get(author_info, 5, default=0)
            r.is_local_guide = isinstance(guide_level, int) and guide_level > 0
            review_meta = _get(author_info, 10, default=[])
            if isinstance(review_meta, list) and review_meta:
                review_count_str = _get(review_meta, 0, default="") or ""
                r.review_count = get_review_count(review_count_str, language)
            review.reviewer = r

        review_date = _get(meta, 6, default="") or ""
        review.date = relative_to_datetime(review_date, language) if review_date else ""

    content = _get(inner, 2, default=[])
    if isinstance(content, list):
        rating_arr = _get(content, 0, default=[])
        if isinstance(rating_arr, list) and rating_arr:
            review.rating = int(_get(rating_arr, 0, default=0) or 0)

        lang_arr = _get(content, 14, default=[])
        if isinstance(lang_arr, list) and lang_arr:
            review.language = lang_arr[0] if isinstance(lang_arr[0], str) else ""

        text_blocks = _get(content, 15, default=[])
        if isinstance(text_blocks, list):
            for tb in text_blocks:
                if isinstance(tb, list) and tb and isinstance(tb[0], str):
                    review.text = tb[0]
                    break


    reply = _get(inner, 3)
    if isinstance(reply, list) and len(reply) > 3:
        owner_reply_date_str = _get(reply, 3, default="") or ""
        review.owner_reply_date = relative_to_datetime(owner_reply_date_str, language)
        reply_text_blocks = _get(reply, 14, default=[])
        if isinstance(reply_text_blocks, list):
            for tb in reply_text_blocks:
                if isinstance(tb, list) and tb and isinstance(tb[0], str):
                    review.owner_reply = tb[0]
                    break

    return review
