"""
Idea Generator Agent - SMART VERSION
Generates astrophysics YouTube Shorts ideas using Gemini API.
Now uses analytics data to prioritize winning topic types,
while avoiding repetitive ideas and topic-family spam.
"""

import os
import json
import random
import requests
import re
import time
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================
STRATEGY_FILE = "data/strategy.json"
PERFORMANCE_FILE = "data/performance_history.json"
IDEAS_FILE = "ideas.json"

# Default topic families if no analytics data exists
DEFAULT_TOPICS = [
    "scale_comparison",
    "travel_time",
    "planetary_facts",
    "hypothetical",
    "myth_busting"
]

# Topic descriptions for the AI
TOPIC_DESCRIPTIONS = {
    "scale_comparison": "comparing sizes of cosmic objects (How many Earths fit in the Sun? How big is the Milky Way compared to...?)",
    "travel_time": "how long it takes to travel to cosmic destinations at various speeds (How long to reach Mars at light speed?)",
    "planetary_facts": "surprising facts about planets, moons, or other bodies (A day on Venus is longer than its year)",
    "hypothetical": "what-if scenarios in space (What if you fell into a black hole? Could you survive on...?)",
    "myth_busting": "correcting common misconceptions about space (Is the Sun actually yellow? Can you hear explosions in space?)",
    "cosmic_mystery": "unexplained phenomena and mysteries of the universe (What is dark matter? Why is the universe expanding faster?)",
    "extreme_conditions": "extreme environments and conditions in space (hottest planet, coldest place, strongest gravity)"
}

RECENT_TOPIC_LIMIT = 10
RECENT_FAMILY_BLOCK = 3
MAX_GENERATION_ATTEMPTS = 5


