"""
Streamlit page for the AI Music Assistant.

    streamlit run app.py

This is only a front end. It calls the same recommend() function as the
command line (python -m src.main "..."), so the guardrails, the fallback
and the logging all behave exactly the same.
"""

import streamlit as st

from src.ai_assistant import recommend
from src.recommender import MAX_SCORE

EXAMPLES = [
    "upbeat pop for a party",
    "calm acoustic music for studying",
    "angry music for lifting weights",
    "write my essay",
]


def show_result(result: dict) -> None:
    """Draw one recommend() result: guardrail message, profile, songs, write-up."""
    if result["status"] == "rejected":
        st.warning(f"**Blocked by the input guardrail.** {result['message']}")
        return

    if result["mode"] == "fallback":
        st.info("**Fallback mode:** the AI is unavailable, so the rule-based "
                f"recommender answered instead.\n\nReason: {result['fallback_reason']}")

    profile = result["profile"]
    label = "1. Profile the AI built" if result["mode"] == "ai" else "1. Keyword profile (no AI)"
    st.subheader(label)
    genre, mood, energy, acoustic = st.columns(4)
    genre.metric("Genre", profile["favorite_genre"] or "any")
    mood.metric("Mood", profile["favorite_mood"] or "any")
    energy.metric("Energy", f"{profile['target_energy']:.2f}")
    acoustic.metric("Acoustic", "yes" if profile["likes_acoustic"] else "no")

    st.subheader("2. Songs my scorer retrieved")
    st.dataframe(
        [
            {
                "Rank": rank,
                "Song": song["title"],
                "Artist": song["artist"],
                "Genre": song["genre"],
                "Mood": song["mood"],
                "Score": f"{song['score']:.2f} / {MAX_SCORE:.2f}",
                "Why it matched": song["reasons"],
            }
            for rank, song in enumerate(result["retrieved"], start=1)
        ],
        hide_index=True,
    )

    heading = "3. AI recommendations" if result["mode"] == "ai" else "3. Rule-based recommendations"
    st.subheader(heading)
    st.markdown(result["ai_text"])

    if result["grounding_flags"]:
        st.warning("The grounding check removed songs that were not retrieved: "
                   + ", ".join(result["grounding_flags"]))
    elif result["mode"] == "ai":
        st.caption("Grounding check passed: every song above was retrieved from the catalog.")


def main() -> None:
    st.set_page_config(page_title="AI Music Assistant", page_icon="🎵")
    st.title("🎵 AI Music Assistant")
    st.caption("Ask for music in plain English. The AI builds a profile, my scorer "
               "retrieves songs from the catalog, and the AI writes picks using only "
               "those songs.")

    st.write("Try an example:")
    clicked = None
    columns = [*st.columns(2), *st.columns(2)]
    for column, example in zip(columns, EXAMPLES):
        if column.button(example):
            clicked = example
    if clicked is not None:
        st.session_state["request"] = clicked

    with st.form("ask"):
        text = st.text_input("What do you want to hear?", key="request",
                             placeholder="chill music for studying")
        submitted = st.form_submit_button("Recommend")

    if submitted or clicked is not None:
        with st.spinner("Finding songs..."):
            result = recommend(text)
        show_result(result)


main()
