"""Classify Portuguese review comments as negative (score 1-2) or not, from the text alone.

Baseline: TF-IDF word + character n-grams with logistic regression. Cheap, fast, strong.
The transformer version (multilingual DistilBERT) is in notebooks/review_sentiment_distilbert_colab.ipynb
because fine-tuning needs a GPU (free on Google Colab).

    python -m ml.review_sentiment
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline, make_union
from sqlalchemy import text

from backend.config import readonly_engine
from ml import tracking

SQL = """
SELECT TRIM(COALESCE(review_comment_title, '') || ' ' || review_comment_message) AS text,
       (review_score <= 2)::int AS negative
FROM olist.order_reviews
WHERE review_comment_message IS NOT NULL AND LENGTH(TRIM(review_comment_message)) >= 3
"""


def load() -> pd.DataFrame:
    with readonly_engine().connect() as conn:
        return pd.read_sql(text(SQL), conn)


def model():
    features = make_union(
        TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True, strip_accents="unicode"),
        TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=5, sublinear_tf=True, strip_accents="unicode"),
    )
    return make_pipeline(features, LogisticRegression(max_iter=3000, C=4.0, class_weight="balanced"))


def main() -> None:
    df = load()
    train, test = train_test_split(df, test_size=0.2, stratify=df["negative"], random_state=0)
    clf = model().fit(train["text"], train["negative"])
    pred = clf.predict(test["text"])
    f1 = f1_score(test["negative"], pred)
    with tracking.start("review_sentiment"):
        import mlflow

        mlflow.log_params({"model": "tfidf_word_char+logreg", "train_rows": len(train)})
        mlflow.log_metric("f1_negative", f1)
    examples = test.assign(pred=pred)
    report = {"rows": len(df), "negative_share": round(float(df["negative"].mean()), 4), "f1_negative": round(float(f1), 4),
              "classification_report": classification_report(test["negative"], pred, output_dict=True),
              "sample_errors": examples[examples["pred"] != examples["negative"]].head(5).to_dict(orient="records")}
    print(tracking.save_report("review_sentiment", report))
    print(f"F1 (negative class): {f1:.3f} on {len(test):,} held-out reviews")


if __name__ == "__main__":
    main()
