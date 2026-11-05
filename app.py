import streamlit as st
import sqlite3
import random
import datetime
import html
import urllib.parse
from zoneinfo import ZoneInfo
from pathlib import Path
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Daily Timer Giveaway",
    page_icon="🎁",
    layout="centered"
)

# WhatsApp number: country code + number, digits only
ADMIN_WHATSAPP = st.secrets.get(
    "ADMIN_WHATSAPP",
    "91XXXXXXXXXX"
)

DB_PATH = "giveaway.db"
TODAY = datetime.datetime.now(
    ZoneInfo("Asia/Kolkata")
).date().isoformat()


# ---------------- DATABASE ----------------

def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS targets(
                day TEXT PRIMARY KEY,
                target INTEGER NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS entries(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                instagram TEXT NOT NULL,
                elapsed REAL NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(day, instagram)
            )
        """)

        row = con.execute(
            "SELECT target FROM targets WHERE day=?",
            (TODAY,)
        ).fetchone()

        if row is None:
            target = random.randint(10, 20)

            con.execute(
                "INSERT INTO targets(day,target) VALUES(?,?)",
                (TODAY, target)
            )
            con.commit()
            return target

        return int(row[0])


target = init_db()


# ---------------- CSS ----------------

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top, #202020, #080808 70%);
    color: white;
}

.block-container {
    max-width: 760px;
    padding-top: 1rem;
}

h1, h2, h3, p, label {
    color: white !important;
}

/* Hide Streamlit toolbar, GitHub, Star and menu icons */
#MainMenu {
    visibility: hidden;
}

header {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

[data-testid="stToolbar"] {
    visibility: hidden !important;
    height: 0 !important;
}

[data-testid="stDecoration"] {
    display: none !important;
}

[data-testid="stStatusWidget"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------- HEADER ----------------

st.title("🎁 Daily Timer Giveaway")

st.markdown(f"""
<div style="
background:linear-gradient(135deg,#9b1515,#330909);
padding:22px;
border-radius:18px;
text-align:center;
border:1px solid #ff5555;
">
<div style="font-size:15px;color:#ffdada">
TODAY'S TARGET
</div>

<div style="
font-size:clamp(48px,10vw,76px);
font-weight:900;
color:white;
">
{target}.000 SEC
</div>

<div style="color:#ffe4e4">
Stop as close as possible to {target}.000 seconds!
</div>
</div>
""", unsafe_allow_html=True)


# ---------------- FOLLOW ----------------

st.markdown("### Instagram")

st.link_button(
    "📸 Follow @oyye_rider",
    "https://www.instagram.com/oyye_rider/"
)

st.warning(
    "Instagram follow status cannot be verified automatically "
    "without authorized Instagram API access."
)

followed = st.checkbox(
    "I have followed @oyye_rider"
)


# ---------------- TIMER COMPONENT ----------------

if followed:

    st.markdown("### Timer Challenge")

    st.caption(
        "START दबाएँ। Target पर beep बजेगा। "
        "STOP करने के बाद Instagram ID submit करें।"
    )

    component_path = str(
        Path(__file__).parent / "timer_component"
    )

    timer_component = components.declare_component(
        "giveaway_timer",
        path=component_path
    )

    result = timer_component(
        target=target,
        day=TODAY,
        key=f"giveaway_timer_{TODAY}"
    )

    # ---------------- SUBMIT ENTRY ----------------

    if isinstance(result, dict) and result.get("submitted"):

        instagram = str(
            result.get("instagram", "")
        ).strip().lstrip("@").lower()

        elapsed = float(
            result.get("elapsed", 0)
        )

        if len(instagram) < 2 or elapsed <= 0 or elapsed > 120:

            st.error("Invalid entry. Please try again.")

        else:

            with db() as con:

                try:
                    con.execute("""
                        INSERT INTO entries(
                            day, instagram, elapsed, created_at
                        )
                        VALUES (?, ?, ?, ?)
                    """, (
                        TODAY,
                        instagram,
                        elapsed,
                        datetime.datetime.now(
                            ZoneInfo("Asia/Kolkata")
                        ).isoformat(timespec="seconds")
                    ))

                    con.commit()

                    st.session_state["submitted_user"] = instagram
                    st.session_state["submitted_elapsed"] = elapsed

                    st.success(
                        f"Entry submitted: @{instagram} — {elapsed:.3f} sec"
                    )

                except sqlite3.IntegrityError:

                    st.error(
                        "This Instagram ID has already submitted today."
                    )


else:

    st.info(
        "Instagram follow confirmation के बाद timer unlock होगा।"
    )


# ---------------- LEADERBOARD ----------------

st.divider()
st.markdown("## 🏆 Today's Leaderboard")

with db() as con:

    entries = con.execute("""
        SELECT instagram, elapsed, created_at
        FROM entries
        WHERE day=?
    """, (TODAY,)).fetchall()


entries.sort(
    key=lambda row: (
        abs(row[1] - target),
        row[2]
    )
)


if not entries:

    st.write("No entries yet. Be the first!")

else:

    for rank, (instagram, elapsed, created) in enumerate(
        entries[:50], 1
    ):

        medal = (
            "🥇" if rank == 1 else
            "🥈" if rank == 2 else
            "🥉" if rank == 3 else
            f"#{rank}"
        )

        difference = abs(elapsed - target)

        st.markdown(f"""
        <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        background:#171717;
        border:1px solid #333;
        border-radius:12px;
        padding:12px;
        margin:7px 0;
        ">
            <div>
                <b>{medal} @{html.escape(instagram)}</b>
                <div style="color:#aaa;font-size:12px">
                    Difference: {difference:.3f} sec
                </div>
            </div>

            <div style="
            font-size:20px;
            font-weight:bold;
            color:#ffdf8a;
            ">
                {elapsed:.3f} sec
            </div>
        </div>
        """, unsafe_allow_html=True)


    winner = entries[0]
    current_user = st.session_state.get("submitted_user")

    # ---------------- WINNER POPUP ----------------

    if current_user and winner[0] == current_user:

        if not st.session_state.get("winner_popup_shown"):

            @st.dialog("🎉 Congratulations! You are the winner!")

            def winner_dialog():

                st.success(
                    f"Your time: {winner[1]:.3f} sec"
                )

                st.write(
                    f"Today's target: {target}.000 sec"
                )

                st.write(
                    "Contact Admin on WhatsApp to claim your prize."
                )

                if ADMIN_WHATSAPP == "91XXXXXXXXXX":

                    st.warning(
                        "Admin WhatsApp number is not configured."
                    )

                else:

                    message = urllib.parse.quote(
                        f"Hello Admin! I am @{current_user}. "
                        f"My stopped time was {winner[1]:.3f} sec. "
                        f"Today's target is {target}.000 sec."
                    )

                    whatsapp_url = (
                        f"https://wa.me/{ADMIN_WHATSAPP}"
                        f"?text={message}"
                    )

                    st.link_button(
                        "📲 Contact Admin on WhatsApp",
                        whatsapp_url
                    )

            st.session_state["winner_popup_shown"] = True

            winner_dialog()


st.caption(
    "Winner is the player closest to today's target. "
    "Instagram follow verification is not implemented."
)
