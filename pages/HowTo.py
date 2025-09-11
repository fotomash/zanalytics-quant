import streamlit as st


def render(mock_data):
    """Display guidance on using Confluence Scorer and Whisperer."""
    st.title("How To")

    st.subheader("Confluence Scorer Usage")
    st.write(
        "Use the Confluence Scorer to weigh technical, behavioral, and risk inputs. "
        "Scores above 80 suggest acting; 50-80 warrant caution; below 50 mean stand down."
    )

    st.subheader("Whisperer Interaction Tips")
    st.write(
        "Be direct and contextual. Ask about signal, risk, and action in one prompt, "
        "and let Whisperer return structured guidance and journal notes."
    )
