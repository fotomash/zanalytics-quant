import os
import requests
import streamlit as st


def _safe_get_json(url, timeout=4):
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def compute_session_mindset(trades=None, risk=None, limits=None):
    """
    trades: list of dicts like {'pnl': float, 'timestamp': '...'}
    risk: dict like {'daily_pnl': float, 'daily_drawdown': float, 'cooling_off_active': bool, 'cooling_until': 'HH:MM', 'loss_streak': int}
    limits: dict like {'daily_loss_limit': float (neg), 'max_trades_per_day': int}
    """
    bullets = []
    trades = trades or []
    risk = risk or {}
    limits = limits or {}

    daily_pnl = float(risk.get('daily_pnl', 0.0) or 0.0)
    daily_dd = float(risk.get('daily_drawdown', 0.0) or 0.0)
    loss_streak = int(risk.get('loss_streak', 0) or 0)
    cooling = bool(risk.get('cooling_off_active', False))
    cooling_until = risk.get('cooling_until')

    max_trades = limits.get('max_trades_per_day', 5)
    daily_loss_limit = limits.get('daily_loss_limit', -3.0)

    # Recent trades W-L and last result
    wins = sum(1 for t in trades if (t.get('pnl') or 0) > 0)
    losses = sum(1 for t in trades if (t.get('pnl') or 0) <= 0)
    last = trades[-1]['pnl'] if trades else None
    if trades:
        bullets.append(f"Recent trades: {wins}W-{losses}L • Last: {'WIN ✅' if (last or 0)>0 else 'LOSS ❌'}")
    else:
        bullets.append("No trades yet today • Patience is a position ✅")

    # Session PnL / Drawdown context
    if daily_pnl or daily_dd:
        dd_note = f"Drawdown: {daily_dd:+.2f}" if daily_dd else "Drawdown: 0.00"
        bullets.append(f"Session PnL: {daily_pnl:+.2f} • {dd_note}")

    # Limit proximity
    if daily_loss_limit is not None and daily_pnl is not None:
        remaining = abs(daily_loss_limit) - abs(min(daily_pnl, 0))
        if daily_pnl <= 0 and remaining <= abs(daily_loss_limit) * 0.2:
            bullets.append("Near daily loss limit ⚠️ • Switch to observe-only until A+ setup")

    # Cooling off
    if cooling:
        bullets.append(f"Cooling-off active 🧊 • Resume at: {cooling_until or 'later'}")
    elif loss_streak >= 2:
        bullets.append("Two consecutive losses 🚩 • Take a 15-minute reset before next decision")

    # Guidance
    guidance = [
        "Trade the plan, not the PnL. Process > outcome.",
        "Only A+ setups. Let lesser trades pass ⏳",
        "Breathe, slow down, reduce size when uncertain.",
        f"Max {max_trades} trades per day • Protect your edge."
    ]
    bullets.extend(guidance[:2 if cooling else 3])
    return bullets


def render_session_mindset_panel(django_api_url: str = None):
    dj = django_api_url or os.getenv('DJANGO_API_URL', 'http://localhost:8000') or 'http://localhost:8000'
    # If running inside Docker, prefer the internal service name
    if '://localhost' in dj and os.getenv('IN_DOCKER') == '1':
        dj = 'http://django:8000'
    risk = _safe_get_json(f"{dj}/api/pulse/risk") if dj else None
    journal = _safe_get_json(f"{dj}/api/pulse/journal/today") if dj else None
    trades = (journal or {}).get('trades', []) if journal else []
    limits = (risk or {}).get('limits', {}) if risk else {}
    bullets = compute_session_mindset(trades=trades, risk=risk, limits=limits)

    st.markdown("<h4>🧠 Session Mindset</h4>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:rgba(26,34,45,0.85);border:1px solid rgba(37,48,71,0.4);"
        "border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.6rem;'>",
        unsafe_allow_html=True
    )
    for b in bullets:
        st.markdown(f"- {b}")
    st.markdown("</div>", unsafe_allow_html=True)

