import math
import plotly.graph_objects as go

COL = {
    "pos": "#22C55E",
    "neg": "#EF4444",
    "warn": "#F59E0B",
    "info": "#3B82F6",
    "cyan": "#22D3EE",
    "track": "rgba(148, 163, 184, 0.28)",
    "base": "rgba(15, 23, 42, 0)",
    # Dark-theme tracks
    "base_dark": "#1F2937",
    "ghost_dark": "#374151",
}


def _bipolar_slice(value, cap=1.0):
    if value is None:
        return 0.0, "clockwise", COL["track"], "awaiting feed"
    v = max(-cap, min(cap, float(value)))
    frac = abs(v) / cap
    deg = 360.0 * frac
    color = COL["pos"] if v >= 0 else COL["neg"]
    direction = "clockwise" if v >= 0 else "counterclockwise"
    return deg, direction, color, f"{v:.2f} of ±{cap:.2f}"


def _unipolar_slice(value, cap=1.0, color=COL["info"]):
    if value is None:
        return 0.0, "clockwise", COL["track"], "awaiting feed"
    v = max(0.0, min(cap, float(value)))
    deg = 360.0 * (v / cap)
    return deg, "clockwise", color, f"{v:.2f}/{cap:.2f}"


def _semicircle_split(left_frac, right_frac, colors=("rgba(239,68,68,0.95)", "rgba(34,197,94,0.95)")):
    l = 0.0 if left_frac is None else max(0.0, min(1.0, float(left_frac)))
    r = 0.0 if right_frac is None else max(0.0, min(1.0, float(right_frac)))
    return (180 * l, colors[0], "realized"), (180 * r, colors[1], "unrealized")


