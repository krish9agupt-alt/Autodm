import streamlit as st
import sqlite3, os, secrets, hashlib, time
from datetime import datetime, date
from zoneinfo import ZoneInfo

TZ=ZoneInfo("Asia/Kolkata")
DB_PATH=os.getenv("DB_PATH","giveaway.db")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","")
ADMIN_UPI=os.getenv("ADMIN_UPI_ID","")
TARGET_MIN=float(os.getenv("TARGET_MIN","5.0"))
TARGET_MAX=float(os.getenv("TARGET_MAX","15.0"))
TOLERANCE_MS=int(os.getenv("TOLERANCE_MS","200"))
PRIZE="₹100"

st.set_page_config(page_title="Daily Giveaway",page_icon="🎁",layout="centered")

def today():
    return datetime.now(TZ).date().isoformat()

def connect():
    conn=sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS daily (
            day TEXT PRIMARY KEY, target REAL NOT NULL, winner_entry_id INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL,
            username TEXT NOT NULL, device_key TEXT NOT NULL,
            elapsed REAL NOT NULL, diff REAL NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(day, device_key), UNIQUE(day, username)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS winner_upi (
            day TEXT PRIMARY KEY, entry_id INTEGER NOT NULL, upi TEXT NOT NULL
        )""")

def get_daily():
    d=today()
    with connect() as c:
        row=c.execute("SELECT * FROM daily WHERE day=?",(d,)).fetchone()
        if row: return dict(row)
        target=round(TARGET_MIN+(TARGET_MAX-TARGET_MIN)*secrets.randbelow(1000000)/1000000,3)
        c.execute("INSERT OR IGNORE INTO daily(day,target,winner_entry_id) VALUES(?,?,NULL)",(d,target))
        row=c.execute("SELECT * FROM daily WHERE day=?",(d,)).fetchone()
        return dict(row)

def entries_for_day(d):
    with connect() as c:
        return c.execute("SELECT * FROM entries WHERE day=? ORDER BY diff ASC, created_at ASC",(d,)).fetchall()

def get_winner(d):
    with connect() as c:
        row=c.execute("""SELECT e.* FROM daily d LEFT JOIN entries e ON e.id=d.winner_entry_id
                         WHERE d.day=?""",(d,)).fetchone()
        return row

def get_entry(id_):
    with connect() as c:
        return c.execute("SELECT * FROM entries WHERE id=?",(id_,)).fetchone()

def lock_winner(d):
    with connect() as c:
        c.execute("""UPDATE daily SET winner_entry_id=(SELECT id FROM entries
                   WHERE day=? ORDER BY diff ASC, created_at ASC LIMIT 1)
                   WHERE day=? AND winner_entry_id IS NULL AND EXISTS
                   (SELECT 1 FROM entries WHERE day=?)""",(d,d,d))

init_db()
daily=get_daily()
d=today()

st.markdown("""
<style>
.block-container{max-width:760px;padding-top:1.4rem}
.winner{background:linear-gradient(135deg,#171717,#06110C);padding:22px;border-radius:18px;color:#fff;border:1px solid #A31C1B}
.winner h1,.winner h2,.winner p{color:white}
div.stButton>button{border-radius:12px;font-weight:700;min-height:45px}
</style>
""",unsafe_allow_html=True)

st.title("🎁 Daily Giveaway")
st.caption(f"{datetime.now(TZ).strftime('%d %b %Y')} • Daily Prize {PRIZE} • Free Entry")

winner=get_winner(d)
if winner and winner["id"]:
    st.markdown(f"""<div class="winner"><p>🏆 TODAY'S WINNER</p><h1>{winner['username']}</h1>
    <h2>{winner['elapsed']:.3f} sec</h2><p>Prize: {PRIZE}</p></div>""",unsafe_allow_html=True)
else:
    st.info("Today's winner will be announced after the daily entries are finalized.")

st.subheader("⏱️ Stop the timer")
st.write(f"Today's secret target is randomly generated between {TARGET_MIN:.1f}–{TARGET_MAX:.1f} seconds.")
st.caption("Target is hidden from players. The backend records elapsed time; exact millisecond accuracy can be affected by internet/server latency.")

# username is required and serves as basic duplicate key. Not a verified Instagram identity.
username=st.text_input("Instagram username (without @)",max_chars=30,placeholder="your_instagram_username")
device_key=st.text_input("Device code (for daily lock)", type="password", help="MVP lock: use a unique code saved by you. This is not secure device fingerprinting.")
device_key_hash=hashlib.sha256(device_key.strip().encode()).hexdigest() if device_key.strip() else ""

with connect() as c:
    existing=None
    if device_key_hash:
        existing=c.execute("SELECT * FROM entries WHERE day=? AND device_key=?",(d,device_key_hash)).fetchone()
    user_existing=None
    if username.strip():
        user_existing=c.execute("SELECT * FROM entries WHERE day=? AND username=?",(d,username.strip().lower())).fetchone()

if existing or user_existing:
    st.warning("This device code or Instagram username has already played today. One attempt per day.")
    e=existing or user_existing
    st.success(f"Recorded time: {e['elapsed']:.3f} sec")
elif winner and winner["id"]:
    st.warning("Today's winner is already locked. Game is closed.")
else:
    if "started_at" not in st.session_state:
        st.session_state.started_at=None
    if "stopped_elapsed" not in st.session_state:
        st.session_state.stopped_elapsed=None
    if st.session_state.stopped_elapsed is None:
        col1,col2=st.columns(2)
        with col1:
            if st.button("▶️ START TIMER",use_container_width=True,disabled=not (username.strip() and device_key.strip())):
                st.session_state.started_at=time.perf_counter()
                st.session_state.stopped_elapsed=None
                st.rerun()
        with col2:
            if st.button("🛑 STOP TIMER",use_container_width=True,disabled=st.session_state.started_at is None):
                st.session_state.stopped_elapsed=time.perf_counter()-st.session_state.started_at
                st.session_state.started_at=None
                st.rerun()
        if st.session_state.started_at is not None:
            st.warning("Timer started! Press STOP once.")
            st.metric("Timer",f"{time.perf_counter()-st.session_state.started_at:.3f} sec")
            if st.button("Refresh timer"):
                st.rerun()
    else:
        elapsed=float(st.session_state.stopped_elapsed)
        st.metric("Your stopped time",f"{elapsed:.3f} sec")
        st.write("Submit your Instagram name to record your single attempt.")
        if st.button("Submit my time",use_container_width=True):
            name=username.strip().lower().lstrip("@")
            key=device_key_hash
            if not name or not key:
                st.error("Enter Instagram username and device code first.")
            else:
                diff=abs(elapsed-float(daily["target"]))
                with connect() as c:
                    try:
                        c.execute("INSERT INTO entries(day,username,device_key,elapsed,diff,created_at) VALUES(?,?,?,?,?,?)",
                                  (d,name,key,elapsed,diff,datetime.now(TZ).isoformat()))
                    except sqlite3.IntegrityError:
                        st.error("Already played today.")
                    else:
                        # Winner is finalized by Admin after the entry window closes.
                        st.session_state.started_at=None
                        st.session_state.stopped_elapsed=None
                        st.success("Your time has been submitted!")
                        st.rerun()

st.divider()
st.subheader("🏁 Today's Leaderboard")
rows=entries_for_day(d)
if rows:
    for i,row in enumerate(rows[:20],1):
        label="🥇" if i==1 else f"{i}."
        st.write(f"{label} **@{row['username']}** — {row['elapsed']:.3f} sec")
else:
    st.caption("No entries yet.")

st.divider()
st.subheader("🔐 Admin")
with st.expander("Admin login"):
    admin_pw=st.text_input("Admin password",type="password",key="admin_password")
    if st.button("Login to Admin"):
        if ADMIN_PASSWORD and secrets.compare_digest(admin_pw,ADMIN_PASSWORD):
            st.session_state.admin=True
        else:
            st.error("Incorrect password or ADMIN_PASSWORD is not configured.")
    if st.session_state.get("admin"):
        st.success("Admin authenticated")
        st.write(f"**Secret target:** {daily['target']:.3f} sec")
        st.write(f"**Admin UPI ID:** {ADMIN_UPI if ADMIN_UPI else 'Set ADMIN_UPI_ID environment variable'}")
        st.write("Only Admin sees the UPI ID. Do not put it in public code or GitHub.")
        st.write("Entries are ranked by closest time to the target.")
        if st.button("Finalize winner (closest time)"):
            lock_winner(d)
            st.success("Winner finalized for today.")
            st.rerun()
        if st.button("Admin logout"):
            st.session_state.admin=False
            st.rerun()

st.caption("Giveaway MVP. Admin must finalize the daily winner. Avoid collecting sensitive payment details publicly.")