# =============================================================================
# TEXT NORMALIZATION / SIMILARITY
# =============================================================================
def normalize_text(text):
    """Normalize text for easier duplicate detection."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text):
    """Convert text into a set of normalized words."""
    return set(normalize_text(text).split())


def jaccard_similarity(a, b):
    """Simple word-overlap similarity."""
    a_words = tokenize(a)
    b_words = tokenize(b)

    if not a_words or not b_words:
        return 0.0

    intersection = len(a_words & b_words)
    union = len(a_words | b_words)
    return intersection / union if union else 0.0


# =============================================================================
# ANALYTICS INTEGRATION
# =============================================================================
def load_strategy():
    """Load the current strategy from analytics."""
    if os.path.exists(STRATEGY_FILE):
        try:
            with open(STRATEGY_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load strategy: {e}")
    return None


def load_performance_history():
    """Load past video performance."""
    if os.path.exists(PERFORMANCE_FILE):
        try:
            with open(PERFORMANCE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load performance history: {e}")
    return []


def load_ideas():
    """Load existing ideas."""
    if os.path.exists(IDEAS_FILE):
        try:
            with open(IDEAS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load ideas: {e}")
    return []


def get_recent_topics(history, limit=10):
    """Get recently used topic families from published history."""
    recent = sorted(
        history,
        key=lambda x: x.get("published_at", ""),
        reverse=True
    )[:limit]
    return [v.get("topic_family", "general") for v in recent]


def get_recent_titles(history, limit=10):
    """Get recently used titles from published history."""
    recent = sorted(
        history,
        key=lambda x: x.get("published_at", ""),
        reverse=True
    )[:limit]
    return [v.get("title", "") for v in recent if v.get("title")]


def family_on_cooldown(topic_family, history, cooldown_count=3):
    """Block reuse of topic family if it appeared in the most recent uploads."""
    recent_families = get_recent_topics(history, limit=cooldown_count)
    return topic_family in recent_families


def select_topic_family(strategy, history):
    """
    Select a topic family based on analytics data.
    Prioritizes top performers while maintaining some variety.
    """

    if not strategy or not strategy.get("top_performing_topics"):
        print("📊 No analytics data yet, using balanced selection")
        available = [
            t for t in DEFAULT_TOPICS
            if not family_on_cooldown(t, history, cooldown_count=2)
        ]
        return random.choice(available or DEFAULT_TOPICS)

    top_topics = strategy.get("top_performing_topics", [])
    suggested = strategy.get("suggested_next", DEFAULT_TOPICS)
    avoid = [t["topic"] for t in strategy.get("avoid_topics", [])]

    recent_topics = get_recent_topics(history, limit=5)

    roll = random.random()

    # 60% chance: pick from top performers
    if roll < 0.6 and top_topics:
        candidates = [
            t["topic"]
            for t in top_topics
            if t["topic"] not in recent_topics[:RECENT_FAMILY_BLOCK]
            and t["topic"] not in avoid
        ]
        if candidates:
            selected = random.choice(candidates)
            print(f"📊 Selected top performer: {selected}")
            return selected

    # 30% chance: pick from suggested
    if roll < 0.9 and suggested:
        candidates = [
            t for t in suggested
            if t not in recent_topics[:RECENT_FAMILY_BLOCK]
            and t not in avoid
        ]
        if candidates:
            selected = random.choice(candidates)
            print(f"📊 Selected from suggestions: {selected}")
            return selected

    # 10% chance: explore
    all_topics = list(TOPIC_DESCRIPTIONS.keys())
    candidates = [
        t for t in all_topics
        if t not in recent_topics[:RECENT_FAMILY_BLOCK]
        and t not in avoid
    ]
    if candidates:
        selected = random.choice(candidates)
        print(f"📊 Exploration pick: {selected}")
        return selected

    # fallback
    fallback = [t for t in DEFAULT_TOPICS if t not in avoid]
    return random.choice(fallback or DEFAULT_TOPICS)


def get_topic_guidance(topic_family):
    """Get description for the selected topic family."""
    return TOPIC_DESCRIPTIONS.get(topic_family, "interesting astrophysics facts")


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================
def build_used_text_bank(history, existing_ideas):
    """Build a bank of previously used text for dedupe checks."""
    used_entries = []

    # published history
    for item in history[-50:]:
        used_entries.append({
            "topic": item.get("topic", ""),
            "hook": item.get("hook", ""),
            "title": item.get("title", ""),
            "topic_family": item.get("topic_family", "")
        })

    # saved ideas
    for item in existing_ideas[-50:]:
        used_entries.append({
            "topic": item.get("topic", ""),
            "hook": item.get("hook", ""),
            "title": item.get("title", ""),
            "topic_family": item.get("topic_family", "")
        })

    return used_entries


def is_too_similar(new_idea, used_entries, similarity_threshold=0.65):
    """
    Reject ideas that are exact duplicates or near-duplicates.
    Looks at topic, hook, and title.
    """
    new_topic = new_idea.get("topic", "")
    new_hook = new_idea.get("hook", "")
    new_title = new_idea.get("title", "")
    new_family = new_idea.get("topic_family", "")

    for existing in used_entries:
        existing_topic = existing.get("topic", "")
        existing_hook = existing.get("hook", "")
        existing_title = existing.get("title", "")
        existing_family = existing.get("topic_family", "")

        # Exact match checks
        if normalize_text(new_topic) and normalize_text(new_topic) == normalize_text(existing_topic):
            print(f"⚠️ Duplicate topic detected: {new_topic}")
            return True

        if normalize_text(new_hook) and normalize_text(new_hook) == normalize_text(existing_hook):
            print(f"⚠️ Duplicate hook detected: {new_hook}")
            return True

        if normalize_text(new_title) and normalize_text(new_title) == normalize_text(existing_title):
            print(f"⚠️ Duplicate title detected: {new_title}")
            return True

        # Near-duplicate checks
        topic_sim = jaccard_similarity(new_topic, existing_topic)
        hook_sim = jaccard_similarity(new_hook, existing_hook)
        title_sim = jaccard_similarity(new_title, existing_title)

        if topic_sim >= similarity_threshold:
            print(f"⚠️ Near-duplicate topic similarity: {topic_sim:.2f}")
            return True

        if hook_sim >= similarity_threshold:
            print(f"⚠️ Near-duplicate hook similarity: {hook_sim:.2f}")
            return True

        if title_sim >= similarity_threshold:
            print(f"⚠️ Near-duplicate title similarity: {title_sim:.2f}")
            return True

        # Same family + very similar topic/hook = reject
        if new_family == existing_family and (topic_sim >= 0.45 or hook_sim >= 0.45):
            print("⚠️ Same family and too semantically close to recent idea")
            return True

    return False


# =============================================================================
# IDEA GENERATION
# =============================================================================
def call_gemini(prompt, api_key):
    """Low-level Gemini API call."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    headers = {
        "Content-Type": "application/json"
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🚀 Calling Gemini API (attempt {attempt + 1})...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 503:
                print("⚠️ Service unavailable, retrying in 5 seconds...")
                time.sleep(5)
                continue

            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]

            clean_text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)

        except requests.exceptions.RequestException as e:
            print(f"⚠️ API request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                print("❌ All retries failed")
                return None
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse response: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None

    return None


def build_prompt(topic_family, topic_guidance, history, existing_ideas):
    """Build a prompt with freshness constraints."""
    recent_titles = get_recent_titles(history, limit=8)
    recent_idea_topics = [
        idea.get("topic", "")
        for idea in existing_ideas[-8:]
        if idea.get("topic")
    ]

    avoid_list = recent_titles + recent_idea_topics
    avoid_text = "\n".join([f"- {item}" for item in avoid_list if item]) or "- None"

    prompt = f"""You are a viral astrophysics YouTube Shorts content strategist.

Generate ONE idea for a 20-second silent infographic Short about space or astrophysics.

IMPORTANT:
- Focus on this topic type: {topic_family}
- This means: {topic_guidance}
- DO NOT generate an idea similar to any recently used topic below
- Avoid near-duplicates, rephrasings, and the same scientific payoff in different wording
- Prefer a distinctly new object, paradox, measurement, phenomenon, or comparison angle

Recently used topics/titles to avoid:
{avoid_text}

Requirements:
- Hook must be attention-grabbing (question or surprising statement)
- Facts must be scientifically accurate with specific numbers
- Payoff should be surprising or thought-provoking
- Make it feel fresh and not like something commonly posted
- Do not reuse the same framing as the avoid-list items
- The title must be different in wording and concept from recent titles

Return ONLY this JSON format, no other text:
{{
    "topic": "brief topic name",
    "topic_family": "{topic_family}",
    "hook": "the opening question or statement",
    "facts": [
        "fact 1 with specific numbers",
        "fact 2 with specific numbers",
        "fact 3 with specific numbers"
    ],
    "payoff": "surprising conclusion",
    "title": "YouTube title with emoji (max 60 chars)",
    "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""
    return prompt


def generate_idea():
    """Generate a single Short idea from Gemini, informed by analytics and dedupe logic."""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment")
        return None

    strategy = load_strategy()
    history = load_performance_history()
    existing_ideas = load_ideas()
    used_entries = build_used_text_bank(history, existing_ideas)

    for generation_attempt in range(MAX_GENERATION_ATTEMPTS):
        print(f"\n🧪 Idea generation attempt {generation_attempt + 1}/{MAX_GENERATION_ATTEMPTS}")

        topic_family = select_topic_family(strategy, history)
        topic_guidance = get_topic_guidance(topic_family)

        print(f"🎯 Target topic family: {topic_family}")

        prompt = build_prompt(topic_family, topic_guidance, history, existing_ideas)
        idea = call_gemini(prompt, api_key)

        if not idea:
            continue

        # Force topic_family consistency
        idea["topic_family"] = topic_family

        # Add metadata
        idea["generated_at"] = datetime.now().isoformat()
        idea["status"] = "pending"
        idea["strategy_based"] = strategy is not None

        if is_too_similar(idea, used_entries):
            print("🔁 Idea was too similar. Retrying with a fresh generation...")
            continue

        print("✅ Idea generated successfully!")
        print(f"📝 Topic: {idea.get('topic')}")
        print(f"🎣 Hook: {idea.get('hook')}")
        return idea

    print("❌ Could not generate a fresh enough idea after multiple attempts")
    return None


# =============================================================================
# FILE MANAGEMENT
# =============================================================================
def save_idea(idea):
    """Save idea to the JSON file."""
    ideas = load_ideas()
    ideas.append(idea)

    with open(IDEAS_FILE, "w") as f:
        json.dump(ideas, f, indent=2)

    print(f"💾 Saved to {IDEAS_FILE} (total ideas: {len(ideas)})")
    return IDEAS_FILE


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("🌌 ASTRO SHORTS ENGINE - Smart Idea Generator")
    print("   Now powered by analytics + freshness controls 📊")
    print("=" * 60)
    print()

    if os.path.exists(STRATEGY_FILE):
        print("📊 Analytics data found - using smart selection")
    else:
        print("📊 No analytics yet - using balanced selection")

    print()

    idea = generate_idea()

    if idea:
        save_idea(idea)
        print()
        print("=" * 60)
        print("🎬 Idea ready for script formatting!")
        print("=" * 60)
    else:
        print()
        print("❌ Failed to generate idea. Check errors above.")
        exit(1)


if __name__ == "__main__":
    main()
