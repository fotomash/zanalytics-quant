import streamlit as st
import yaml
from pathlib import Path

ICON_MAP = {
    "wyckoff": "\U0001F9E0",  # 🧠
    "smc": "\U0001F4A7",  # 💧
    "macro": "\U0001F30D",  # 🌍
    "volatility": "\u26A1",  # ⚡
}


def _status(score: float):
    """Return colour and emoji for a score (0-100)."""

    if score >= 75:
        return "#22C55E", "\u2705"  # green, check
    if score >= 50:
        return "#FACC15", "\u26A0\uFE0F"  # yellow, warning
    return "#EF4444", "\u274C"  # red, cross


def render_confluence_gates(scores: dict, weights: dict):
    """Render the 'Pac-Man' style confluence score visualization."""

    st.subheader("🚦 Confluence Gates")

    # Wyckoff is KING: If Wyckoff score is below a threshold, the trade is a no-go.
    wyckoff_score = float(scores.get("wyckoff", 0))
    wyckoff_threshold = 50
    is_valid_setup = wyckoff_score >= wyckoff_threshold

    total_score = 0.0
    for gate, weight in weights.items():
        try:
            total_score += float(scores.get(gate, 0)) * float(weight)
        except Exception:
            continue
    if not is_valid_setup:
        total_score = wyckoff_score

    colour = "#00D1FF" if is_valid_setup else "#FF2B2B"
    percent = max(0.0, min(100.0, total_score))

    meter = f"""
    <div style='display:flex;flex-direction:column;align-items:center;'>
        <div style='position:relative;width:150px;height:150px;'>
            <div style='
                width:150px;height:150px;border-radius:50%;
                background:conic-gradient({colour} {percent}%, #2b3042 {percent}%);
            '></div>
            <div style='
                position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                width:90px;height:90px;border-radius:50%;
                background:#0F172A;
                display:flex;flex-direction:column;align-items:center;justify-content:center;
            '>
                <span style='font-size:20px;font-weight:600;color:#F1F5F9;'>{total_score:.0f}%</span>
                <span style='font-size:12px;color:#94A3B8;'>CONFIDENCE</span>
            </div>
        </div>
    </div>
    """
    st.markdown(meter, unsafe_allow_html=True)

    for gate, weight in weights.items():
        score = float(scores.get(gate, 0))
        color, emoji = _status(score)
        icon = ICON_MAP.get(gate, "")
        is_king_gate = gate == "wyckoff"
        gate_label = (
            f"👑 {gate.replace('_', ' ').title()}"
            if is_king_gate
            else gate.replace("_", " ").title()
        )
        st.markdown(
            f"""
            <div style='display:flex;align-items:center;padding:8px 12px;margin-bottom:8px;background:rgba(255,255,255,0.05);border-left:5px solid {color};border-radius:4px;'>
                <div style='font-size:20px;margin-right:8px;'>{icon}</div>
                <div style='flex:1;'>
                    <div style='font-size:14px;font-weight:600;color:#F1F5F9;text-transform:capitalize;'>{gate_label}</div>
                    <div style='font-size:12px;color:#94A3B8;'>weight {float(weight):.2f}</div>
                </div>
                <div style='font-size:14px;font-weight:700;color:{color};'>
                    {score:.0f}% {emoji}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def get_confluence_weights(path: str | Path | None = None) -> dict:
    """Load confluence weights from hybrid_confluence.yaml."""

    if path is None:
        path = (
            Path(__file__).resolve().parents[2]
            / "knowledge"
            / "strategies"
            / "hybrid_confluence.yaml"
        )

    try:
        data = yaml.safe_load(Path(path).read_text()) or {}
        return data.get("confluence_weights", {}) or {}
    except Exception:
        return {}


__all__ = ["render_confluence_gates", "get_confluence_weights"]

