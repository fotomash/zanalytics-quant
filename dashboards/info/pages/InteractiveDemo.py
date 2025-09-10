import streamlit as st
from dashboard.utils.streamlit_api import safe_api_call
from .utils import donut_chart


def render(mock_data):
    st.title("Interactive Whisperer Demo")

    col1, col2 = st.columns(2)
    with col1:
        confluence = st.slider("Confluence", 0, 100, 50)
        st.plotly_chart(donut_chart("Confluence", confluence), use_container_width=True)
    with col2:
        risk_used = st.slider("Risk Used (%)", 0, 100, 20)
        st.plotly_chart(donut_chart("Risk", risk_used), use_container_width=True)

    st.subheader("Ask Whisperer")
    question = st.text_area("Question or journal note")
    symbol = st.text_input("Symbol", "XAUUSD")
    if st.button("Send to Whisperer") and question.strip():
        with st.spinner("Contacting Whisperer..."):
            resp = safe_api_call(
                "POST",
                "api/v1/actions/query",
                {
                    "type": "whisper_suggest",
                    "payload": {
                        "user_id": "demo",
                        "symbol": symbol,
                        "question": question,
                        "metrics": {"confluence": confluence, "risk": risk_used},
                    },
                },
                timeout=5.0,
            )
        if resp.get("error"):
            st.error(f"API error: {resp['error']}")
        else:
            if resp.get("message"):
                st.success(resp["message"])
            for h in resp.get("heuristics") or []:
                st.markdown(f"**{h.get('category', '')}:** {h.get('message', '')}")
                reasons = h.get("reasons") or []
                if reasons:
                    with st.expander("Reasons"):
                        for r in reasons:
                            st.write(f"- {r.get('key')}: {r.get('value')}")
                actions = h.get("actions") or []
                if actions:
                    st.write("Actions:")
                    for a in actions:
                        st.write(f"- {a.get('label')}")
