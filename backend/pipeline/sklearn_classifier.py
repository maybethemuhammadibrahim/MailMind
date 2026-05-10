# backend/pipeline/sklearn_classifier.py
# ---------------------------------------------------------------
# Runtime inference module for the locally trained email classifier.
# Loads the sklearn model lazily on first call and exposes a single
# predict_category() function for coarse email triage.
#
# The model predicts one of: "spam", "promotions", "forum",
# "social_media", "updates", "verify_code".
# Fine-grained categories (urgent, action-required, meeting-request,
# order-update) are handled by Gemini in the main classifier.py.
# ---------------------------------------------------------------

from pathlib import Path
from typing import Optional

import joblib
from sklearn.pipeline import Pipeline

# ---------------------------------------------------------------------------
# Model path — resolved relative to this file's location
# ---------------------------------------------------------------------------

MODEL_PATH: Path = Path(__file__).resolve().parent / "models" / "email_classifier.pkl"

# Module-level cache — model is loaded once on first predict_category() call
_model: Optional[Pipeline] = None


def _load_model() -> Pipeline:
    """Loads the trained sklearn pipeline from disk.

    Returns:
        Pipeline: the trained TF-IDF + LogisticRegression pipeline

    Raises:
        RuntimeError: if the .pkl file does not exist
    """
    global _model

    if _model is not None:
        return _model

    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"sklearn model not found at {MODEL_PATH}. "
            f"Run train/train_classifier.py first."
        )

    print(f"[sklearn] Loading model from {MODEL_PATH}")
    _model = joblib.load(MODEL_PATH)
    print("[sklearn] Model loaded successfully.")
    return _model


def predict_category(subject: str, body: str) -> str:
    """Predicts the coarse email category using the local sklearn model.

    Concatenates subject and body to match the training feature format,
    then returns the predicted MailMind label.

    Args:
        subject: email subject line
        body:    plain-text email body

    Returns:
        One of: "spam", "promotions", "forum", "social_media",
        "updates", "verify_code"
    """
    model: Pipeline = _load_model()

    # Match the training format: text = subject + " " + body
    text: str = f"{subject} {body}"
    prediction: str = model.predict([text])[0]

    return prediction
