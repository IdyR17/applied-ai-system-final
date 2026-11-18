import pytest

from src.recommender import (MAX_SCORE, Recommender, Song, UserProfile, load_songs,
                             recommend_songs, score_song)

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_recommender_sorts_by_score_not_by_file_order():
    # The best match is last in the list, so returning songs[:k] would fail.
    rec = make_small_recommender()
    rec.songs.reverse()
    user = UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.8, likes_acoustic=False)

    results = rec.recommend(user, k=1)

    assert [song.title for song in results] == ["Test Pop Track"]


def test_explain_recommendation_gives_the_real_reasons():
    rec = make_small_recommender()
    user = UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.8, likes_acoustic=False)

    explanation = rec.explain_recommendation(user, rec.songs[0])

    assert "genre matches (pop)" in explanation
    assert "mood matches (happy)" in explanation


# ---------------------------------------------------------------- the retriever

POP_FAN = {"favorite_genre": "pop", "favorite_mood": "happy",
           "target_energy": 0.82, "likes_acoustic": False}
POP_SONG = {"genre": "pop", "mood": "happy", "energy": 0.82, "acousticness": 0.18}


def test_score_song_perfect_match_gets_max_score():
    score, reasons = score_song(POP_FAN, POP_SONG)
    assert score == pytest.approx(MAX_SCORE)
    assert len(reasons) == 4


def test_score_song_ignores_capital_letters_and_spaces():
    shouty = {**POP_FAN, "favorite_genre": " Pop ", "favorite_mood": "HAPPY"}
    assert score_song(shouty, POP_SONG)[0] == pytest.approx(MAX_SCORE)


def test_score_song_closer_energy_scores_higher():
    near = {**POP_SONG, "energy": 0.80}
    far = {**POP_SONG, "energy": 0.30}
    assert score_song(POP_FAN, near)[0] > score_song(POP_FAN, far)[0]


def test_score_song_wrong_genre_loses_the_genre_points():
    rock = {**POP_SONG, "genre": "rock"}
    assert score_song(POP_FAN, POP_SONG)[0] - score_song(POP_FAN, rock)[0] == pytest.approx(2.0)


def test_recommend_songs_returns_top_k_highest_first():
    songs = load_songs("data/songs.csv")
    results = recommend_songs(POP_FAN, songs, k=5)
    scores = [score for _, score, _ in results]

    assert len(results) == 5
    assert scores == sorted(scores, reverse=True)
    assert results[0][0]["title"] == "Sunrise City"


def test_recommend_songs_unknown_genre_still_returns_songs():
    songs = load_songs("data/songs.csv")
    k_pop_fan = {**POP_FAN, "favorite_genre": "k-pop"}
    assert len(recommend_songs(k_pop_fan, songs, k=5)) == 5