def concentric_ring(
    center_title: str,
    center_value: str,
    caption: str = "",
    # Outer
    outer_bipolar=None,
    outer_cap=1.0,
    outer_ghost_bipolar=None,
    # Middle
    middle_mode="unipolar",
    middle_val=None,
    middle_cap=1.0,
    middle_split=(None, None),
    # Inner
    inner_unipolar=None,
    inner_cap=1.0,
    size=(280, 280),
    rotation_deg=270,
    # Overlays
    ticks=None,
    cap_dots=True,
    petals=None,  # list of {side:'long|short', notional_pct:0..1, minutes_open:int}
    fade_tail=None,  # list of floats in [-1,1] segments indicating recent change
):
    fig = go.Figure()

    # Outer ring (bipolar)
    out_deg, out_dir, out_col, out_hover = _bipolar_slice(outer_bipolar, cap=outer_cap)
    fig.add_trace(
        go.Pie(
            values=[out_deg, 360 - out_deg],
            hole=0.58,
            direction=out_dir,
            sort=False,
            rotation=rotation_deg,
            marker=dict(colors=[out_col, COL["track"]], line=dict(color="rgba(0,0,0,0)", width=0)),
            textinfo="none",
            hoverinfo="text",
            hovertext=[out_hover, ""],
            showlegend=False,
            name="outer",
        )
    )

    # Outer ghost track (e.g., yesterday close) as a thin overlay arc
    if outer_ghost_bipolar is not None:
        g_deg, g_dir, g_col, g_hover = _bipolar_slice(outer_ghost_bipolar, cap=outer_cap)
        fig.add_trace(
            go.Pie(
                values=[g_deg, 360 - g_deg],
                hole=0.60,  # slightly larger hole -> thin arc overlay
                rotation=rotation_deg,
                sort=False,
                direction=g_dir,
                marker=dict(colors=[COL["ghost_dark"], "rgba(0,0,0,0)"]),
                textinfo="none",
                hoverinfo="text",
                hovertext=[f"ghost: {g_hover}", ""],
                showlegend=False,
                name="outer_ghost",
                opacity=0.35,
            )
        )

    # Middle ring
    if middle_mode == "split":
        (l_deg, l_col, l_label), (r_deg, r_col, r_label) = _semicircle_split(*middle_split)
        fig.add_trace(
            go.Pie(
                values=[l_deg, 180 - l_deg, 180],
                hole=0.73,
                rotation=rotation_deg + 180,
                sort=False,
                direction="counterclockwise",
                marker=dict(colors=[l_col, COL["track"], COL["base"]]),
                textinfo="none",
                hoverinfo="text",
                hovertext=[l_label, "", ""],
                showlegend=False,
                name="mid_left",
            )
        )
        fig.add_trace(
            go.Pie(
                values=[r_deg, 180 - r_deg, 180],
                hole=0.73,
                rotation=rotation_deg,
                sort=False,
                direction="clockwise",
                marker=dict(colors=[r_col, COL["track"], COL["base"]]),
                textinfo="none",
                hoverinfo="text",
                hovertext=[r_label, "", ""],
                showlegend=False,
                name="mid_right",
            )
        )
    else:
        mid_deg, _, mid_col, mid_hover = _unipolar_slice(middle_val, cap=middle_cap, color=COL["warn"])
        fig.add_trace(
            go.Pie(
                values=[mid_deg, 360 - mid_deg],
                hole=0.73,
                rotation=rotation_deg,
                sort=False,
                direction="clockwise",
                marker=dict(colors=[mid_col, COL["track"]]),
                textinfo="none",
                hoverinfo="text",
                hovertext=[mid_hover, ""],
                showlegend=False,
                name="middle",
            )
        )

    # Inner ring (unipolar)
    in_deg, _, in_col, in_hover = _unipolar_slice(inner_unipolar, cap=inner_cap, color=COL["info"])
    # Color hint: green if >=0.5 else red
    if inner_unipolar is not None:
        in_col = COL["pos"] if float(inner_unipolar) >= 0.5 else COL["neg"]
    fig.add_trace(
        go.Pie(
            values=[in_deg, 360 - in_deg],
            hole=0.86,
            rotation=rotation_deg,
            sort=False,
            direction="clockwise",
            marker=dict(colors=[in_col, COL["track"]]),
            textinfo="none",
            hoverinfo="text",
            hovertext=[in_hover, ""],
            showlegend=False,
            name="inner",
        )
    )

    # Center labels
    fig.add_annotation(
        text=f"<b>{center_title}</b><br>{center_value}",
        x=0.5,
        y=0.52,
        showarrow=False,
        font=dict(size=16, color="#E5E7EB"),
    )
    if caption:
        fig.add_annotation(
            text=f"<span style='font-size:12px;color:#93A3B8'>{caption}</span>",
            x=0.5,
            y=0.38,
            showarrow=False,
        )

    # ---- Marker helpers (ticks + cap dots) ----
    def _angle_to_xy(angle_deg: float, radius: float, cx: float = 0.5, cy: float = 0.5):
        # 0° at 12 o'clock, CW positive
        theta = math.radians(90.0 - angle_deg)
        return cx + radius * math.cos(theta), cy + radius * math.sin(theta)

    # Radii for the three rings (paper coords ~0..1)
    radii = {
        "outer": {"r_in": 0.58 * 0.5, "r_out": 0.5},
        "middle": {"r_in": 0.73 * 0.5, "r_out": 0.5},
        "inner": {"r_in": 0.86 * 0.5, "r_out": 0.5},
    }

    # Calculate final angles for cap dots
    def _final_angle(direction: str, deg: float, rotation: float) -> float:
        if deg <= 0:
            return rotation % 360
        return (rotation + deg) % 360 if direction == "clockwise" else (rotation - deg) % 360

    # Cap dots at arc ends (filled for positive/CW, hollow for negative/CCW)
    if cap_dots:
        # Outer
        oa = _final_angle(out_dir, out_deg, rotation_deg)
        x, y = _angle_to_xy(oa, radii["outer"]["r_out"])  # at outer edge
        rdot = 0.012
        if out_deg > 0:
            if out_dir == "clockwise":
                fig.add_shape(type="circle", xref="paper", yref="paper",
                               x0=x - rdot, x1=x + rdot, y0=y - rdot, y1=y + rdot,
                               line=dict(color=COL["pos"], width=1), fillcolor=COL["pos"], opacity=0.9)
            else:
                fig.add_shape(type="circle", xref="paper", yref="paper",
                               x0=x - rdot, x1=x + rdot, y0=y - rdot, y1=y + rdot,
                               line=dict(color=COL["neg"], width=1), fillcolor="rgba(0,0,0,0)", opacity=0.9)
        # Middle (only in unipolar mode)
        if middle_mode != "split":
            ma = _final_angle("clockwise", mid_deg, rotation_deg)
            mx, my = _angle_to_xy(ma, radii["middle"]["r_out"])  # at outer edge
            fig.add_shape(type="circle", xref="paper", yref="paper",
                           x0=mx - rdot, x1=mx + rdot, y0=my - rdot, y1=my + rdot,
                           line=dict(color=COL["warn"], width=1), fillcolor=COL["warn"], opacity=0.9)
        # Inner
        ia = _final_angle("clockwise", in_deg, rotation_deg)
        ix, iy = _angle_to_xy(ia, radii["inner"]["r_out"])  # at outer edge
        fig.add_shape(type="circle", xref="paper", yref="paper",
                       x0=ix - rdot, x1=ix + rdot, y0=iy - rdot, y1=iy + rdot,
                       line=dict(color=in_col, width=1), fillcolor=in_col, opacity=0.9)

    # Threshold ticks
    if ticks:
        for t in ticks or []:
            ring = t.get("ring", "outer")
            if ring not in radii:
                continue
            angle = t.get("angle_deg")
            if angle is None and "angle_norm" in t:
                angle = float(t["angle_norm"]) * 360.0
            if angle is None:
                continue
            color = t.get("color", COL["info"])
            dash = {"solid": None, "dashed": "dash"}.get(t.get("style", "solid"), None)
            # Draw a short radial line from slightly inside to outer edge
            r_in = radii[ring]["r_out"] - 0.04
            r_out = radii[ring]["r_out"]
            x0, y0 = _angle_to_xy(angle % 360, r_in)
            x1, y1 = _angle_to_xy(angle % 360, r_out)
            fig.add_shape(type="line", xref="paper", yref="paper",
                          x0=x0, y0=y0, x1=x1, y1=y1,
                          line=dict(color=color, width=1, dash=dash))
            if t.get("hover"):
                fig.add_annotation(x=x1, y=y1, xref="paper", yref="paper",
                                   text=t.get("hover"), showarrow=False, opacity=0.0,
                                   hovertext=t.get("hover"))

    # Position petals (tiny wedgelets around outer perimeter)
    if petals:
        # Space petals around the ring without overlap; max 8 petals practical
        max_wedge = 8.0  # degrees for 100% notional
        n = len(petals)
        for i, p in enumerate(petals[:8]):
            try:
                notional = max(0.02, min(1.0, float(p.get('notional_pct', 0.1) or 0.1)))
                side = (p.get('side') or '').lower()
                minutes = int(p.get('minutes_open', 0) or 0)
                wedge = max(2.0, notional * max_wedge)
                # Place evenly
                start_angle = (rotation_deg + (i * (360.0 / (n or 1)))) % 360
                # Color and opacity
                col = COL['pos'] if side == 'long' else COL['neg']
                opacity = max(0.35, min(0.95, (minutes / 120.0)))  # older -> more opaque
                fig.add_trace(
                    go.Pie(
                        values=[wedge, 360 - wedge],
                        hole=0.56,  # slightly thinner than outer ring
                        rotation=start_angle,
                        sort=False,
                        direction='clockwise',
                        marker=dict(colors=[col, 'rgba(0,0,0,0)']),
                        textinfo='none',
                        hoverinfo='skip',
                        showlegend=False,
                        name=f"petal_{i}",
                        opacity=opacity,
                    )
                )
            except Exception:
                continue

    # Fade tail (recent unrealized trend) as 3 short arc segments with decreasing opacity
    if isinstance(fade_tail, (list, tuple)) and len(fade_tail) > 0:
        # Use middle ring radius for the tail
        r = radii['middle']['r_out']
        segs = list(fade_tail)[:3]
        for j, seg in enumerate(segs):
            try:
                v = float(seg)
            except Exception:
                continue
            # segment length proportional to |v|, direction by sign
            length_deg = max(6.0, min(30.0, abs(v) * 90.0))
            # place tail behind the middle arc end
            end_angle = _final_angle('clockwise', mid_deg if 'mid_deg' in locals() else 0.0, rotation_deg)
            start = (end_angle - length_deg) if v >= 0 else (end_angle + length_deg)
            # draw as polyline of 6 short chords
            steps = 6
            for k in range(steps):
                a0 = start + (k * (length_deg/steps)) * (1 if v < 0 else -1)
                a1 = start + ((k+1) * (length_deg/steps)) * (1 if v < 0 else -1)
                x0, y0 = _angle_to_xy(a0, r)
                x1, y1 = _angle_to_xy(a1, r)
                fig.add_shape(type='line', xref='paper', yref='paper',
                              x0=x0, y0=y0, x1=x1, y1=y1,
                              line=dict(color=COL['cyan'], width=2), opacity=max(0.15, 0.5 - j*0.15))

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=size[1],
        width=size[0],
    )
    return fig


