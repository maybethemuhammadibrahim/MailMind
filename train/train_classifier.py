# train/train_classifier.py
# ---------------------------------------------------------------
# ONE-TIME training script for the MailMind email classifier.
# Trains a TF-IDF + Logistic Regression pipeline on the
# jason23322/high-accuracy-email-classifier dataset and saves
# the trained model as a .pkl file for runtime inference.
#
# Usage (from project root):
#   python train/train_classifier.py
#
# Prerequisites:
#   pip install scikit-learn joblib pandas
#   Place train.csv and test.csv in the train/ directory.
# ---------------------------------------------------------------

from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline

# ---------------------------------------------------------------------------
# Path resolution — all paths relative to this script's location
# ---------------------------------------------------------------------------

SCRIPT_DIR: Path = Path(__file__).resolve().parent        # train/
DATA_DIR: Path = SCRIPT_DIR                                # train.csv lives here
MODEL_DIR: Path = SCRIPT_DIR.parent / "backend" / "pipeline" / "models"
MODEL_PATH: Path = MODEL_DIR / "email_classifier.pkl"

TRAIN_CSV: Path = DATA_DIR / "train.csv"
TEST_CSV: Path = DATA_DIR / "test.csv"

# ---------------------------------------------------------------------------
# Dataset labels — used directly as training targets (no translation layer)
# ---------------------------------------------------------------------------

# The dataset contains 6 categories that MailMind uses as-is for sklearn
# coarse triage: spam, promotions, forum, social_media, updates, verify_code.
# Fine-grained categories (urgent, action-required, meeting-request,
# order-update) are handled by Gemini at runtime.

VALID_LABELS: list[str] = [
    "spam", "promotions", "forum", "social_media", "updates", "verify_code",
]


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------


def main() -> None:
    """Loads data, trains the classifier, evaluates, and saves the model."""

    # --- 1. Validate files exist ---
    if not TRAIN_CSV.exists():
        raise FileNotFoundError(
            f"Training data not found at {TRAIN_CSV}\n"
            f"Download the dataset and place train.csv in {DATA_DIR}"
        )
    if not TEST_CSV.exists():
        raise FileNotFoundError(
            f"Test data not found at {TEST_CSV}\n"
            f"Download the dataset and place test.csv in {DATA_DIR}"
        )

    # --- 2. Load CSVs ---
    print(f"[Train] Loading training data from {TRAIN_CSV}")
    train_df: pd.DataFrame = pd.read_csv(TRAIN_CSV)

    print(f"[Train] Loading test data from {TEST_CSV}")
    test_df: pd.DataFrame = pd.read_csv(TEST_CSV)

    print(f"[Train] Training samples: {len(train_df):,}")
    print(f"[Train] Test samples:     {len(test_df):,}")

    # --- 3. Use raw dataset labels directly ---
    print("[Train] Using raw dataset category labels...")
    print(f"[Train] Label distribution (train):\n{train_df['category'].value_counts().to_string()}")
    print(f"[Train] Label distribution (test):\n{test_df['category'].value_counts().to_string()}")

    # --- 4. Prepare features ---
    # The 'text' column contains pre-combined subject + body
    X_train: pd.Series = train_df["text"].fillna("")
    y_train: pd.Series = train_df["category"]

    X_test: pd.Series = test_df["text"].fillna("")
    y_test: pd.Series = test_df["category"]

    # --- 5. Build sklearn Pipeline ---
    print("[Train] Building TF-IDF + LogisticRegression pipeline...")
    model: Pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=15000,
                sublinear_tf=True,
            ),
        ),
        (
            "clf",
            LogisticRegression(
                max_iter=1000,
                C=5,
                class_weight="balanced",
            ),
        ),
    ])

    # --- 6. Train ---
    print("[Train] Training the model...")
    model.fit(X_train, y_train)
    print("[Train] Training complete.")

    # --- 7. Evaluate ---
    print("[Train] Evaluating on test set...")
    y_pred: pd.Series = model.predict(X_test)
    accuracy: float = accuracy_score(y_test, y_pred)

    print("\n" + "=" * 60)
    print("CLASSIFICATION REPORT")
    print("=" * 60)
    print(classification_report(y_test, y_pred))
    print(f"Test Accuracy: {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print("=" * 60)

    # --- 8. Save model ---
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    # --- 9. Confirmation ---
    print(f"\nModel saved to: {MODEL_PATH.resolve()}")
    print(f"Test accuracy:  {accuracy:.4f}")
    print("\nThe MailMind app will now use this model for coarse email triage.")
    print("Gemini will still handle fine-grained classification at runtime.")


if __name__ == "__main__":
    main()
