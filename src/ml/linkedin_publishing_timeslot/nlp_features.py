"""
NLP feature extraction for LinkedIn post content.
Provides:
  - extract_text_features: CTA/question detection + VADER sentiment
  - extract_topic_features: BERTopic topic cluster ID + keywords
"""

import re
import logging
import pandas as pd

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


# ── Topic modeling ────────────────────────────────────────────────────────────
def extract_topic_features(df: pd.DataFrame, min_topic_size: int = 5) -> pd.DataFrame:
    """
    Fits a BERTopic model on the post content and assigns each post:
      - topic_id (INTEGER): BERTopic cluster ID (-1 = outlier)
      - topic_label (VARCHAR): comma-joined top keywords for that topic
    Adds these columns to df in-place and returns it.
    """
    try:
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.warning("bertopic/sentence-transformers not installed. Skipping topic features.")
        df["topic_id"] = -1
        df["topic_label"] = "unknown"
        return df

    content = df["content"].fillna("").tolist()
    valid_mask = [bool(c.strip()) for c in content]
    valid_docs = [c for c, v in zip(content, valid_mask) if v]

    if len(valid_docs) < min_topic_size:
        logger.warning(f"Too few documents ({len(valid_docs)}) for topic modeling. Assigning topic_id=-1.")
        df["topic_id"] = -1
        df["topic_label"] = "unknown"
        return df

    logger.info(f"Fitting BERTopic on {len(valid_docs)} documents...")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    topic_model = BERTopic(
        embedding_model=embedding_model,
        min_topic_size=max(min_topic_size, 3),
        verbose=False,
    )
    topics, _ = topic_model.fit_transform(valid_docs)

    # Build a map from topic_id -> label (top 3 words)
    topic_info = topic_model.get_topic_info()
    topic_label_map = {}
    for _, row in topic_info.iterrows():
        tid = row["Topic"]
        words = topic_model.get_topic(tid)
        if words:
            label = ", ".join([w for w, _ in words[:3]])
        else:
            label = "unknown"
        topic_label_map[tid] = label

    # Fill full array (including empty-content rows)
    topic_ids = []
    topic_labels = []
    valid_iter = iter(topics)
    for is_valid in valid_mask:
        if is_valid:
            tid = next(valid_iter)
            topic_ids.append(tid)
            topic_labels.append(topic_label_map.get(tid, "unknown"))
        else:
            topic_ids.append(-1)
            topic_labels.append("unknown")

    df["topic_id"] = topic_ids
    df["topic_label"] = topic_labels

    logger.info(f"BERTopic: assigned {len(set(t for t in topic_ids if t >= 0))} topics.")
    return df