# Convenience builders for common donuts described in the spec
def donut_balance(
    balance_usd: float,
    pnl_since_inception_pct: float | None,
    inception_momentum_pct: float | None,
    ytd_pct: float | None = None,
    all_time_high_pct: float | None = None,
    max_drawdown_pct: float | None = None,
    breach_pct: float | None = None,
    ghost_prev_outer: float | None = None,
    size=(300, 300),
):
    # Outer: since inception bipolar
    ticks = []
    if all_time_high_pct is not None:
        ticks.append({"ring": "outer", "angle_norm": max(-1.0, min(1.0, float(all_time_high_pct))), "color": COL["pos"], "style": "solid", "hover": "All-time high"})
    if max_drawdown_pct is not None:
        ticks.append({"ring": "outer", "angle_norm": max(-1.0, min(1.0, -abs(float(max_drawdown_pct)))), "color": COL["neg"], "style": "solid", "hover": "Max drawdown"})
    if breach_pct is not None:
        ticks.append({"ring": "outer", "angle_norm": max(-1.0, min(1.0, -abs(float(breach_pct)))), "color": COL["neg"], "style": "solid", "hover": "Breach line"})

    # Middle: inception momentum (unipolar; negative turns amber and clamps to 0 for angle)
    mid_val = None
    mid_color = COL["cyan"]
    if inception_momentum_pct is not None:
        try:
            v = float(inception_momentum_pct)
            mid_val = max(0.0, v)
            if v < 0:
                mid_color = COL["warn"]
        except Exception:
            mid_val = None

    # Inner: YTD unipolar
    cap = 1.0
    fig = concentric_ring(
        center_title="Balance",
        center_value=f"${balance_usd:,.0f}",
        caption=f"Δ inception {pnl_since_inception_pct:+.1f}%" if pnl_since_inception_pct is not None else "",
        outer_bipolar=pnl_since_inception_pct,
        outer_cap=1.0,
        outer_ghost_bipolar=ghost_prev_outer,
        middle_mode="unipolar",
        middle_val=mid_val,
        middle_cap=cap,
        inner_unipolar=ytd_pct if ytd_pct is not None else None,
        inner_cap=cap,
        size=size,
        rotation_deg=270,
        ticks=ticks,
        cap_dots=True,
    )
    return fig


