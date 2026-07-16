"""
NLP feature extraction for LinkedIn post content.
Provides:
  - extract_text_features: CTA/question detection + VADER sentiment
  - extract_topic_features: TF-IDF + KMeans topic clustering (zero extra deps, uses sklearn)
"""

import re
import logging
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

logger = logging.getLogger("ml-service.linkedin_timeslot.nlp")

# ── CTA / Question detection ──────────────────────────────────────────────────
_CTA_PHRASES = [
    r"let me know",
    r"comment below",
    r"drop a comment",
    r"share (this|if|your|below)",
    r"what do you think",
    r"what('s| is) your (take|view|opinion|thought)",
    r"tag (a|someone|a friend)",
    r"repost if",
    r"follow (me|us|for)",
    r"click (the )?(link|button)",
    r"swipe (left|right|up)",
    r"check (it |this )?out",
    r"dm me",
    r"sign up",
    r"learn more",
]
_CTA_PATTERN = re.compile("|".join(_CTA_PHRASES), re.IGNORECASE)

_QUESTION_STARTERS = re.compile(
    r"(^|\n)(what|why|how|when|where|who|which|do you|have you|are you|would you|could you|should we|can you)",
    re.IGNORECASE,
)


def _has_cta(text: str) -> bool:
    if not text:
        return False
    return bool(_CTA_PATTERN.search(text))


def _has_question(text: str) -> bool:
    if not text:
        return False
    return "?" in text or bool(_QUESTION_STARTERS.search(text))


def extract_text_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds per-row text features to the DataFrame.
    Expects a `content` column.
    Adds: has_cta, has_question, sentiment_score, sentiment_label
    """
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
    except ImportError:
        logger.warning("vaderSentiment not installed. Skipping sentiment features.")
        df["has_cta"] = False
        df["has_question"] = False
        df["sentiment_score"] = 0.0
        df["sentiment_label"] = "neutral"
        return df

    content = df["content"].fillna("")

    df["has_cta"] = content.apply(_has_cta)
    df["has_question"] = content.apply(_has_question)

    def _sentiment(text):
        scores = analyzer.polarity_scores(text)
        compound = scores["compound"]
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        return compound, label

    sentiments = content.apply(_sentiment)
    df["sentiment_score"] = [s[0] for s in sentiments]
    df["sentiment_label"] = [s[1] for s in sentiments]

    return df


# ── Topic modeling (TF-IDF + KMeans) ─────────────────────────────────────────
def extract_topic_features(df: pd.DataFrame, min_topic_size: int = 5, n_topics: int = 8) -> pd.DataFrame:
    """
    Clusters posts into topics using TF-IDF + KMeans (sklearn only, no extra deps).
    Assigns each post:
      - topic_id (INTEGER): cluster ID 0..n_topics-1, or -1 if insufficient data
      - topic_label (VARCHAR): top 3 TF-IDF keywords for that cluster
    """
    content = df["content"].fillna("").tolist()
    valid_mask = [bool(c.strip()) for c in content]
    valid_docs = [c for c, v in zip(content, valid_mask) if v]

    if len(valid_docs) < min_topic_size:
        logger.warning(
            f"Too few documents ({len(valid_docs)}) for topic modeling. Assigning topic_id=-1."
        )
        df["topic_id"] = -1
        df["topic_label"] = "unknown"
        return df

    # Fit TF-IDF
    n_clusters = min(n_topics, len(valid_docs) // 2)
    logger.info(f"Fitting TF-IDF + KMeans ({n_clusters} clusters) on {len(valid_docs)} documents...")

    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
    )
    X = vectorizer.fit_transform(valid_docs)
    X_norm = normalize(X)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_ids = km.fit_predict(X_norm)

    # Build cluster label from top TF-IDF terms per centroid
    terms = vectorizer.get_feature_names_out()
    cluster_label_map = {}
    for cid, centroid in enumerate(km.cluster_centers_):
        top_indices = centroid.argsort()[-3:][::-1]
        label = ", ".join(terms[i] for i in top_indices)
        cluster_label_map[cid] = label

    # Re-align with original rows (including empty-content ones)
    topic_ids = []
    topic_labels = []
    valid_iter = iter(cluster_ids)
    for is_valid in valid_mask:
        if is_valid:
            cid = int(next(valid_iter))
            topic_ids.append(cid)
            topic_labels.append(cluster_label_map.get(cid, "unknown"))
        else:
            topic_ids.append(-1)
            topic_labels.append("unknown")

    df["topic_id"] = topic_ids
    df["topic_label"] = topic_labels

    logger.info(f"TF-IDF KMeans: assigned {n_clusters} topics.")
    return df
