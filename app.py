"""
WaterBuddy - a daily hydration tracker built with Streamlit.

IBCP CRS AI, FA-2.

The whole screen acts as a water bottle: a water layer behind the app rises
as you log drinks. Everything lives in st.session_state, so nothing is saved
to disk or sent anywhere. Close the tab and your data is gone.

Sections:
    1. Config and data
    2. Session state helpers
    3. Calculation functions
    4. Visual components (HTML / SVG builders)
    5. CSS
    6. Page layout
"""

import math
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st


# =============================================================================
# 1. Config and data
# =============================================================================

st.set_page_config(
    page_title="WaterBuddy",
    page_icon="💧",
    layout="centered",
    initial_sidebar_state="auto",
)

# Streamlit Cloud servers run on UTC, so "today" is worked out in India time.
TIMEZONE = ZoneInfo("Asia/Kolkata")

GLASS_ML = 250  # one glass
CUP_ML = 250    # 1 cup = 250 ml

# Age group -> recommended daily water intake in ml
AGE_GROUPS = {
    "Kids (6–12)": 1600,
    "Teens (13–18)": 2100,
    "Adults (19–50)": 2500,
    "Older adults (51–64)": 2400,
    "Seniors (65+)": 2000,
}
DEFAULT_AGE_GROUP = "Teens (13–18)"

# Short names used in sentences ("Recommended for teens")
AGE_GROUP_NOUN = {
    "Kids (6–12)": "kids",
    "Teens (13–18)": "teens",
    "Adults (19–50)": "adults",
    "Older adults (51–64)": "older adults",
    "Seniors (65+)": "seniors",
}

MILESTONES = (0, 25, 50, 75, 100)

# Drippy's messages: one set per age group, one line per milestone.
MESSAGES = {
    "Kids (6–12)": {
        0: "Hi, I'm Drippy! Let's fill your bottle together. One sip to start!",
        25: "Woohoo, a quarter full! I'm waving at you. Keep going!",
        50: "Halfway there! Your body is doing a happy dance.",
        75: "Wow, almost full! Just a few more sips, superstar!",
        100: "You did it! You're a real hydration hero today!",
    },
    "Teens (13–18)": {
        0: "New day, empty tank. Grab your bottle and let's get going.",
        25: "25% down. Nice start. Keep the bottle on your desk so you don't forget.",
        50: "Halfway. Better focus and energy are on your side now.",
        75: "75%! Last stretch. One or two more refills and you're done.",
        100: "Goal hit. Hydration: completed it. Respect.",
    },
    "Adults (19–50)": {
        0: "Good morning. A glass of water now is the easiest win of the day.",
        25: "A quarter done. Steady sips beat drinking it all at once.",
        50: "Halfway to your goal, and nicely paced.",
        75: "Three-quarters there. One more glass with your next meal should do it.",
        100: "Daily goal reached. Well done, your body thanks you.",
    },
    "Older adults (51–64)": {
        0: "Let's begin gently. A glass with breakfast is a lovely start.",
        25: "A good start. Keeping a glass within reach makes it easy.",
        50: "Halfway there, nicely done. Water helps your joints and your energy.",
        75: "Nearly there. A cup of water with your afternoon break will do it.",
        100: "Goal complete. A wonderful day of looking after yourself.",
    },
    "Seniors (65+)": {
        0: "Hello! Thirst can be quiet as we get older, so let's sip little and often.",
        25: "Lovely start. Small sips through the morning add up nicely.",
        50: "Halfway already, wonderful. Keep a glass beside your chair.",
        75: "Almost there. One or two more small glasses and you're done.",
        100: "You reached your goal today. Splendid work, rest easy.",
    },
}

TIPS = [
    "Start your day with a glass of water before your first cup of tea or coffee.",
    "Keep a reusable bottle on your desk. If you can see it, you'll sip from it.",
    "Pale yellow pee is a good sign you're well hydrated.",
    "Feeling tired or getting a headache? You might just be thirsty.",
    "Fruits like watermelon, oranges and cucumber count towards your water too.",
    "Drink a glass of water with every meal and snack.",
    "Add a slice of lemon, mint or cucumber if plain water feels boring.",
    "Sip before, during and after sport or PE, not just when you feel thirsty.",
    "Hot day? You need more water than usual, so raise your goal a little.",
    "Set small targets: one glass every hour or two is easier than a lot at once.",
    "Thirst can feel like hunger. Try a glass of water before reaching for a snack.",
    "Your brain is about 75% water. Staying hydrated helps you concentrate.",
]

# Palette
MIST = "#EEF8FA"
LAGOON = "#4CC3D3"
DEEP = "#0D5770"
INK = "#08303F"
SUN = "#FFC24B"
SEA_GREEN = "#2FBF9B"
SEA_GREEN_DEEP = "#0E6B5C"


# =============================================================================
# 2. Session state helpers
# =============================================================================

def now_local() -> datetime:
    """Current time in India, regardless of the server's timezone."""
    return datetime.now(TIMEZONE)


def today_str() -> str:
    return now_local().date().isoformat()


