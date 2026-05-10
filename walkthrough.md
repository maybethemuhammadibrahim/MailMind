# Hybrid Email Classifier — Implementation Walkthrough

## Overview

Retrofitted the MailMind email classifier with a **hybrid sklearn + Gemini** approach:
- **sklearn** handles coarse triage (spam / newsletter / fyi) — instant, free, no API calls
- **Gemini** handles fine-grained classification + full sentiment analysis — may upgrade to urgent, action-required, meeting-request, order-update

## Files Changed / Created

| File | Status | Purpose |
|------|--------|---------|
| `train/train_classifier.py` | **NEW** | One-time training script |
| `backend/pipeline/sklearn_classifier.py` | **NEW** | Runtime inference (lazy model loading) |
| `backend/pipeline/classifier.py` | **MODIFIED** | Hybrid: sklearn first → Gemini refinement |
| `.gitignore` | **MODIFIED** | Added train data + model exclusions |

### Files NOT modified (as requested)
gemini.py, summarizer.py, drafter.py, reviewer.py, crafter.py, all extractors, all routes, all DB files, main.py — **none touched**.

## How to Train the Model

### Step 1 — Install dependencies
```bash
pip install scikit-learn joblib pandas
```
(Already installed in your venv.)

### Step 2 — Place the dataset
Download the `jason23322/high-accuracy-email-classifier` dataset and place the CSV files at:
```
train/train.csv
train/test.csv
```

### Step 3 — Run training (from project root)
```bash
python train/train_classifier.py
```

This will:
1. Load and translate labels (Spam→spam, Promotions→newsletter, everything else→fyi)
2. Train a TF-IDF + LogisticRegression pipeline
3. Print a classification report with per-class precision/recall/F1
4. Save the model to `backend/pipeline/models/email_classifier.pkl`

### Step 4 — Restart the app
```bash
uvicorn main:app --reload --port 8000
```

The model loads lazily on the first email classification request.

## Runtime Flow (Before vs After)

### Before
```
Email → Gemini (full classification + sentiment) → result dict
```
Each email cost 1 Gemini API call for classification.

### After
```
Email → sklearn (instant, free) → coarse category
      → Gemini (uses sklearn hint + does sentiment) → result dict
```
- sklearn runs in ~1ms, predicts: spam / newsletter / fyi
- The prediction is injected into the Gemini prompt as a "starting point"
- Gemini may override to urgent/action-required/meeting-request/order-update if warranted
- If Gemini fails (quota exhausted), the sklearn prediction is used as fallback instead of "unknown"

## Label Translation Map

| Dataset Label | MailMind Label |
|--------------|----------------|
| Spam | spam |
| Promotions | newsletter |
| Forum | fyi |
| Social Media | fyi |
| Updates | fyi |
| Verify Code | fyi |

> **Note:** urgent, action-required, meeting-request, order-update are NOT in the dataset.
> These are only assigned by Gemini based on email content analysis.

## Key Design Decisions

1. **Graceful degradation**: If the `.pkl` file is missing, classifier.py catches the RuntimeError and falls back to `"fyi"` as the sklearn hint — Gemini still works normally
2. **Gemini failure fallback**: If Gemini is down/exhausted, the result uses the sklearn category instead of "unknown", giving a better-than-nothing classification
3. **Same API surface**: `classify_email(subject, sender, body) → dict` — signature and return type unchanged, all downstream code works without modification
