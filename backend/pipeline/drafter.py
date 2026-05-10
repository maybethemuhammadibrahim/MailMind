# backend/pipeline/drafter.py
# ---------------------------------------------------------------
# Multi-Agent Reply Drafter — generates professional email replies
# using Gemini with full context: classification, summary, user
# settings (tone/vocabulary), thread history (memory), and
# sentiment analysis. After generating, passes the draft to the
# Quality Review Agent for a quality gate check.
# ---------------------------------------------------------------

from db.sqlite import get_ai_settings, get_thread_history
from pipeline.gemini import call_draft
from pipeline.reviewer import review_draft

# ---------------------------------------------------------------------------
# System prompt — tone rules and exact JSON schema for the draft output
# ---------------------------------------------------------------------------

SYSTEM_TEMPLATE = (
    "You are a warm, emotionally intelligent email assistant who drafts replies "
    "that sound like they were written by a real, thoughtful human being — NOT a robot. "
    "Your replies must feel genuine, personable, and naturally conversational.\n\n"
    "IMPORTANT RULES FOR EVERY REPLY:\n"
    "1. ALWAYS start with a warm, context-appropriate greeting (e.g., 'Hi [Name],' or 'Hello [Name],'). "
    "   Use the sender's first name when available.\n"
    "2. ALWAYS end with a friendly sign-off (e.g., 'Best regards,', 'Warm regards,', 'Thanks again,', "
    "   'Looking forward to hearing from you,') followed by a newline and '[Your Name]'.\n"
    "3. Write at least 3-5 sentences for most replies. Important or urgent emails deserve "
    "   4-8 sentences. NEVER write a one-liner unless the category is spam/promotions.\n"
    "4. Show EMPATHY and EMOTION where appropriate — acknowledge feelings, express genuine "
    "   gratitude, show enthusiasm, or convey concern. Use phrases like 'I really appreciate...', "
    "   'That sounds wonderful!', 'I completely understand...', 'I'm sorry to hear that...'.\n"
    "5. Be SPECIFIC — reference details from the original email to show you actually read it. "
    "   Don't write generic filler.\n"
    "6. Use natural language — contractions are fine ('I'm', 'we'll', 'that's'), vary sentence "
    "   length, and avoid corporate buzzwords.\n\n"
    "USER PREFERENCES:\n"
    "- Default tone: {user_tone}\n"
    "- Writing traits to emphasise: {vocabulary}\n\n"
    "SENDER SENTIMENT CONTEXT:\n"
    "- Sender's mood: {sentiment}\n"
    "- Emotional intensity: {intensity}\n"
    "- Recommended reply tone: {recommended_tone}\n"
    "- IMPORTANT: If the sender is upset, angry, or frustrated, lead with empathy and "
    "  acknowledgment before addressing the content.\n\n"
    "TONE MATCHING BY CATEGORY:\n"
    "- urgent → empathetic and action-oriented, acknowledge the urgency, commit to specific next steps\n"
    "- meeting-request → enthusiastic, confirm availability or propose alternatives with warmth\n"
    "- action-required → acknowledge the task, show commitment, mention when you'll complete it\n"
    "- order-update → friendly acknowledgment of the update\n"
    "- promotions/forum/social_media/updates/verify_code → no reply needed "
    "(return confidence_score 0.1 and a brief 'Thanks for sharing')\n"
    "- spam → no reply needed (return confidence_score 0.0)\n\n"
    "Use the classification and summary provided to understand urgency and what is needed.\n\n"
    "Return ONLY valid JSON with exactly these keys:\n"
    '  "draft_reply": (string — the FULL reply text, including greeting and sign-off, '
    "minimum 3 sentences for non-spam emails),\n"
    '  "confidence_score": (float 0.0-1.0, how appropriate a reply is),\n'
    '  "suggested_subject": (string, reply subject line like \'Re: Original Subject\').'
)


def _build_system_prompt(sentiment: dict = None, settings: dict = None) -> str:
    """
    Builds the system prompt with injected user settings and sentiment data.

    This is what makes the drafter 'settings-aware' — the tone and vocabulary
    preferences from the Settings page are read from the database and injected
    into every drafting call.

    Args:
        sentiment (dict): sentiment data from classifier output, or None
        settings  (dict): pre-fetched AI settings to avoid redundant DB calls

    Returns:
        str: fully assembled system prompt with user preferences
    """
    # Use pre-fetched settings or read from DB (single source)
    if settings is None:
        settings = get_ai_settings()

    # Extract sentiment context (or use safe defaults)
    sent = sentiment or {}
    sentiment_label = sent.get("sender_sentiment", sent.get("sentiment", "neutral"))
    intensity = sent.get("sentiment_intensity", sent.get("intensity", 0.3))
    recommended_tone = sent.get("recommended_reply_tone", sent.get("recommended_tone", settings["tone"]))

    return SYSTEM_TEMPLATE.format(
        user_tone=settings["tone"],
        vocabulary=", ".join(settings["vocabulary"]),
        sentiment=sentiment_label,
        intensity=intensity,
        recommended_tone=recommended_tone,
    )