def donut_equity(
    equity_usd: float,
    pnl_day_norm: float,
    risk_used_pct: float | None,
    exposure_pct: float | None,
    daily_target_norm: float | None = None,
    daily_loss_norm: float | None = None,
    size=(300, 300),
):
    ticks = []
    if daily_target_norm is not None:
        ticks.append({"ring": "outer", "angle_norm": max(-1.0, min(1.0, float(daily_target_norm))), "color": COL["pos"], "style": "solid", "hover": "Daily target"})
    if daily_loss_norm is not None:
        ticks.append({"ring": "outer", "angle_norm": max(-1.0, min(1.0, float(daily_loss_norm))), "color": COL["neg"], "style": "solid", "hover": "Daily loss limit"})
    # Advisory at 75% on risk budget
    ticks.append({"ring": "middle", "angle_norm": 0.75, "color": COL["warn"], "style": "dashed", "hover": "75% risk budget"})
    ticks.append({"ring": "middle", "angle_norm": 1.0, "color": COL["warn"], "style": "solid", "hover": "100% risk budget"})

    fig = concentric_ring(
        center_title="Equity",
        center_value=f"${equity_usd:,.0f}",
        caption=f"Day {pnl_day_norm*100:+.1f}% vs target" if pnl_day_norm is not None else "",
        outer_bipolar=pnl_day_norm,
        outer_cap=1.0,
        middle_mode="unipolar",
        middle_val=risk_used_pct,
        middle_cap=1.0,
        inner_unipolar=exposure_pct,
        inner_cap=1.0,
        size=size,
        rotation_deg=270,
        ticks=ticks,
        cap_dots=True,
    )
    return fig


