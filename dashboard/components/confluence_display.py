import streamlit as st

ICON_MAP = {
    "wyckoff": "\U0001F9E0",  # 🧠
    "smc": "\U0001F4A7",      # 💧
    "macro": "\U0001F30D",    # 🌍
    "volatility": "\u26A1",   # ⚡
}


def _status(score: float):
    """Return colour and emoji for a score (0-100)."""
    if score >= 75:
        return "#22C55E", "\u2705"  # green, check
    if score >= 50:
        return "#FACC15", "\u26A0\uFE0F"  # yellow, warning
    return "#EF4444", "\u274C"  # red, cross


def render_confluence_gates(scores: dict, weights: dict):
    """Render a confluence meter and per-gate breakdown.

    Parameters
    ----------
    scores : dict
        Mapping of gate name -> score in range 0..100.
    weights : dict
        Mapping of gate name -> weight (typically 0..1).
    """
    total = 0.0
    for g, w in weights.items():
        try:
            total += float(scores.get(g, 0)) * float(w)
        except Exception:
            continue

    colour, _ = _status(total)
    angle = max(0.0, min(100.0, total)) / 100 * 360

    meter = f"""
    <div style='display:flex;flex-direction:column;align-items:center;'>
        <div style='position:relative;width:150px;height:150px;'>
            <div style='
                width:150px;height:150px;border-radius:50%;
                background:conic-gradient({colour} {angle}deg, rgba(255,255,255,0.08) {angle}deg);
            '></div>
            <div style='
                position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                width:90px;height:90px;border-radius:50%;
                background:#0F172A;
                display:flex;flex-direction:column;align-items:center;justify-content:center;
            '>
                <span style='font-size:20px;font-weight:600;color:#F1F5F9;'>{total:.0f}%</span>
                <span style='font-size:12px;color:#94A3B8;'>CONFIDENCE</span>
            </div>
        </div>
    </div>
    """
    st.markdown(meter, unsafe_allow_html=True)

    for gate in weights:
        score = float(scores.get(gate, 0))
        weight = float(weights.get(gate, 0))
        color, emoji = _status(score)
        icon = ICON_MAP.get(gate, "")
        st.markdown(
            f"""
            <div style='display:flex;align-items:center;padding:8px 12px;margin-bottom:8px;background:rgba(255,255,255,0.05);border-left:5px solid {color};border-radius:4px;'>
                <div style='font-size:20px;margin-right:8px;'>{icon}</div>
                <div style='flex:1;'>
                    <div style='font-size:14px;font-weight:600;color:#F1F5F9;text-transform:capitalize;'>{gate}</div>
                    <div style='font-size:12px;color:#94A3B8;'>weight {weight:.2f}</div>
                </div>
                <div style='font-size:14px;font-weight:700;color:{color};'>
                    {score:.0f}% {emoji}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

