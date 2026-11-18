import csv
import math
from dataclasses import asdict, dataclass
from typing import List, Dict, Tuple

# Scoring weights
# (Tried genre 1.0 / energy 3.0 as an experiment, see "Weight experiment" in model_card.md)
GENRE_WEIGHT = 2.0
MOOD_WEIGHT = 1.0
ENERGY_WEIGHT = 1.5
ACOUSTIC_WEIGHT = 0.5
ENERGY_SIGMA = 0.15
MAX_SCORE = GENRE_WEIGHT + MOOD_WEIGHT + ENERGY_WEIGHT + ACOUSTIC_WEIGHT

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP wrapper around the same scoring logic as recommend_songs.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the k best-matching songs, highest score first."""
        prefs = asdict(user)
        ranked = sorted(self.songs, key=lambda song: score_song(prefs, asdict(song))[0],
                        reverse=True)
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return the reasons this song scored the way it did for this user."""
        score, reasons = score_song(asdict(user), asdict(song))
        return f"Score {score:.2f} / {MAX_SCORE:.2f}: " + ", ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """Read songs from a CSV file into a list of dicts, converting number columns to int/float."""
    float_fields = ["energy", "tempo_bpm", "valence", "danceability", "acousticness"]

    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["id"] = int(row["id"])
            for field in float_fields:
                row[field] = float(row[field])
            songs.append(row)

    print(f"Loaded {len(songs)} songs from {csv_path}")
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song against the user's preferences and return (score, reasons)."""
    score = 0.0
    reasons = []

    # Genre match (ignore capital letters and extra spaces)
    if song["genre"].strip().lower() == user_prefs["favorite_genre"].strip().lower():
        score += GENRE_WEIGHT
        reasons.append(f"genre matches ({song['genre']}) +{GENRE_WEIGHT:.1f}")

    # Mood match (ignore capital letters and extra spaces)
    if song["mood"].strip().lower() == user_prefs["favorite_mood"].strip().lower():
        score += MOOD_WEIGHT
        reasons.append(f"mood matches ({song['mood']}) +{MOOD_WEIGHT:.1f}")

    # Energy closeness: up to ENERGY_WEIGHT (the closer to the target, the more points)
    distance = song["energy"] - user_prefs["target_energy"]
    energy_points = ENERGY_WEIGHT * math.exp(-(distance ** 2) / (2 * ENERGY_SIGMA ** 2))
    score += energy_points
    reasons.append(f"energy {song['energy']:.2f} vs target {user_prefs['target_energy']:.2f} +{energy_points:.2f}")

    # Acoustic fit
    if user_prefs["likes_acoustic"] and song["acousticness"] >= 0.6:
        score += ACOUSTIC_WEIGHT
        reasons.append(f"acoustic sound +{ACOUSTIC_WEIGHT:.1f}")
    elif not user_prefs["likes_acoustic"] and song["acousticness"] < 0.4:
        score += ACOUSTIC_WEIGHT
        reasons.append(f"non-acoustic sound +{ACOUSTIC_WEIGHT:.1f}")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score every song and return the top k as (song, score, explanation), highest first."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        scored.append((song, score, ", ".join(reasons)))

    return sorted(scored, key=lambda item: item[1], reverse=True)[:k]