def donut_pnl(
    pnl_day_norm: float,
    realized_usd: float | None,
    unrealized_usd: float | None,
    profit_efficiency: float | None,
    size=(300, 300),
):
    # Middle: realized/unrealized split semicircles scaled by magnitude ratio
    total = 0.0
    try:
        total = abs(float(realized_usd or 0.0)) + abs(float(unrealized_usd or 0.0))
    except Exception:
        total = 0.0
    left = (abs(float(realized_usd or 0.0)) / total) if total > 0 else 0.0
    right = (abs(float(unrealized_usd or 0.0)) / total) if total > 0 else 0.0

    fig = concentric_ring(
        center_title="P&L",
        center_value=f"{(realized_usd or 0.0) + (unrealized_usd or 0.0):+,.0f}",
        caption="trade view",
        outer_bipolar=pnl_day_norm,
        outer_cap=1.0,
        middle_mode="split",
        middle_split=(left, right),
        inner_unipolar=profit_efficiency,
        inner_cap=1.0,
        size=size,
        rotation_deg=270,
        cap_dots=True,
    )
    return fig


def donut_system_overview(
    *,
    equity_usd: float,
    pnl_day_norm: float | None,
    pnl_since_inception_pct: float | None = None,
    risk_used_pct: float | None = None,
    exposure_pct: float | None = None,
    discipline_score: float | None = None,
    patience_ratio: float | None = None,  # -0.5..+0.5 bipolar overlay between middle and inner
    daily_target_norm: float | None = None,
    daily_loss_norm: float | None = None,
    size=(300, 300),
):
    """Composite system compass as one donut with three rings.

    - Outer: PnL vs target/limit (bipolar) with ghost from inception P&L
    - Middle: split ring: left=risk_used (amber), right=exposure (blue)
    - Inner: psychology (discipline 0..100) unipolar
    """
    ticks = []
    if daily_target_norm is not None:
        ticks.append({"ring": "outer", "angle_norm": max(-1.0, min(1.0, float(daily_target_norm))), "color": COL["pos"], "style": "solid", "hover": "Daily target"})
    if daily_loss_norm is not None:
        ticks.append({"ring": "outer", "angle_norm": max(-1.0, min(1.0, float(daily_loss_norm))), "color": COL["neg"], "style": "solid", "hover": "Daily loss limit"})

    # Scale discipline 0..100 to 0..1 and choose color
    inner_val = None
    inner_col = COL["pos"]
    try:
        if discipline_score is not None:
            dv = max(0.0, min(100.0, float(discipline_score))) / 100.0
            inner_val = dv
            inner_col = COL["pos"] if dv >= 0.7 else COL["warn"] if dv >= 0.5 else COL["neg"]
    except Exception:
        inner_val = None

    # Build split values
    left = None if risk_used_pct is None else max(0.0, min(1.0, float(risk_used_pct)))
    right = None if exposure_pct is None else max(0.0, min(1.0, float(exposure_pct)))

    fig = concentric_ring(
        center_title="System",
        center_value=f"${equity_usd:,.0f}",
        caption="PnL • Risk/Expo • Discipline",
        outer_bipolar=pnl_day_norm,
        outer_cap=1.0,
        outer_ghost_bipolar=pnl_since_inception_pct,
        middle_mode="split",
        middle_split=(left, right),
        inner_unipolar=inner_val,
        inner_cap=1.0,
        size=size,
        rotation_deg=270,
        ticks=ticks,
        cap_dots=True,
    )
    # Patience overlay (thin ring between middle and inner)
    if patience_ratio is not None:
        try:
            p = max(-0.5, min(0.5, float(patience_ratio)))
            p_mag = abs(p) / 0.5
            p_dir = "clockwise" if p >= 0 else "counterclockwise"
            p_col = COL["info"] if p >= 0 else COL["warn"]
            fig.add_trace(
                go.Pie(
                    values=[p_mag * 360.0, 360.0 - p_mag * 360.0],
                    hole=0.80,
                    rotation=270,
                    sort=False,
                    direction=p_dir,
                    marker=dict(colors=[p_col, "rgba(0,0,0,0)"]),
                    textinfo="none",
                    hoverinfo="skip",
                    showlegend=False,
                    name="tempo",
                    opacity=0.7,
                )
            )
        except Exception:
            pass

    # Breach collar: subtle red arc when approaching loss limit (>=80% of negative bound)
    try:
        if pnl_day_norm is not None and float(pnl_day_norm) <= -0.8:
            fig.add_trace(
                go.Pie(
                    values=[72, 288],  # 20% of ring as collar
                    hole=0.56,
                    rotation=270,
                    sort=False,
                    direction="counterclockwise",
                    marker=dict(colors=["rgba(239,68,68,0.25)", "rgba(0,0,0,0)"]),
                    textinfo="none",
                    hoverinfo="skip",
                    showlegend=False,
                    name="breach_collar",
                )
            )
    except Exception:
        pass
    return fig