def init_state() -> None:
    """Create every session_state key once, on the first run."""
    defaults = {
        "age_group": DEFAULT_AGE_GROUP,
        "goal": AGE_GROUPS[DEFAULT_AGE_GROUP],
        "log": [],                # list of {"time": "HH:MM", "ml": int, "label": str}
        "day": today_str(),       # the date this log belongs to
        "prev_pct": 0.0,          # water level drawn on the previous run (0-100)
        "render_id": 0,           # makes each run's @keyframes name unique
        "celebrated": False,      # balloons already shown today?
        "tip_index": random.randrange(len(TIPS)),
        "last_day": None,         # summary of the previous day, shown after a reset
        "flash": None,            # one-off toast message after an action
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def start_new_day(new_day: str | None = None) -> None:
    """Clear today's log. Keeps a short summary of the day that just ended."""
    total = total_intake(st.session_state.log)
    if st.session_state.log:
        st.session_state.last_day = {
            "day": st.session_state.day,
            "total": total,
            "goal": st.session_state.goal,
            "pct": percent_of_goal(total, st.session_state.goal),
            "drinks": len(st.session_state.log),
        }
    st.session_state.log = []
    st.session_state.celebrated = False
    st.session_state.day = new_day or today_str()


def check_date_rollover() -> None:
    """Auto-reset when the date changes (e.g. the tab is left open overnight)."""
    today = today_str()
    if st.session_state.day != today:
        start_new_day(today)
        st.session_state.flash = ("It's a new day, so your bottle has been emptied.", ":material/wb_sunny:")


# --- Widget callbacks (run before the page is redrawn) ---

def on_age_group_change() -> None:
    """Changing the age group resets the goal to that group's suggestion."""
    st.session_state.goal = AGE_GROUPS[st.session_state.age_group]


def add_drink(ml: int, label: str = "Glass") -> None:
    st.session_state.log.append(
        {"time": now_local().strftime("%H:%M"), "ml": int(ml), "label": label}
    )
    st.session_state.flash = (f"Added {int(ml):,} ml", ":material/water_drop:")


def add_custom_drink() -> None:
    amount = st.session_state.custom_amount
    unit = st.session_state.custom_unit
    ml = cups_to_ml(amount) if unit == "cups" else amount
    if ml <= 0:
        st.session_state.flash = ("Enter an amount above zero first.", ":material/info:")
        return
    label = f"{amount:g} cup" + ("" if amount == 1 else "s") if unit == "cups" else "Custom"
    add_drink(round(ml), label)


def undo_last_drink() -> None:
    if st.session_state.log:
        removed = st.session_state.log.pop()
        st.session_state.flash = (f"Removed {removed['ml']:,} ml", ":material/undo:")


def reset_day() -> None:
    start_new_day()
    st.session_state.flash = ("Fresh start! Your bottle is empty again.", ":material/restart_alt:")


def next_tip() -> None:
    choices = [i for i in range(len(TIPS)) if i != st.session_state.tip_index]
    st.session_state.tip_index = random.choice(choices)


# =============================================================================
# 3. Calculation functions
# =============================================================================

def total_intake(log: list[dict]) -> int:
    """Total ml drunk today."""
    return sum(entry["ml"] for entry in log)


def remaining_ml(total: int, goal: int) -> int:
    """How much is left to reach the goal (never negative)."""
    return max(goal - total, 0)


def percent_of_goal(total: int, goal: int) -> float:
    """Percent of the goal achieved. Can go above 100."""
    if goal <= 0:
        return 0.0
    return round(total / goal * 100, 1)


def glasses_left(remaining: int) -> int:
    """Number of 250 ml glasses still needed, rounded up."""
    return math.ceil(remaining / GLASS_ML)


def milestone_for(pct: float) -> int:
    """Highest milestone reached: 0, 25, 50, 75 or 100."""
    for m in reversed(MILESTONES):
        if pct >= m:
            return m
    return 0


def cups_to_ml(cups: float) -> float:
    return cups * CUP_ML


def ml_to_cups(ml: float) -> float:
    return ml / CUP_ML


def motivational_message(age_group: str, pct: float) -> str:
    return MESSAGES[age_group][milestone_for(pct)]


# =============================================================================
# 4. Visual components
# =============================================================================

def html(markup: str) -> None:
    """Render raw HTML. Lines are joined so Markdown never treats them as code."""
    flat = " ".join(line.strip() for line in markup.strip().splitlines() if line.strip())
    st.markdown(flat, unsafe_allow_html=True)


def water_layer(pct: float, prev_pct: float, render_id: int) -> str:
    """The full-screen water. Rises from the previous level to the new one."""
    def level(p: float) -> str:
        p = max(0.0, min(p, 100.0))
        return f"calc(5vh + {p * 0.95:.2f}vh)"

    complete = pct >= 100
    anim = f"wb_rise_{render_id}"
    bubbles = "".join(
        f'<span class="wb-bubble" style="left:{left}%;width:{size}px;height:{size}px;'
        f'animation-duration:{dur}s;animation-delay:{delay}s"></span>'
        for left, size, dur, delay in [
            (8, 10, 9, 0), (21, 6, 7, 2.5), (37, 12, 11, 1), (55, 7, 8, 4),
            (68, 9, 10, 2), (82, 5, 6.5, 0.5), (93, 11, 12, 3.5),
        ]
    )
    wave = (
        '<svg viewBox="0 0 2400 60" preserveAspectRatio="none" aria-hidden="true">'
        '<path d="M0 30 Q150 0 300 30 T600 30 T900 30 T1200 30 T1500 30 T1800 30 T2100 30 T2400 30 V60 H0 Z"/>'
        "</svg>"
    )
    return f"""
    <style>
      @keyframes {anim} {{ from {{ height: {level(prev_pct)}; }} to {{ height: {level(pct)}; }} }}
      .wb-water {{ height: {level(pct)}; animation: {anim} 1.6s cubic-bezier(.22,.8,.26,1) both; }}
    </style>
    <div class="wb-water {'wb-complete' if complete else ''}" aria-hidden="true">
      <div class="wb-wave wb-wave-back">{wave}</div>
      <div class="wb-wave wb-wave-front">{wave}</div>
      <div class="wb-body">{bubbles}</div>
    </div>
    """


def drippy_svg(milestone: int) -> str:
    """Drippy the droplet. Face, arms and extras change with each milestone."""
    # Eyes
    if milestone == 100:
        eyes = (
            '<path d="M57 112 Q64 103 71 112" class="wb-line"/>'
            '<path d="M89 112 Q96 103 103 112" class="wb-line"/>'
        )
    else:
        r = 7 if milestone >= 50 else 6.2
        eyes = (
            f'<circle cx="64" cy="110" r="{r}" fill="{INK}"/><circle cx="66.5" cy="107.5" r="2.2" fill="#fff"/>'
            f'<circle cx="96" cy="110" r="{r}" fill="{INK}"/><circle cx="98.5" cy="107.5" r="2.2" fill="#fff"/>'
        )

    # Mouth
    if milestone == 0:
        mouth = '<path d="M71 133 Q80 140 89 133" class="wb-line"/>'
    elif milestone == 25:
        mouth = '<path d="M68 131 Q80 144 92 131" class="wb-line"/>'
    elif milestone in (50, 75):
        mouth = (
            f'<path d="M67 130 Q80 150 93 130 Z" fill="{INK}"/>'
            '<path d="M73 140 Q80 146 87 140 Q80 137 73 140 Z" fill="#ff8fa3"/>'
        )
    else:
        mouth = (
            f'<path d="M61 127 Q80 158 99 127 Z" fill="{INK}"/>'
            '<path d="M70 141 Q80 151 90 141 Q80 136 70 141 Z" fill="#ff8fa3"/>'
        )

    blush = ""
    if milestone >= 50:
        blush = (
            '<ellipse cx="52" cy="126" rx="8" ry="4.5" fill="#ff9fb2" opacity=".55"/>'
            '<ellipse cx="108" cy="126" rx="8" ry="4.5" fill="#ff9fb2" opacity=".55"/>'
        )

    # Arms
    left_down = '<path d="M34 128 Q20 138 22 153" class="wb-arm"/><circle cx="22" cy="154" r="5.5" class="wb-hand"/>'
    right_down = '<path d="M126 128 Q140 138 138 153" class="wb-arm"/><circle cx="138" cy="154" r="5.5" class="wb-hand"/>'
    left_up = '<path d="M36 116 Q16 100 20 78" class="wb-arm"/><circle cx="20" cy="76" r="5.5" class="wb-hand"/>'
    right_up = '<path d="M124 116 Q144 100 140 78" class="wb-arm"/><circle cx="140" cy="76" r="5.5" class="wb-hand"/>'
    if milestone == 25:
        arms = left_down + f'<g class="wb-waving">{right_up}</g>'
    elif milestone >= 75:
        arms = left_up + right_up
    else:
        arms = left_down + right_down

    crown = ""
    sparkles = ""
    if milestone == 100:
        crown = (
            f'<g class="wb-crown"><path d="M59 34 L62 11 L71 23 L80 5 L89 23 L98 11 L101 34 Z" '
            f'fill="{SUN}" stroke="#D9951A" stroke-width="2" stroke-linejoin="round"/>'
            '<circle cx="80" cy="25" r="3" fill="#ff7a90"/>'
            '<circle cx="68" cy="28" r="2.2" fill="#fff"/><circle cx="92" cy="28" r="2.2" fill="#fff"/></g>'
        )
        sparkles = (
            f'<path class="wb-spark" d="M18 40 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3z" fill="{SUN}"/>'
            f'<path class="wb-spark wb-spark-2" d="M142 44 l2.5 6 6 2.5 -6 2.5 -2.5 6 -2.5 -6 -6 -2.5 6 -2.5z" fill="{SUN}"/>'
        )

    motion = "wb-jump" if milestone == 75 else "wb-bob"
    return f"""
    <svg class="wb-drippy" viewBox="0 0 160 180" role="img" aria-label="Drippy the water droplet, {milestone}% mood">
      <defs>
        <linearGradient id="wbDrop" x1="0" y1="0" x2="0.4" y2="1">
          <stop offset="0" stop-color="#9BE7F0"/>
          <stop offset=".55" stop-color="{LAGOON}"/>
          <stop offset="1" stop-color="#1C8FA6"/>
        </linearGradient>
      </defs>
      <ellipse cx="80" cy="174" rx="34" ry="4.5" fill="{DEEP}" opacity=".13" class="wb-shadow"/>
      <g class="{motion}">
        {sparkles}
        {arms}
        <path d="M80 26 C64 56 30 86 30 122 A50 50 0 0 0 130 122 C130 86 96 56 80 26 Z"
              fill="url(#wbDrop)" stroke="{DEEP}" stroke-opacity=".25" stroke-width="2"/>
        <ellipse cx="57" cy="92" rx="7" ry="13" fill="#fff" opacity=".55" transform="rotate(28 57 92)"/>
        {crown}
        {eyes}
        {blush}
        {mouth}
      </g>
    </svg>
    """


def mascot_block(age_group: str, pct: float) -> str:
    m = milestone_for(pct)
    msg = motivational_message(age_group, pct)
    return f"""
    <div class="wb-mascot">
      {drippy_svg(m)}
      <div class="wb-bubble-speech" role="status">{msg}</div>
    </div>
    """


def readout_block(total: int, goal: int, pct: float, remaining: int, glasses: int) -> str:
    fill = min(pct, 100)
    dots = "".join(
        f'<span class="wb-dot {"wb-dot-on" if pct >= m else ""}" style="left:{m}%" '
        f'title="{m}%"></span>'
        for m in MILESTONES[1:]
    )
    if remaining > 0:
        to_go = f"<b>{remaining:,} ml</b> to go"
        glasses_txt = f"<b>{glasses}</b> glass{'es' if glasses != 1 else ''} left"
    else:
        extra = total - goal
        to_go = "<b>Goal reached</b>" + (f" (+{extra:,} ml)" if extra > 0 else "")
        glasses_txt = "<b>0</b> glasses left"
    return f"""
    <div class="wb-readout">
      <div class="wb-amount">{total:,}<span> ml</span></div>
      <div class="wb-of">of your {goal:,} ml goal today</div>
      <div class="wb-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{fill:.0f}">
        <div class="wb-fill" style="width:{fill}%"></div>
        {dots}
      </div>
      <div class="wb-stats">
        <span><b>{pct:g}%</b> done</span><i></i><span>{to_go}</span><i></i><span>{glasses_txt}</span>
      </div>
    </div>
    """


def topbar_block() -> str:
    d = now_local()
    return f"""
    <div class="wb-top">
      <div class="wb-brand"><span class="wb-logo"></span>WaterBuddy</div>
      <div class="wb-date">{d:%A}, {d.day} {d:%B}</div>
    </div>
    """


def log_block(log: list[dict]) -> str:
    if not log:
        return '<div class="wb-empty">No drinks yet. Your first glass will show up here.</div>'
    rows = "".join(
        f'<li><span class="wb-time">{e["time"]}</span><span class="wb-label">{e["label"]}</span>'
        f'<span class="wb-ml">+{e["ml"]:,} ml</span></li>'
        for e in reversed(log)
    )
    return f'<ul class="wb-log">{rows}</ul>'


def summary_text(log: list[dict], goal: int, age_group: str) -> str:
    """End-of-day summary written as plain sentences."""
    total = total_intake(log)
    pct = percent_of_goal(total, goal)
    if not log:
        return "Nothing logged yet today. Your summary will build up as you drink."
    biggest = max(log, key=lambda e: e["ml"])
    n = len(log)
    parts = [
        f"You've had <b>{n} drink{'s' if n != 1 else ''}</b> adding up to <b>{total:,} ml</b>, "
        f"which is <b>{pct:g}%</b> of your goal.",
        f"First sip at {log[0]['time']}, latest at {log[-1]['time']}. "
        f"Biggest drink: {biggest['ml']:,} ml at {biggest['time']}.",
    ]
    standard = AGE_GROUPS[age_group]
    if total >= standard:
        parts.append(f"You also passed the standard target for {AGE_GROUP_NOUN[age_group]}.")
    if pct >= 100:
        parts.append("Verdict: fully hydrated. Great job!")
    elif pct >= 75:
        parts.append("Verdict: so close. One or two more glasses before bed.")
    elif pct >= 50:
        parts.append("Verdict: a solid effort. Try to sip a bit earlier tomorrow.")
    else:
        parts.append("Verdict: you've made a start. Keep a bottle nearby for the rest of the day.")
    return " ".join(parts)


# =============================================================================
# 5. CSS
# =============================================================================

BASE_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700;12..96,800&display=swap');

:root {{
  --mist: {MIST}; --lagoon: {LAGOON}; --deep: {DEEP}; --ink: {INK}; --sun: {SUN};
  --glass: rgba(255,255,255,.58); --glass-border: rgba(255,255,255,.75);
}}

/* Font everywhere, but keep Streamlit's Material icon font working */
html, body, .stApp, .stApp *:not([data-testid="stIconMaterial"]):not([data-testid="stExpanderIcon"]) {{
  font-family: 'Bricolage Grotesque', system-ui, sans-serif;
}}
[data-testid="stIconMaterial"], [data-testid="stExpanderIcon"] {{ font-family: 'Material Symbols Rounded' !important; }}

/* App background and the stacking context that holds the water */
.stApp {{ background: var(--mist); color: var(--ink); }}
[data-testid="stMain"] {{ position: relative; z-index: 0; background: transparent; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stDecoration"] {{ display: none; }}
.block-container, [data-testid="stMainBlockContainer"] {{ padding-top: 3.2rem; padding-bottom: 4rem; max-width: 780px; }}

/* Elements that only hold CSS or the fixed water take no space */
[data-testid="stElementContainer"]:has(.wb-css),
[data-testid="stElementContainer"]:has(.wb-water) {{ position: absolute; width: 0; height: 0; margin: 0; overflow: visible; }}

/* ---------- Water ---------- */
.wb-water {{ position: fixed; left: 0; right: 0; bottom: 0; z-index: -1; pointer-events: none; }}
.wb-body {{ position: absolute; inset: 0; overflow: hidden;
  background: linear-gradient(180deg, #6fd3df 0%, var(--lagoon) 18%, #1f8ea5 60%, var(--deep) 100%);
  transition: background 1.2s ease; }}
.wb-wave {{ position: absolute; left: 0; width: 200%; height: 34px; top: -33px; }}
.wb-wave svg {{ width: 100%; height: 100%; display: block; }}
.wb-wave-front svg path {{ fill: #6fd3df; }}
.wb-wave-back {{ top: -40px; height: 40px; opacity: .45; }}
.wb-wave-back svg path {{ fill: var(--lagoon); }}
.wb-wave-front {{ animation: wb-drift 9s linear infinite; }}
.wb-wave-back {{ animation: wb-drift-rev 13s linear infinite; }}
@keyframes wb-drift {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}
@keyframes wb-drift-rev {{ from {{ transform: translateX(-50%); }} to {{ transform: translateX(0); }} }}

.wb-complete .wb-body {{ background: linear-gradient(180deg, #7fe3c4 0%, {SEA_GREEN} 20%, #17917a 60%, {SEA_GREEN_DEEP} 100%); }}
.wb-complete .wb-wave-front svg path {{ fill: #7fe3c4; }}
.wb-complete .wb-wave-back svg path {{ fill: {SEA_GREEN}; }}

.wb-bubble {{ position: absolute; bottom: -14px; border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, rgba(255,255,255,.9), rgba(255,255,255,.25) 60%, rgba(255,255,255,.08));
  border: 1px solid rgba(255,255,255,.5); animation-name: wb-bubble-up; animation-timing-function: ease-in;
  animation-iteration-count: infinite; opacity: 0; }}
@keyframes wb-bubble-up {{
  0% {{ bottom: -14px; opacity: 0; transform: translateX(0); }}
  15% {{ opacity: .8; }}
  50% {{ transform: translateX(8px); }}
  90% {{ opacity: .6; }}
  100% {{ bottom: 96%; opacity: 0; transform: translateX(-6px); }}
}}

/* ---------- Frosted glass panels ---------- */
.st-key-today, .st-key-insights {{
  background: var(--glass);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid var(--glass-border);
  box-shadow: 0 20px 50px -24px rgba(8,48,63,.35), inset 0 1px 0 rgba(255,255,255,.8);
}}
.st-key-today {{ border-radius: 32px; padding: 26px 30px 24px; gap: .9rem; }}
.st-key-insights {{ border-radius: 26px; padding: 22px 26px; margin-top: 1.1rem; gap: .7rem; }}

/* Top bar */
.wb-top {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }}
.wb-brand {{ display: flex; align-items: center; gap: 9px; font-weight: 800; font-size: 1.25rem;
  letter-spacing: -.02em; color: var(--deep); }}
.wb-logo {{ width: 18px; height: 22px; background: linear-gradient(160deg, #9BE7F0, var(--lagoon) 50%, var(--deep));
  border-radius: 50% 50% 50% 50% / 62% 62% 40% 40%; clip-path: path('M9 0 C6 5 0 9 0 14 A9 8 0 0 0 18 14 C18 9 12 5 9 0 Z'); }}
.wb-date {{ color: rgba(8,48,63,.62); font-weight: 500; font-size: .95rem; }}

/* Mascot */
.wb-mascot {{ display: flex; flex-direction: column; align-items: center; gap: 6px; }}
.wb-drippy {{ width: 170px; height: auto; overflow: visible; }}
.wb-line {{ fill: none; stroke: var(--ink); stroke-width: 4.5; stroke-linecap: round; }}
.wb-arm {{ fill: none; stroke: #1C8FA6; stroke-width: 7; stroke-linecap: round; }}
.wb-hand {{ fill: #4CC3D3; stroke: #1C8FA6; stroke-width: 2; }}
.wb-bob {{ animation: wb-bob 3.2s ease-in-out infinite; }}
.wb-jump {{ animation: wb-jump 1s cubic-bezier(.3,0,.4,1) infinite; }}
.wb-waving {{ transform-box: view-box; transform-origin: 124px 116px; animation: wb-wave-arm 1.1s ease-in-out infinite; }}
.wb-spark {{ transform-box: fill-box; transform-origin: center; animation: wb-twinkle 1.6s ease-in-out infinite; }}
.wb-spark-2 {{ animation-delay: .7s; }}
@keyframes wb-bob {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-5px); }} }}
@keyframes wb-jump {{ 0%,100% {{ transform: translateY(0); }} 45% {{ transform: translateY(-16px); }} 60% {{ transform: translateY(-14px); }} }}
@keyframes wb-wave-arm {{ 0%,100% {{ transform: rotate(-8deg); }} 50% {{ transform: rotate(18deg); }} }}
@keyframes wb-twinkle {{ 0%,100% {{ transform: scale(.6); opacity: .5; }} 50% {{ transform: scale(1.1); opacity: 1; }} }}

.wb-bubble-speech {{ position: relative; background: #fff; color: var(--ink); border-radius: 18px;
  padding: 12px 16px; font-size: .98rem; line-height: 1.4; font-weight: 500; text-align: center; max-width: 260px;
  box-shadow: 0 10px 24px -14px rgba(8,48,63,.45); }}
.wb-bubble-speech::before {{ content: ""; position: absolute; top: -9px; left: 50%; transform: translateX(-50%);
  border: 10px solid transparent; border-top: 0; border-bottom-color: #fff; }}

/* Readout */
.wb-amount {{ font-size: clamp(3.2rem, 9vw, 4.8rem); font-weight: 800; letter-spacing: -.045em; line-height: .95;
  color: var(--deep); font-variant-numeric: tabular-nums; }}
.wb-amount span {{ font-size: .42em; font-weight: 600; letter-spacing: -.01em; color: var(--lagoon); }}
.wb-of {{ margin-top: 6px; color: rgba(8,48,63,.7); font-size: 1.05rem; }}
.wb-track {{ position: relative; height: 8px; border-radius: 99px; background: rgba(13,87,112,.12); margin: 22px 7px 16px 0; }}
.wb-fill {{ position: absolute; left: 0; top: 0; bottom: 0; border-radius: 99px;
  background: linear-gradient(90deg, var(--lagoon), var(--deep)); transition: width .8s cubic-bezier(.22,.8,.26,1); }}
.wb-dot {{ position: absolute; top: 50%; width: 14px; height: 14px; border-radius: 50%; transform: translate(-50%, -50%);
  background: #fff; border: 2.5px solid rgba(13,87,112,.25); transition: all .4s ease; }}
.wb-dot-on {{ background: var(--sun); border-color: #fff; box-shadow: 0 0 0 3px rgba(255,194,75,.35); }}
.wb-readout {{ margin-bottom: 6px; }}
.wb-stats {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; color: rgba(8,48,63,.75); font-size: .98rem; }}
.wb-stats b {{ color: var(--ink); font-weight: 700; }}
.wb-stats i {{ width: 4px; height: 4px; border-radius: 50%; background: rgba(8,48,63,.3); }}

/* ---------- Buttons ---------- */
.stApp button[data-testid^="stBaseButton"] {{
  border-radius: 14px; border: 1px solid rgba(13,87,112,.14); background: rgba(255,255,255,.85);
  color: var(--deep); font-weight: 600; min-height: 44px; box-shadow: 0 4px 12px -8px rgba(8,48,63,.4);
  transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
}}
.stApp button[data-testid^="stBaseButton"]:hover {{ background: #fff; border-color: var(--lagoon); color: var(--deep);
  transform: translateY(-1px); box-shadow: 0 8px 18px -10px rgba(8,48,63,.45); }}
.stApp button[data-testid^="stBaseButton"]:focus-visible {{ outline: 3px solid rgba(76,195,211,.6); outline-offset: 2px; }}
.stApp button[data-testid^="stBaseButton"]:disabled {{ opacity: .45; transform: none; }}

.st-key-log250 button {{
  min-height: 74px; border-radius: 999px !important; border: none !important;
  background: linear-gradient(120deg, #5fd6e3 0%, var(--lagoon) 35%, #1f8ea5 75%, var(--deep) 100%) !important;
  color: #fff !important; box-shadow: 0 16px 30px -14px rgba(13,87,112,.7), inset 0 1px 0 rgba(255,255,255,.45) !important;
}}
.st-key-log250 button p {{ font-size: 1.6rem !important; font-weight: 800 !important; letter-spacing: -.02em; }}
.st-key-log250 button:hover {{ filter: brightness(1.06); transform: translateY(-2px) !important; }}
.st-key-log250 button:active {{ transform: translateY(1px) scale(.99) !important; }}

/* ---------- Inputs, expander, misc ---------- */
.stApp [data-baseweb="select"] > div, .stApp [data-baseweb="input"] {{ border-radius: 12px; background: rgba(255,255,255,.85); }}
.stApp label p {{ font-weight: 600; color: var(--ink); }}
.stApp [data-testid="stExpander"] details {{ border-radius: 16px; border: 1px solid rgba(13,87,112,.14); background: rgba(255,255,255,.5); }}
.stApp [data-testid="stExpander"] summary p {{ font-weight: 600; color: var(--deep); }}
.stApp [data-testid="stForm"] {{ border: none; padding: 0; }}
.stApp [data-testid="stCaptionContainer"] {{ color: rgba(8,48,63,.6); }}
.wb-divider {{ height: 1px; background: rgba(13,87,112,.12); margin: 2px 0; }}

/* Comparison bars */
.wb-h {{ font-weight: 700; font-size: 1.15rem; color: var(--deep); letter-spacing: -.01em; margin: 6px 0 0; padding: 0; }}
.wb-sub {{ color: rgba(8,48,63,.65); font-size: .95rem; margin: 2px 0 8px; }}
.wb-compare-card {{ font-size: .95rem; color: rgba(8,48,63,.7); }}
.wb-compare-card b {{ display: block; font-size: 1.7rem; color: var(--ink); font-weight: 800; letter-spacing: -.03em; }}
.stApp [data-testid="stProgressBarTrack"] {{ border-radius: 99px; height: 10px; background: rgba(13,87,112,.12); }}
.stApp [data-testid="stProgressBarTrack"] > div {{ border-radius: 99px; height: 10px; background: linear-gradient(90deg, var(--lagoon), var(--deep)); }}
.st-key-cmp_goal [data-testid="stProgressBarTrack"] > div {{ background: linear-gradient(90deg, #7fd6a8, {SEA_GREEN}); }}

/* Drinks log */
.wb-log {{ list-style: none; padding: 0; margin: 0; max-height: 260px; overflow-y: auto; }}
.wb-log li {{ display: flex; align-items: center; gap: 12px; padding: 9px 2px; border-bottom: 1px solid rgba(13,87,112,.09); margin: 0; }}
.wb-log li:last-child {{ border-bottom: none; }}
.wb-time {{ color: rgba(8,48,63,.55); font-variant-numeric: tabular-nums; width: 3.2em; }}
.wb-label {{ flex: 1; color: var(--ink); }}
.wb-ml {{ font-weight: 700; color: var(--deep); font-variant-numeric: tabular-nums; }}
.wb-empty {{ color: rgba(8,48,63,.6); padding: 6px 0; }}
.wb-summary {{ background: rgba(255,255,255,.6); border-radius: 16px; padding: 14px 16px; line-height: 1.55; color: var(--ink); }}
.wb-summary b {{ color: var(--deep); }}
.wb-lastday {{ font-size: .9rem; color: rgba(8,48,63,.65); margin-top: 8px; }}
.wb-privacy {{ font-size: .88rem; color: rgba(8,48,63,.6); display: flex; gap: 8px; align-items: flex-start; }}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {{ background: #fff; border-right: 1px solid rgba(13,87,112,.1); }}
.wb-side-h {{ font-weight: 700; font-size: 1.05rem; color: var(--deep); margin-bottom: 2px; }}
.wb-convert {{ background: {MIST}; border-radius: 14px; padding: 10px 14px; font-size: 1.05rem; color: var(--ink); }}
.wb-convert b {{ color: var(--deep); font-size: 1.3rem; }}
.wb-tip {{ background: linear-gradient(140deg, #fff, {MIST}); border: 1px solid rgba(76,195,211,.35); border-radius: 16px;
  padding: 14px 16px; line-height: 1.5; color: var(--ink); }}

/* ---------- Mobile ---------- */
@media (max-width: 640px) {{
  .block-container, [data-testid="stMainBlockContainer"] {{ padding-left: 12px; padding-right: 12px; padding-top: 3.4rem; }}
  .st-key-today {{ padding: 20px 18px; border-radius: 26px; }}
  .st-key-insights {{ padding: 18px; border-radius: 22px; }}
  .wb-drippy {{ width: 116px; }}
  .wb-bubble-speech {{ font-size: .92rem; padding: 10px 14px; }}
  .st-key-today > [data-testid="stHorizontalBlock"] {{ row-gap: .6rem; }}
  /* Keep +100 / +500 / Undo on one row instead of stacking */
  .st-key-quick [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: .5rem; }}
  .st-key-quick [data-testid="stColumn"] {{ min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }}
  .wb-amount {{ text-align: center; }}
  .wb-of {{ text-align: center; }}
  .wb-stats {{ justify-content: center; font-size: .92rem; }}
  .st-key-log250 button {{ min-height: 64px; }}
}}

/* ---------- Reduced motion ---------- */
@media (prefers-reduced-motion: reduce) {{
  .wb-water, .wb-wave, .wb-bubble, .wb-bob, .wb-jump, .wb-waving, .wb-spark {{ animation: none !important; }}
  .wb-bubble {{ display: none; }}
  .wb-fill, .wb-dot, .stApp button {{ transition: none !important; }}
}}
"""


def inject_css() -> None:
    html(f'<style class="wb-css">{BASE_CSS}</style><span class="wb-css"></span>')


# =============================================================================
# 6. Page layout
# =============================================================================

def render_sidebar() -> None:
    with st.sidebar:
        html('<div class="wb-side-h">Cups ↔ ml converter</div>')
        direction = st.radio(
            "Convert from", ["cups", "ml"], horizontal=True, key="conv_dir",
            format_func=lambda x: "Cups to ml" if x == "cups" else "ml to cups",
            label_visibility="collapsed",
        )
        if direction == "cups":
            cups = st.number_input("Cups", min_value=0.0, max_value=40.0, value=2.0, step=0.5, key="conv_cups")
            html(f'<div class="wb-convert">{cups:g} cup{"s" if cups != 1 else ""} = <b>{cups_to_ml(cups):,.0f} ml</b></div>')
        else:
            ml = st.number_input("Millilitres", min_value=0, max_value=10000, value=500, step=50, key="conv_ml")
            html(f'<div class="wb-convert">{ml:,} ml = <b>{ml_to_cups(ml):g} cups</b></div>')
        st.caption("1 cup = 250 ml")

        st.write("")
        html('<div class="wb-side-h">Hydration tip</div>')
        html(f'<div class="wb-tip">{TIPS[st.session_state.tip_index]}</div>')
        st.button("Show another tip", key="tip_btn", on_click=next_tip,
                  icon=":material/lightbulb:", use_container_width=True)

        st.write("")
        html(
            '<div class="wb-privacy">Everything stays in this browser tab. '
            "Nothing is saved or sent anywhere, so refreshing the page starts fresh.</div>"
        )


def render_today_panel(total: int, goal: int, pct: float, remaining: int, glasses: int) -> None:
    with st.container(key="today"):
        html(topbar_block())
        left, right = st.columns([5, 7], gap="large", vertical_alignment="center")
        with left:
            html(mascot_block(st.session_state.age_group, pct))
        with right:
            html(readout_block(total, goal, pct, remaining, glasses))
            st.button("+250 ml", key="log250", type="primary", on_click=add_drink,
                      args=(250, "Glass"), use_container_width=True)
            b1, b2, b3 = st.container(key="quick").columns(3, gap="small")
            b1.button("+100 ml", key="log100", on_click=add_drink, args=(100, "Small sip"),
                      use_container_width=True)
            b2.button("+500 ml", key="log500", on_click=add_drink, args=(500, "Bottle"),
                      use_container_width=True)
            b3.button("Undo", key="undo", on_click=undo_last_drink, icon=":material/undo:",
                      disabled=not st.session_state.log, use_container_width=True)
            with st.expander("Add a custom amount", icon=":material/tune:"):
                with st.form("custom_form", clear_on_submit=True, border=False):
                    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
                    c1.number_input("Amount", min_value=0.0, max_value=3000.0, value=1.0,
                                    step=0.5, key="custom_amount")
                    c2.radio("Unit", ["cups", "ml"], key="custom_unit", horizontal=True)
                    st.form_submit_button("Add drink", on_click=add_custom_drink,
                                          icon=":material/add:", use_container_width=True)

        html('<div class="wb-divider"></div>')
        s1, s2, s3 = st.columns([4, 3, 3], vertical_alignment="bottom")
        s1.selectbox("Age group", list(AGE_GROUPS), key="age_group", on_change=on_age_group_change)
        s2.number_input("Daily goal (ml)", min_value=500, max_value=6000, step=50, key="goal")
        s3.button("Start a new day", key="reset", on_click=reset_day,
                  icon=":material/restart_alt:", use_container_width=True)
        suggested = AGE_GROUPS[st.session_state.age_group]
        noun = AGE_GROUP_NOUN[st.session_state.age_group]
        st.caption(f"Suggested for {noun}: {suggested:,} ml a day. Change the number if your doctor "
                   "or a hot day calls for more.")


def render_insights_panel(total: int, goal: int) -> None:
    age_group = st.session_state.age_group
    standard = AGE_GROUPS[age_group]
    noun = AGE_GROUP_NOUN[age_group]
    with st.container(key="insights"):
        diff = goal - standard
        if diff == 0:
            diff_txt = "Your goal matches the standard target."
        elif diff > 0:
            diff_txt = f"Your goal is {diff:,} ml above the standard target."
        else:
            diff_txt = f"Your goal is {-diff:,} ml below the standard target."
        html(f'<div><p class="wb-h">Standard target vs your goal</p><div class="wb-sub">{diff_txt}</div></div>')

        c1, c2 = st.columns(2, gap="medium")
        with c1, st.container(key="cmp_std"):
            p = percent_of_goal(total, standard)
            html(f'<div class="wb-compare-card">Recommended for {noun}<b>{standard:,} ml</b></div>')
            st.progress(min(p, 100) / 100, text=f"{p:g}% of it")
        with c2, st.container(key="cmp_goal"):
            p = percent_of_goal(total, goal)
            html(f'<div class="wb-compare-card">Your own goal<b>{goal:,} ml</b></div>')
            st.progress(min(p, 100) / 100, text=f"{p:g}% of it")

        html('<div class="wb-divider"></div>')
        html('<p class="wb-h">Today\'s drinks</p>')
        html(log_block(st.session_state.log))

        html('<div class="wb-divider"></div>')
        html('<p class="wb-h">End-of-day summary</p>')
        last = st.session_state.last_day
        last_txt = ""
        if last:
            last_txt = (f'<div class="wb-lastday">Last day ({last["day"]}): {last["total"]:,} ml of '
                        f'{last["goal"]:,} ml, {last["pct"]:g}% across {last["drinks"]} drinks.</div>')
        html(f'<div class="wb-summary">{summary_text(st.session_state.log, goal, age_group)}{last_txt}</div>')


def main() -> None:
    init_state()
    check_date_rollover()
    st.session_state.render_id += 1

    # Live calculations
    log = st.session_state.log
    goal = st.session_state.goal
    total = total_intake(log)
    remaining = remaining_ml(total, goal)
    pct = percent_of_goal(total, goal)
    glasses = glasses_left(remaining)

    inject_css()
    html(water_layer(pct, st.session_state.prev_pct, st.session_state.render_id))

    render_sidebar()
    render_today_panel(total, goal, pct, remaining, glasses)
    render_insights_panel(total, goal)

    if st.session_state.flash:
        message, icon = st.session_state.flash
        st.toast(message, icon=icon)
        st.session_state.flash = None

    # Balloons only the first time the goal is reached today
    if pct >= 100 and not st.session_state.celebrated:
        st.session_state.celebrated = True
        st.balloons()

    st.session_state.prev_pct = min(pct, 100.0)


main()
