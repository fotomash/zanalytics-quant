import streamlit as st


def chip(text: str, kind: str = 'neutral'):
    """Render a colored pill with ``text``.

    Parameters
    ----------
    text: str
        Content of the pill.
    kind: str
        One of ``good``, ``warn``, ``bad`` or ``neutral`` to select colours.
    """
    bg = {'good': '#dcfce7', 'warn': '#fef9c3', 'bad': '#fee2e2', 'neutral': '#f3f4f6'}.get(kind, '#f3f4f6')
    color = {'good': '#166534', 'warn': '#854d0e', 'bad': '#991b1b', 'neutral': '#374151'}.get(kind, '#374151')
    st.markdown(
        f"<span style='background:{bg}; color:{color}; padding:6px 10px; border-radius:999px; font-size:12px; margin-right:6px;display:inline-block;'>{text}</span>",
        unsafe_allow_html=True,
    )