def _build_prompt(
    subject: str,
    body: str,
    classification: dict,
    summary: dict,
    thread_history: list = None,
) -> str:
    """
    Assembles the drafting prompt by injecting classification, summary,
    and thread history context above the original email.

    The thread history provides 'memory' — the model can see previous
    messages in the conversation and write a reply that feels continuous.

    Args:
        subject        (str):   the original email subject line
        body           (str):   the original email body
        classification (dict):  output from classify_email()
        summary        (dict):  output from summarize_email()
        thread_history (list):  previous emails in the same thread (memory)

    Returns:
        str: fully assembled prompt (body capped at 2000 chars)
    """
    action_items = ", ".join(summary.get("action_items", [])) or "none"
    key_facts = "; ".join(summary.get("key_facts", [])) or "none"

    prompt_parts = [
        f"Category: {classification.get('category', 'updates')}",
        f"Priority score: {classification.get('priority_score', 5)}/10",
        f"Requires reply: {classification.get('requires_reply', False)}",
        f"Summary: {summary.get('one_line_summary', '')}",
        f"Key facts: {key_facts}",
        f"Action items: {action_items}",
    ]

    # Inject thread history (conversation memory) if available.
    # Limit to 3 most recent messages to control token usage.
    if thread_history:
        recent_history = thread_history[-3:]  # Keep only the 3 most recent
        prompt_parts.append("\n--- PREVIOUS MESSAGES IN THIS THREAD (for context) ---")
        for msg in recent_history:
            prompt_parts.append(
                f"From: {msg['sender']} ({msg['timestamp'][:10]})\n"
                f"Body excerpt: {msg['body_plain'][:300]}\n"
            )
        prompt_parts.append("--- END OF THREAD HISTORY ---\n")

    prompt_parts.append(f"\nOriginal email — Subject: {subject}")
    prompt_parts.append(f"Body:\n{body[:2000]}")

    return "\n".join(prompt_parts)


def draft_reply(
    subject: str,
    body: str,
    classification: dict,
    summary: dict,
    sentiment: dict = None,
    thread_id: str = "",
    email_id: str = "",
) -> dict:
    """
    Multi-agent reply drafter: generates a reply using Gemini with full context
    (classification, summary, settings, sentiment, thread memory), then passes
    the draft through the Quality Review Agent for a quality check.

    If the reviewer rejects the draft (score < 0.7), the improved version
    from the reviewer is used instead.

    Args:
        subject        (str):  original email subject
        body           (str):  original email body
        classification (dict): output from classify_email()
        summary        (dict): output from summarize_email()
        sentiment      (dict): output from analyze_sentiment() (optional)
        thread_id      (str):  Gmail thread ID for conversation memory (optional)
        email_id       (str):  current email ID to exclude from thread history

    Returns:
        dict: draft_reply (str), confidence_score (float), suggested_subject (str),
              review_score (float), review_feedback (str)
    """
    category = classification.get("category", "unknown")
    priority = classification.get("priority_score", 5)
    print(f"[Drafter] Drafting — subject: '{subject[:60]}', category: {category}")

    # Fetch settings once — shared by system prompt and review tone
    settings = get_ai_settings()

    # Step 1: Build context-aware system prompt with user settings + sentiment
    system = _build_system_prompt(sentiment, settings=settings)

    # Step 2: Fetch thread history for conversation memory
    thread_history = []
    if thread_id:
        thread_history = get_thread_history(thread_id, exclude_email_id=email_id)
        if thread_history:
            print(f"[Drafter] Thread memory: {len(thread_history)} previous messages")

    # Step 3: Generate the initial draft
    try:
        prompt = _build_prompt(subject, body, classification, summary, thread_history)
        result = call_draft(prompt, system)
        draft_text = result.get("draft_reply", "")
        confidence = result.get("confidence_score", 0.5)
        suggested_subject = result.get("suggested_subject", f"Re: {subject}")

        print(f"[Drafter] Initial draft generated — confidence: {confidence}")

    except Exception as exc:
        print(f"[Drafter] Gemini call failed: {exc} — returning safe default")
        return {
            "draft_reply": (
                f"Hi,\n\nThank you for reaching out regarding '{subject}'. "
                f"I've received your email and will review the details carefully. "
                f"I'll get back to you with a thorough response shortly.\n\n"
                f"Best regards,\n[Your Name]"
            ),
            "confidence_score": 0.4,
            "suggested_subject": f"Re: {subject}",
            "review_score": 0.0,
            "review_feedback": "Draft generation failed — using fallback template.",
        }

    # Step 4: Quality Review Agent — only for high-priority emails.
    # Low-priority emails (promotions, forum, etc.) skip the review to save API quota.
    # High-priority = priority_score >= 7 OR urgent/action-required category.
    should_review = (
        priority >= 7
        or category in ("urgent", "action-required")
    )

    review_score = 0.7
    review_feedback = ""

    if should_review:
        try:
            # Determine the tone to review against (use cached settings)
            review_tone = "professional"
            if sentiment:
                review_tone = sentiment.get(
                    "recommended_reply_tone",
                    sentiment.get("recommended_tone", settings["tone"]),
                )
            else:
                review_tone = settings["tone"]

            review = review_draft(
                original_subject=subject,
                original_body=body,
                draft_text=draft_text,
                requested_tone=review_tone,
                sentiment=sentiment,
            )

            review_score = review.get("score", 0.7)
            review_feedback = review.get("feedback", "")

            # If the reviewer provided an improved version and rejected the original,
            # use the improved version instead
            if not review.get("approved", True) and review.get("improved_draft"):
                print(f"[Drafter] Reviewer rejected (score={review_score}) — using improved draft")
                draft_text = review["improved_draft"]
                # Bump confidence slightly since the reviewed version is better
                confidence = min(confidence + 0.1, 0.95)

            print(f"[Drafter] Final — review_score={review_score}, approved={review.get('approved')}")

        except Exception as exc:
            print(f"[Drafter] Quality review failed: {exc} — skipping review")
            review_score = 0.7
            review_feedback = "Review skipped due to error."
    else:
        print(f"[Drafter] Skipping review — low priority (score={priority}, category={category})")
        review_feedback = "Review skipped — low priority email."

    return {
        "draft_reply": draft_text,
        "confidence_score": confidence,
        "suggested_subject": suggested_subject,
        "review_score": review_score,
        "review_feedback": review_feedback,
    }
