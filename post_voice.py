"""Narrow regression checks, not an AI detector or a substitute for editing."""
import json
from pathlib import Path
import re
import unicodedata

FEEDBACK = Path(__file__).parent / 'content' / 'rejected_posts.json'


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).lower().replace('’', "'").split())


def lint(text):
    reasons = []
    normalized = normalize(text)
    for item in json.loads(FEEDBACK.read_text()):
        if normalized == normalize(item['text']):
            reasons.append('rejected editorial example: ' + item['date'])
            break

    # The observed Nov 3–5 formula. A question, uncertainty or short opener on its
    # own is fine. Flag their combined boilerplate structure, not isolated words.
    paragraphs = [normalize(p) for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    if len(paragraphs) >= 3:
        short_opener = len(paragraphs[0].split()) <= 12
        cautious_narrator = re.search(
            r"\bi(?:'d| would)\s+(?:(?:still|just|probably)\s+)?(?:check|watch|be nervous)\b",
            ' '.join(paragraphs[1:-1]),
        )
        closing_prompt = re.match(r'(?:anyone\b|how do you\b|who(?:\'s| is)\b|what would you\b)', paragraphs[-1])
        if short_opener and cautious_narrator and closing_prompt and paragraphs[-1].endswith('?'):
            reasons.append('formula: short opener + hypothetical caution + audience question; choose a substantive angle')
    return reasons
