"""
Idea Generator Agent - SMART VERSION
Generates astrophysics YouTube Shorts ideas using Gemini API.
Now uses analytics data to prioritize winning topic types!
"""

import os
import json
import random
import requests
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


# =============================================================================
# ANALYTICS INTEGRATION
# =============================================================================
def load_strategy():
    """Load the current strategy from analytics."""
    if os.path.exists(STRATEGY_FILE):
        try:
            with open(STRATEGY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load strategy: {e}")
    return None


def load_performance_history():
    """Load past video performance."""
    if os.path.exists(PERFORMANCE_FILE):
        try:
            with open(PERFORMANCE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load performance history: {e}")
    return []


def get_recent_topics(history, limit=10):
    """Get recently used topics to avoid repetition."""
    recent = sorted(history, key=lambda x: x.get('published_at', ''), reverse=True)[:limit]
    return [v.get('topic_family', 'general') for v in recent]


def select_topic_family(strategy, history):
    """
    Select a topic family based on analytics data.
    Prioritizes top performers while maintaining some variety.
    """
    
    # If no strategy yet, use defaults with randomness
    if not strategy or not strategy.get('top_performing_topics'):
        print("📊 No analytics data yet, using balanced selection")
        return random.choice(DEFAULT_TOPICS)
    
    top_topics = strategy.get('top_performing_topics', [])
    suggested = strategy.get('suggested_next', DEFAULT_TOPICS)
    avoid = [t['topic'] for t in strategy.get('avoid_topics', [])]
    
    # Get recent topics to avoid repetition
    recent_topics = get_recent_topics(history, limit=5)
    
    # Build weighted selection
    # 60% chance: pick from top performers
    # 30% chance: pick from suggested
    # 10% chance: try something new (exploration)
    
    roll = random.random()
    
    if roll < 0.6 and top_topics:
        # Pick from top performers
        candidates = [t['topic'] for t in top_topics if t['topic'] not in recent_topics[-2:]]
        if candidates:
            selected = random.choice(candidates)
            print(f"📊 Selected top performer: {selected}")
            return selected
    
    if roll < 0.9 and suggested:
        # Pick from suggested
        candidates = [t for t in suggested if t not in recent_topics[-2:] and t not in avoid]
        if candidates:
            selected = random.choice(candidates)
            print(f"📊 Selected from suggestions: {selected}")
            return selected
    
    # Exploration: try something potentially new
    all_topics = list(TOPIC_DESCRIPTIONS.keys())
    candidates = [t for t in all_topics if t not in recent_topics[-3:] and t not in avoid]
    if candidates:
        selected = random.choice(candidates)
        print(f"📊 Exploration pick: {selected}")
        return selected
    
    # Fallback
    return random.choice(DEFAULT_TOPICS)


def get_topic_guidance(topic_family):
    """Get description for the selected topic family."""
    return TOPIC_DESCRIPTIONS.get(topic_family, "interesting astrophysics facts")


# =============================================================================
# IDEA GENERATION
# =============================================================================
def generate_idea():
    """Generate a single Short idea from Gemini, informed by analytics."""
    
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment")
        return None
    
    # Load analytics data
    strategy = load_strategy()
    history = load_performance_history()
    
    # Select topic family based on performance
    topic_family = select_topic_family(strategy, history)
    topic_guidance = get_topic_guidance(topic_family)
    
    print(f"🎯 Target topic family: {topic_family}")
    
    # Build the prompt with topic guidance
    prompt = f"""You are a viral astrophysics YouTube Shorts content strategist.

Generate ONE idea for a 20-second silent infographic Short about space or astrophysics.

IMPORTANT: Focus on this topic type: {topic_family}
This means: {topic_guidance}

Requirements:
- Hook must be attention-grabbing (question or surprising statement)
- Facts must be scientifically accurate with specific numbers
- Payoff should be surprising or thought-provoking
- Make it feel fresh and not like something commonly posted

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

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Retry logic for API calls
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🚀 Calling Gemini API (attempt {attempt + 1})...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 503:
                print(f"⚠️ Service unavailable, retrying in 5 seconds...")
                import time
                time.sleep(5)
                continue
                
            response.raise_for_status()
            
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            
            # Clean up and parse
            clean_text = text.replace('```json', '').replace('```', '').strip()
            idea = json.loads(clean_text)
            
            # Add metadata
            idea['generated_at'] = datetime.now().isoformat()
            idea['status'] = 'pending'
            idea['strategy_based'] = strategy is not None
            
            print("✅ Idea generated successfully!")
            print(f"📝 Topic: {idea.get('topic')}")
            print(f"🎣 Hook: {idea.get('hook')}")
            
            return idea
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ API request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                import time
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


# =============================================================================
# FILE MANAGEMENT
# =============================================================================
def load_ideas():
    """Load existing ideas."""
    if os.path.exists(IDEAS_FILE):
        try:
            with open(IDEAS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return []


def save_idea(idea):
    """Save idea to the JSON file."""
    ideas = load_ideas()
    ideas.append(idea)
    
    with open(IDEAS_FILE, 'w') as f:
        json.dump(ideas, f, indent=2)
    
    print(f"💾 Saved to {IDEAS_FILE} (total ideas: {len(ideas)})")
    return IDEAS_FILE


def check_duplicate(idea, existing_ideas, threshold=0.8):
    """Check if idea is too similar to existing ones."""
    new_topic = idea.get('topic', '').lower()
    new_hook = idea.get('hook', '').lower()
    
    for existing in existing_ideas[-20:]:  # Check last 20 ideas
        existing_topic = existing.get('topic', '').lower()
        existing_hook = existing.get('hook', '').lower()
        
        # Simple similarity check
        if new_topic == existing_topic:
            return True
        if new_hook == existing_hook:
            return True
    
    return False


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("🌌 ASTRO SHORTS ENGINE - Smart Idea Generator")
    print("   Now powered by analytics! 📊")
    print("=" * 60)
    print()
    
    # Check for strategy file
    if os.path.exists(STRATEGY_FILE):
        print("📊 Analytics data found - using smart selection")
    else:
        print("📊 No analytics yet - using balanced selection")
    
    print()
    
    # Generate idea
    idea = generate_idea()
    
    if idea:
        # Check for duplicates
        existing = load_ideas()
        if check_duplicate(idea, existing):
            print("⚠️ Similar idea exists, generating another...")
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
