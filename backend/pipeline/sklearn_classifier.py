
from pathlib import Path
from typing import Optional

import joblib
from sklearn.pipeline import Pipeline


MODEL_PATH: Path = Path(__file__).resolve().parent / "models" / "email_classifier.pkl"

_model: Optional[Pipeline] = None


def _load_model() -> Pipeline:
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
    model: Pipeline = _load_model()

    text: str = f"{subject} {body}"
    prediction: str = model.predict([text])[0]

    return prediction
