import time
import requests
import streamlit as st
from dashboard.utils.streamlit_api import api_url


def render_whisper_panel():
    st.subheader("🫢 The Whisperer")
    try:
        data = requests.get(api_url("api/pulse/whispers"), timeout=2).json().get("whispers", [])
    except Exception:
        st.info("No whispers yet.")
        return

    if not data:
        st.info("No whispers yet.")
        return

    for w in data[:20]:
        with st.container(border=True):
            left, right = st.columns([0.8, 0.2])
            with left:
                st.write(f"**{w.get('message','')}**")
                cat = w.get("category", ""); sev = w.get("severity", "")
                ts = time.strftime('%H:%M:%S', time.localtime(w.get("ts", time.time())))
                st.caption(f"{cat} • {sev} • {ts}")
                reasons = w.get("reasons") or []
                if reasons:
                    with st.expander("Why this?"):
                        for r in reasons:
                            k = r.get('key'); v = r.get('value')
                            st.write(f"- `{k}`: {v}")
            with right:
                for a in (w.get("actions") or []):
                    label = a.get("label", "Action")
                    act = a.get("action", "")
                    if st.button(label, key=f"{w.get('id','')}:{act}"):
                        try:
                            # Journal intent
                            requests.post(api_url("api/pulse/whisper/ack"), json={"id": w.get("id"), "reason": label}, timeout=2)
                            if act:
                                requests.post(api_url("api/pulse/whisper/act"), json={"id": w.get("id"), "action": act}, timeout=2)
                            st.toast(f"Ack: {label}")
                        except Exception:
                            st.warning("Could not reach whisper endpoints")
