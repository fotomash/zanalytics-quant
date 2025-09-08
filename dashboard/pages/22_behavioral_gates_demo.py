import streamlit as st
from dashboard.utils.plotly_gates import gate_donut, confluence_donut

st.set_page_config(page_title="Behavioral Gates Demo", page_icon="🧭", layout="wide")
st.markdown("# 🧭 Behavioral Gates — Demo")
st.caption("Mock values to preview gate donuts and composite confluence")

c1, c2 = st.columns(2)
with c1:
    d = st.slider("Discipline", 0, 100, 62)
    p = st.slider("Patience", 0, 100, 48)
    v = st.slider("Conviction", 0, 100, 73)
    e = st.slider("Efficiency", 0, 100, 55)
    thr = st.slider("Threshold", 40, 90, 70)
with c2:
    st.info("Tip: red <50, amber 50–69, green ≥70. Threshold tick marks desired minimum.")

gates = {"Discipline": d, "Patience": p, "Conviction": v, "Efficiency": e}

gc1, gc2, gc3, gc4, gc5 = st.columns(5)
with gc1:
    st.plotly_chart(gate_donut(title='Discipline', score=d, threshold=thr, subtitle='Watch impulsive behavior' if d < thr else None), use_container_width=True, config={'displayModeBar': False})
with gc2:
    st.plotly_chart(gate_donut(title='Patience', score=p, threshold=thr, subtitle='Tempo high' if p < thr else None), use_container_width=True, config={'displayModeBar': False})
with gc3:
    st.plotly_chart(gate_donut(title='Conviction', score=v, threshold=thr, subtitle='Limit size' if v < thr else None), use_container_width=True, config={'displayModeBar': False})
with gc4:
    st.plotly_chart(gate_donut(title='Efficiency', score=e, threshold=thr, subtitle='Improve capture' if e < thr else None), use_container_width=True, config={'displayModeBar': False})
with gc5:
    st.plotly_chart(confluence_donut(title='Confluence', gates=gates), use_container_width=True, config={'displayModeBar': False})

