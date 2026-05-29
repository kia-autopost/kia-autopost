"""
Content Generator — calls Claude API to pick a random scripture
and generate the caption, hashtags, and verse text for each post.
"""
import random, requests, json

VERSES = {
    'Wisdom':     ["James 3:17-18","Proverbs 3:13-14","Proverbs 4:7","James 1:5","Proverbs 9:10","Ecclesiastes 7:12"],
    'Faith':      ["Hebrews 11:1","Mark 11:24","Romans 10:17","Matthew 17:20","Galatians 2:20","2 Corinthians 5:7"],
    'Grace':      ["Ephesians 2:8-9","2 Corinthians 12:9","Romans 5:20","Titus 2:11","Hebrews 4:16"],
    'Peace':      ["Philippians 4:7","John 14:27","Isaiah 26:3","Colossians 3:15","Psalm 23:1-3"],
    'Hope':       ["Romans 15:13","Jeremiah 29:11","Hebrews 6:19","Psalm 31:24","Isaiah 40:31"],
    'Love':       ["1 Corinthians 13:4-7","John 3:16","1 John 4:19","Romans 8:38-39","John 15:13"],
    'Forgiveness':["Ephesians 4:32","Matthew 6:14","Colossians 3:13","1 John 1:9","Psalm 103:12"],
    'Strength':   ["Philippians 4:13","Isaiah 40:31","Psalm 46:1","2 Timothy 1:7","Nehemiah 8:10"],
    'Gratitude':  ["1 Thessalonians 5:18","Colossians 3:17","Psalm 100:4-5","Philippians 4:6","James 1:17"],
    'Prayer':     ["Matthew 6:9-13","Philippians 4:6-7","1 Thessalonians 5:17","James 5:16","Matthew 7:7"],
    'Community':  ["Hebrews 10:24-25","Acts 2:42-44","Romans 12:4-5","Galatians 6:2","Matthew 18:20"],
    'Purpose':    ["Jeremiah 29:11","Romans 8:28","Ephesians 2:10","Proverbs 19:21","Philippians 1:6"],
}

_last_themes = []

def _pick_topic():
    global _last_themes
    themes = list(VERSES.keys())
    # Avoid repeating the last 4 themes
    available = [t for t in themes if t not in _last_themes[-4:]]
    if not available:
        available = themes
    theme = random.choice(available)
    _last_themes.append(theme)
    ref   = random.choice(VERSES[theme])
    return theme, ref

def generate_post(slot: str, api_key: str, translation: str = 'ERV (Easy-to-Read Version)') -> dict:
    """
    Returns dict with keys:
      theme, verse_ref, verse_text, caption, hashtags
    """
    theme, ref = _pick_topic()
    angle = 'energising morning tone' if slot == 'Morning' else 'calm reflective evening tone'

    prompt = f"""You are creating content for Kingdom In Action, a Christian church Instagram page.
Generate ONE reel post. Return ONLY a raw JSON object — no markdown, no backticks, nothing else.

Theme: {theme}
Scripture: {ref}
Tone: peaceful and reflective, {angle}
Translation: {translation}

{{"verse_ref":"{ref}","verse_text":"full verse text in {translation}","theme":"{theme}","caption":"2-3 short sentences on the theme. All Glory To God","hashtags":"#KingdomInAction #AllGloryToGod #{theme.replace(' ','')} #DailyScripture #BibleVerse #FaithDaily #WordOfGod #GodIsGood #ChristianContent #DailyWord"}}"""

    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        json={
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': 500,
            'messages': [{'role': 'user', 'content': prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise ValueError(f"Claude API error: {data['error']}")

    raw   = data['content'][0]['text'].strip()
    raw   = raw.replace('```json','').replace('```','').strip()
    s, e  = raw.index('{'), raw.rindex('}')
    result = json.loads(raw[s:e+1])
    result['theme'] = theme
    return result
