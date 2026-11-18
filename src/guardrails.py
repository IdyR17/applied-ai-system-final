"""
Guardrails that keep the AI music assistant safe and grounded.

  validate_request  - before the AI: empty, too long, off-topic, injection
  validate_profile  - after parse_request: valid JSON, genre/mood in the catalog
  check_grounding   - after generation: strip any song that wasn't retrieved
"""

import json
import re
from typing import Dict, Iterable, List, Tuple, Union

MAX_REQUEST_CHARS = 300

# Words that suggest the request is about music. Catalog genres and moods
# are added on top of this list by the caller.
MUSIC_KEYWORDS = {
    "music", "song", "songs", "track", "tracks", "playlist", "album", "artist",
    "band", "listen", "listening", "tune", "tunes", "beat", "beats", "vibe",
    "vibes", "sound", "genre", "mood", "recommend", "recommendation",
    # moods / feelings
    "chill", "calm", "relax", "relaxing", "happy", "sad", "angry", "upbeat",
    "mellow", "energetic", "hype", "romantic", "peaceful", "moody", "intense",
    # activities people pick music for
    "study", "studying", "focus", "workout", "gym", "lifting", "running", "run",
    "party", "dance", "dancing", "sleep", "drive", "driving", "road", "trip",
    "dinner", "date", "morning", "rainy", "coding", "work", "working",
    # styles
    "acoustic", "electronic", "instrumental", "rap", "piano", "guitar",
}

# Phrases that try to override the system's instructions.
INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (all |any |the )?(previous|prior|above)",
    r"system prompt",
    r"you are now",
    r"pretend (to be|you are)",
]

PROFILE_KEYS = ("favorite_genre", "favorite_mood", "target_energy", "likes_acoustic")


def validate_request(text: str, extra_keywords: Iterable[str] = ()) -> Tuple[bool, str]:
    """Check a user request before it reaches the AI. Returns (ok, message)."""
    if text is None or not text.strip():
        return False, "Please type a music request, for example: 'chill music for studying'."

    if len(text) > MAX_REQUEST_CHARS:
        return False, (f"That request is {len(text)} characters long. Please keep it under "
                       f"{MAX_REQUEST_CHARS} characters, like 'upbeat pop for a party'.")

    lowered = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return False, ("I can only help with music recommendations. "
                           "Try describing the kind of music you want.")

    keywords = MUSIC_KEYWORDS | {k.lower() for k in extra_keywords}
    words = set(re.findall(r"[a-z&\-]+", lowered))
    multiword_hit = any(" " in k and k in lowered for k in keywords)
    if not (words & keywords) and not multiword_hit:
        return False, ("I'm a music assistant, so I can only recommend songs. "
                       "Try something like 'calm acoustic music for studying'.")

    return True, "ok"


def _to_bool(value) -> Union[bool, None]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    return None


def validate_profile(raw: Union[str, Dict], genres: List[str],
                     moods: List[str]) -> Tuple[bool, Union[Dict, List[str]]]:
    """
    Check the AI's profile output. Accepts the raw reply string or a dict.
    Returns (True, clean_profile) or (False, list_of_errors).
    """
    if isinstance(raw, str):
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return False, ["reply did not contain a JSON object"]
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as e:
            return False, [f"invalid JSON: {e.msg}"]
    elif isinstance(raw, dict):
        data = raw
    else:
        return False, ["profile must be a JSON string or dict"]

    errors = []
    missing = [k for k in PROFILE_KEYS if k not in data]
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")

    genre = str(data.get("favorite_genre", "")).strip().lower()
    mood = str(data.get("favorite_mood", "")).strip().lower()
    if "favorite_genre" in data and genre not in genres:
        errors.append(f"genre {genre!r} is not in the catalog")
    if "favorite_mood" in data and mood not in moods:
        errors.append(f"mood {mood!r} is not in the catalog")

    energy = None
    if "target_energy" in data:
        try:
            energy = round(max(0.0, min(1.0, float(data["target_energy"]))), 2)
        except (TypeError, ValueError):
            errors.append(f"target_energy {data['target_energy']!r} is not a number")

    acoustic = _to_bool(data.get("likes_acoustic")) if "likes_acoustic" in data else None
    if "likes_acoustic" in data and acoustic is None:
        errors.append(f"likes_acoustic {data['likes_acoustic']!r} is not true/false")

    if errors:
        return False, errors

    return True, {
        "favorite_genre": genre,
        "favorite_mood": mood,
        "target_energy": energy,
        "likes_acoustic": acoustic,
    }


def check_grounding(ai_text: str, retrieved_titles: List[str],
                    all_titles: List[str]) -> Tuple[str, List[str]]:
    """
    Remove any song the AI mentions that wasn't retrieved.

    A mention is either a **bolded** title (the format we ask for, which also
    catches invented songs) or any catalog title that wasn't retrieved.
    Lines containing a flagged title are dropped.
    Returns (clean_text, flagged_titles).
    """
    allowed = {t.lower() for t in retrieved_titles}
    flagged = []

    for title in re.findall(r"\*\*(.+?)\*\*", ai_text):
        if title.strip().lower() not in allowed and title.strip() not in flagged:
            flagged.append(title.strip())

    lowered = ai_text.lower()
    for title in all_titles:
        if title.lower() not in allowed and title.lower() in lowered and title not in flagged:
            flagged.append(title)

    if not flagged:
        return ai_text, []

    kept = [line for line in ai_text.splitlines()
            if not any(f.lower() in line.lower() for f in flagged)]
    return "\n".join(kept).strip(), flagged