def donut_session_vitals(
    *,
    equity_usd: float,
    sod_equity_usd: float,
    baseline_equity_usd: float,
    daily_profit_pct: float,
    daily_risk_pct: float,
    max_total_dd_pct: float = 10.0,
    since_inception_pct: float | None = None,
    size=(300, 300),
):
    """Session Vitals donut with three rings (outer→inner):
    - Hard Deck (outer): red arc for max total drawdown vs baseline; balance marker
    - Daily Drawdown (middle): unipolar red showing fraction of daily DD used (0..1)
    - Daily P&L Progress (inner): bipolar vs target/limit (-1..+1)
    """
    # Inner: daily PnL bipolar
    try:
        pos_scale = max(0.0001, float(daily_profit_pct) / 100.0)
        neg_scale = max(0.0001, float(daily_risk_pct) / 100.0)
        delta_ratio = (equity_usd - sod_equity_usd) / sod_equity_usd if sod_equity_usd else 0.0
        if delta_ratio >= 0:
            pnl_norm = min(1.0, delta_ratio / pos_scale)
        else:
            pnl_norm = -min(1.0, abs(delta_ratio) / neg_scale)
    except Exception:
        pnl_norm = 0.0

    # Middle: daily DD used (0..1)
    try:
        dd_used = 0.0
        if equity_usd < sod_equity_usd and daily_risk_pct > 0:
            dd_used = (sod_equity_usd - equity_usd) / (sod_equity_usd * (daily_risk_pct / 100.0))
            dd_used = max(0.0, min(1.0, dd_used))
    except Exception:
        dd_used = 0.0

    # Outer: hard deck arc length proportional to max_total_dd_pct
    try:
        hd_len = max(0.0, min(1.0, float(max_total_dd_pct) / 100.0))
    except Exception:
        hd_len = 0.1

    fig = concentric_ring(
        center_title="Session",
        center_value=f"${equity_usd:,.0f}",
        caption="Hard deck • Daily DD • P&L",
        outer_bipolar=None,  # we'll overlay a static red arc for hard deck
        outer_cap=1.0,
        outer_ghost_bipolar=since_inception_pct,
        middle_mode="unipolar",
        middle_val=dd_used,
        middle_cap=1.0,
        inner_unipolar=None,  # replaced by bipolar below
        inner_cap=1.0,
        size=size,
        rotation_deg=270,
        ticks=None,
        cap_dots=True,
    )
    # Replace inner with bipolar P&L
    in_deg, _, in_col, in_hover = _unipolar_slice(abs(pnl_norm), cap=1.0, color=COL["pos"])  # use unipolar deg calc
    dirn = "clockwise" if pnl_norm >= 0 else "counterclockwise"
    col = COL["pos"] if pnl_norm >= 0 else COL["neg"]
    fig.add_trace(
        go.Pie(
            values=[in_deg, 360 - in_deg],
            hole=0.86,
            rotation=270,
            sort=False,
            direction=dirn,
            marker=dict(colors=[col, COL["track"]]),
            textinfo="none",
            hoverinfo="text",
            hovertext=[f"P&L {pnl_norm:+.2f}", ""],
            showlegend=False,
            name="pnl_inner",
        )
    )
    # Overlay hard deck static red arc
    fig.add_trace(
        go.Pie(
            values=[hd_len * 360.0, 360.0 - hd_len * 360.0],
            hole=0.58,
            rotation=270,
            sort=False,
            direction="counterclockwise",
            marker=dict(colors=["rgba(239,68,68,0.35)", "rgba(0,0,0,0)"]),
            textinfo="none",
            hoverinfo="text",
            hovertext=[f"Max DD {max_total_dd_pct:.1f}%", ""],
            showlegend=False,
            name="hard_deck",
        )
    )
    # Balance marker on outer edge vs baseline
    try:
        bal_ratio = (equity_usd - baseline_equity_usd) / baseline_equity_usd if baseline_equity_usd else 0.0
        # map to -1..+1 by clamping at ±max_total_dd_pct for red side and +max_total_dd_pct for green
        ar = max(-1.0, min(1.0, bal_ratio / (max_total_dd_pct / 100.0)))
        ang = (270 + (abs(ar) * 360.0) * (1 if ar >= 0 else -1)) % 360
        # draw a small dot
        def _ang2xy(a, r):
            import math
            th = math.radians(90 - a)
            return 0.5 + r * math.cos(th), 0.5 + r * math.sin(th)
        x, y = _ang2xy(ang, 0.5)
        rdot = 0.012
        fig.add_shape(type="circle", xref="paper", yref="paper",
                      x0=x - rdot, x1=x + rdot, y0=y - rdot, y1=y + rdot,
                      line=dict(color=COL["pos"] if ar >= 0 else COL["neg"], width=1),
                      fillcolor=COL["pos"] if ar >= 0 else COL["neg"], opacity=0.95)
    except Exception:
        pass

    return fig
