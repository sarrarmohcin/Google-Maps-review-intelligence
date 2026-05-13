import streamlit as st
import pandas as pd
import plotly.express as px

from db import run_query
from queries import (
    PLACES_QUERY,
    REVIEWS_QUERY,
    REVIEWERS_QUERY,
    BUSINESS_STATS_QUERY,
    ASPECTS_QUERY
)

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="Google Maps Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# -------------------------------
# DATA LOADERS (cached)
# -------------------------------
@st.cache_data
def load_places():
    return run_query(PLACES_QUERY)


@st.cache_data
def load_reviews(business_id):
    return run_query(REVIEWS_QUERY, {"business_id": business_id})


@st.cache_data
def load_reviewers(business_id):
    return run_query(REVIEWERS_QUERY, {"business_id": business_id})


@st.cache_data
def load_stats(business_id):
    return run_query(BUSINESS_STATS_QUERY, {"business_id": business_id})


@st.cache_data
def load_aspects(business_id):
    return run_query(ASPECTS_QUERY, {"business_id": business_id})


# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.title("📍 Places")

places = load_places()

selected = st.sidebar.selectbox(
    "Select a place",
    places["id"].tolist(),
    format_func=lambda x: places[places["id"] == x]["name"].values[0]
)

place = places[places["id"] == selected].iloc[0]


# Sidebar metrics
st.sidebar.markdown("### Quick Stats")
st.sidebar.metric("Rating", place["rating"])
st.sidebar.metric("Reviews", place["reviews"])


# -------------------------------
# HEADER CARD
# -------------------------------
st.markdown(f"""
<div class="card">
    <h2 class="big-title">🏢 {place['name']}</h2>
    <p>🔗 <a href="{place['url']}" target="_blank">Google Maps Link</a></p>
</div>
""", unsafe_allow_html=True)


# Load data
reviews = load_reviews(selected)
reviewers = load_reviewers(selected)
stats = load_stats(selected)
aspects = load_aspects(selected)


# -------------------------------
# TABS
# -------------------------------
tab1, tab2, tab3 = st.tabs(["📝 Reviews", "👤 Reviewers", "📊 Analytics"])


# ======================================================
# TAB 1 - REVIEWS
# ======================================================
with tab1:
    st.subheader("Customer Reviews")

    sentiment_filter = st.selectbox(
        "Filter sentiment",
        ["all", "positive", "neutral", "negative"]
    )

    df = reviews.copy()

    if sentiment_filter != "all":
        df = df[df["overall_sentiment"] == sentiment_filter]

    for _, r in df.head(20).iterrows():
        st.markdown(f"""
        <div class="card">
            <h4>{r['reviewer_name']} ⭐ {r['review_rating']}</h4>
            <p><b>Sentiment:</b> {r['overall_sentiment']}</p>
            <p>{r['review_text'][:300] if r['review_text'] else ""}</p>
            <hr>
            <p><i>{r['summary'] or ""}</i></p>
        </div>
        """, unsafe_allow_html=True)


# ======================================================
# TAB 2 - REVIEWERS
# ======================================================
with tab2:
    st.subheader("Top Reviewers")

    st.dataframe(
        reviewers[
            [
                "reviewer_name",
                "total_reviews",
                "average_rating",
                "google_review_count",
                "first_review_date",
                "last_review_date"
            ]
        ],
        use_container_width=True
    )

    fig = px.bar(
        reviewers.head(10),
        x="reviewer_name",
        y="total_reviews",
        title="Top Reviewers"
    )
    st.plotly_chart(fig, use_container_width=True)


# ======================================================
# TAB 3 - ANALYTICS
# ======================================================
with tab3:
    st.subheader("Sentiment Analysis")

    if not stats.empty:
        s = stats.iloc[0]

        col1, col2, col3 = st.columns(3)

        col1.metric("Positive", s["positive_reviews"])
        col2.metric("Neutral", s["neutral_reviews"])
        col3.metric("Negative", s["negative_reviews"])

        pie_df = pd.DataFrame({
            "sentiment": ["positive", "neutral", "negative"],
            "count": [
                s["positive_reviews"],
                s["neutral_reviews"],
                s["negative_reviews"]
            ]
        })

        fig = px.pie(
            pie_df,
            names="sentiment",
            values="count",
            title="Sentiment Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Aspects Analysis")

    if not aspects.empty:
        fig2 = px.bar(
            aspects.head(10),
            x="aspect",
            y="total_mentions",
            color="positive_mentions",
            title="Top Aspects"
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(aspects, use_container_width=True)