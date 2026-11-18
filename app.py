"""
Streamlit page for the AI Music Assistant.

    streamlit run app.py

This is only a front end. It calls the same recommend() function as the
command line (python -m src.main "..."), so the guardrails, the fallback
and the logging all behave exactly the same.
"""

import re

import streamlit as st

from src.ai_assistant import SONGS_PATH, catalog_values, recommend
from src.recommender import MAX_SCORE, load_songs

EXAMPLES = [
    "upbeat pop for a party",
    "calm acoustic music for studying",
    "angry music for lifting weights",
    "write my essay",
]

# One line of the AI's answer: "1. **Title** by Artist: why it fits"
PICK_LINE = re.compile(r"^\s*\d+\.\s*\*\*(.+?)\*\*[^:]*:\s*(.+)$")


def split_ai_text(ai_text: str) -> tuple:
    """Split the AI's answer into {song title: reason} and any other lines."""
    reasons, other = {}, []
    for line in ai_text.splitlines():
        match = PICK_LINE.match(line)
        if match:
            reasons[match.group(1).strip().lower()] = match.group(2).strip()
        elif line.strip():
            other.append(line.strip())
    return reasons, other


def show_sidebar() -> None:
    songs = load_songs(SONGS_PATH)
    genres, moods = catalog_values(songs)
    with st.sidebar:
        st.header("How it works")
        st.markdown(
            "1. **Input check** blocks empty, off-topic or unsafe requests.\n"
            "2. **The AI builds a profile** from your words, using only genres "
            "and moods that exist in the catalog.\n"
            "3. **A rule-based scorer retrieves** the five best-matching songs.\n"
            "4. **The AI writes the picks** using only those songs.\n"
            "5. **Grounding check** removes any song that wasn't retrieved."
        )
        st.divider()
        st.caption(f"Catalog: {len(songs)} songs · {len(genres)} genres · {len(moods)} moods")
        st.caption("If the AI is unavailable, the scorer answers on its own "
                   "and the page says so.")


def show_checks(result: dict) -> None:
    """One line per guardrail, so the checks are visible, not hidden."""
    ai_mode = result["mode"] == "ai"
    first, second, third = st.columns(3)
    first.markdown(":green[●] **Input check** passed")
    if ai_mode:
        second.markdown(":green[●] **Profile check** passed")
    else:
        second.markdown(":orange[●] **Profile** from keywords")
    if not ai_mode:
        third.markdown(":orange[●] **Fallback mode**")
    elif result["grounding_flags"]:
        third.markdown(f":orange[●] **Grounding** removed {len(result['grounding_flags'])}")
    else:
        third.markdown(":green[●] **Grounding check** passed")


def show_song(rank: int, song: dict, reason: str) -> None:
    """One retrieved song as a card: who, how well it matched, and why."""
    with st.container(border=True):
        info, score = st.columns([4, 1])
        info.markdown(f"**{rank}. {song['title']}**  \n{song['artist']}")
        info.caption(f"{song['genre']} · {song['mood']} · energy {song['energy']:.2f}")
        score.metric("Match", f"{song['score'] / MAX_SCORE:.0%}")
        st.progress(max(0.0, min(song["score"] / MAX_SCORE, 1.0)))
        if reason:
            st.write(reason)
        with st.expander(f"How it scored {song['score']:.2f} / {MAX_SCORE:.2f}"):
            for part in song["reasons"].split(", "):
                st.markdown(f"- {part}")


def show_result(result: dict) -> None:
    if result["status"] == "rejected":
        st.error(f"**Blocked by the input check.** {result['message']}")
        return

    ai_mode = result["mode"] == "ai"
    show_checks(result)
    if not ai_mode:
        st.info("The AI is unavailable, so the rule-based recommender answered "
                f"on its own.\n\nReason: {result['fallback_reason']}")

    profile = result["profile"]
    st.subheader("What I understood" if ai_mode else "What I understood (keywords only)")
    genre, mood, energy, acoustic = st.columns(4)
    genre.metric("Genre", profile["favorite_genre"] or "any")
    mood.metric("Mood", profile["favorite_mood"] or "any")
    energy.metric("Energy", f"{profile['target_energy']:.2f}")
    acoustic.metric("Acoustic", "yes" if profile["likes_acoustic"] else "no")

    st.subheader("Your picks")
    # In fallback mode the text is just the scorer's reasons, which each card
    # already shows under "How it scored".
    reasons, other = split_ai_text(result["ai_text"]) if ai_mode else ({}, [])
    for line in other:
        st.write(line)
    for rank, song in enumerate(result["retrieved"], start=1):
        show_song(rank, song, reasons.get(song["title"].lower(), ""))

    if result["grounding_flags"]:
        st.warning("The grounding check removed songs that were not retrieved: "
                   + ", ".join(result["grounding_flags"]))


def main() -> None:
    st.set_page_config(page_title="AI Music Assistant", page_icon="🎵", layout="centered")
    show_sidebar()

    st.title("🎵 AI Music Assistant")
    st.markdown("Tell me what you want to hear. I'll pick songs from the catalog "
                "and explain every choice.")

    clicked = None
    with st.form("ask"):
        text = st.text_input("What do you want to hear?", key="request",
                             placeholder="chill music for studying")
        submitted = st.form_submit_button("Find songs", type="primary")

    st.caption("Or try one of these:")
    columns = [*st.columns(2), *st.columns(2)]
    for column, example in zip(columns, EXAMPLES):
        if column.button(example, width="stretch"):
            clicked = example

    request = clicked if clicked is not None else text
    if submitted or clicked is not None:
        st.divider()
        st.markdown(f"Results for **“{request}”**" if request.strip() else "Results")
        with st.spinner("Finding songs..."):
            result = recommend(request)
        show_result(result)


main()
