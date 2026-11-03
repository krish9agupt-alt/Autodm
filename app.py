import streamlit as st
import sqlite3, os, secrets, hashlib, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components

TZ=ZoneInfo("Asia/Kolkata")
DB_PATH=os.getenv("DB_PATH","giveaway.db")
ADMIN_USER=os.getenv("ADMIN_USER","Admin")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","@Krish9A")
ADMIN_UPI=os.getenv("ADMIN_UPI_ID","")
INSTAGRAM_USERNAME=os.getenv("INSTAGRAM_USERNAME","your_instagram_page")
TARGET_MIN=float(os.getenv("TARGET_MIN","5.0"))
TARGET_MAX=float(os.getenv("TARGET_MAX","15.0"))
PRIZE="₹100"

st.set_page_config(page_title="Daily Giveaway",page_icon="🎁",layout="centered")

def now():
    return datetime.now(TZ)
def today():
    return now().date().isoformat()
def connect():
    conn=sqlite3.connect(DB_PATH,timeout=20,check_same_thread=False)
    conn.row_factory=sqlite3.Row
    return conn
def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS daily(day TEXT PRIMARY KEY,target REAL NOT NULL,winner_entry_id INTEGER)""")
        c.execute("""CREATE TABLE IF NOT EXISTS entries(
            id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, username TEXT NOT NULL,
            elapsed REAL NOT NULL, diff REAL NOT NULL, created_at TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS play_locks(username TEXT PRIMARY KEY, stopped_at TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS winner_upi(day TEXT PRIMARY KEY,entry_id INTEGER NOT NULL,upi TEXT NOT NULL)""")
def get_daily():
    d=today()
    with connect() as c:
        row=c.execute("SELECT * FROM daily WHERE day=?",(d,)).fetchone()
        if row: return dict(row)
        target=round(TARGET_MIN+(TARGET_MAX-TARGET_MIN)*secrets.randbelow(1000000)/1000000,3)
        c.execute("INSERT OR IGNORE INTO daily(day,target,winner_entry_id) VALUES(?,?,NULL)",(d,target))
        row=c.execute("SELECT * FROM daily WHERE day=?",(d,)).fetchone()
        return dict(row)
def get_entries(d):
    with connect() as c:
        return c.execute("SELECT * FROM entries WHERE day=? ORDER BY diff ASC,created_at ASC",(d,)).fetchall()
def get_winner(d):
    with connect() as c:
        return c.execute("""SELECT e.* FROM daily d LEFT JOIN entries e ON e.id=d.winner_entry_id WHERE d.day=?""",(d,)).fetchone()
def lock_winner(d):
    with connect() as c:
        c.execute("""UPDATE daily SET winner_entry_id=(SELECT id FROM entries WHERE day=? ORDER BY diff ASC,created_at ASC LIMIT 1)
                     WHERE day=? AND winner_entry_id IS NULL AND EXISTS(SELECT 1 FROM entries WHERE day=?)""",(d,d,d))
def get_lock(username):
    if not username: return None
    with connect() as c:
        return c.execute("SELECT stopped_at FROM play_locks WHERE username=?",(username.lower(),)).fetchone()
def cooldown_remaining(username):
    row=get_lock(username)
    if not row: return 0
    try:
        stopped=datetime.fromisoformat(row["stopped_at"])
        remaining=24*60*60-(now()-stopped).total_seconds()
        return max(0,int(remaining))
    except Exception: return 0
def set_lock(username):
    with connect() as c:
        c.execute("""INSERT INTO play_locks(username,stopped_at) VALUES(?,?)
                     ON CONFLICT(username) DO UPDATE SET stopped_at=excluded.stopped_at""",
                  (username.lower(),now().isoformat()))

init_db()
d=today()
daily=get_daily()
st.markdown("""
<style>
.block-container{max-width:760px;padding-top:1.2rem}
.winner{background:linear-gradient(135deg,#171717,#06110C);padding:22px;border-radius:18px;color:#fff;border:1px solid #A31C1B}
.winner h1,.winner h2,.winner p{color:white}
div.stButton>button{border-radius:12px;font-weight:700;min-height:45px}
</style>
""",unsafe_allow_html=True)

# Hidden admin entrance: hold for 6 seconds
components.html("""
<div style="text-align:center;margin:12px 0">
<button id="secretAdmin" style="background:#171717;color:#aaa;border:1px solid #444;border-radius:9px;padding:9px 16px;font-size:12px;user-select:none;touch-action:none">
Hold here for 6 seconds • Admin
</button>
<div id="holdMsg" style="font-size:11px;color:#777;margin-top:5px"></div>
</div>
<script>
const b=document.getElementById('secretAdmin'), msg=document.getElementById('holdMsg');
let timer=null, start=0;
function begin(e){e.preventDefault();start=Date.now();msg.textContent='Keep holding…';timer=setTimeout(()=>{msg.textContent='Opening admin…';window.parent.location.href=window.parent.location.pathname+'?admin=1';},6000);}
function end(){if(timer)clearTimeout(timer);timer=null;if(Date.now()-start<6000)msg.textContent='Hold for the full 6 seconds';}
b.addEventListener('pointerdown',begin);b.addEventListener('pointerup',end);b.addEventListener('pointerleave',end);b.addEventListener('pointercancel',end);
</script>
""",height=70)

if st.query_params.get("admin")=="1":
    st.title("🔐 Admin Login")
    admin_user=st.text_input("Admin User")
    admin_pass=st.text_input("Passcode",type="password")
    if st.button("Login"):
        if secrets.compare_digest(admin_user,ADMIN_USER) and secrets.compare_digest(admin_pass,ADMIN_PASSWORD):
            st.session_state.admin_auth=True
            st.success("Admin login successful")
        else:
            st.error("Wrong username or passcode")
    if st.session_state.get("admin_auth"):
        st.subheader("Admin Dashboard")
        st.write(f"**Today's secret target:** {daily['target']:.3f} seconds")
        st.write(f"**Admin-only UPI ID:** {ADMIN_UPI or 'Set ADMIN_UPI_ID in environment/secrets'}")
        if st.button("Finalize today's closest-time winner"):
            lock_winner(d)
            st.success("Winner locked.")
            st.rerun()
        st.write("Today's entries:")
        for row in get_entries(d):
            st.write(f"@{row['username']} — {row['elapsed']:.3f}s (difference {row['diff']:.3f}s)")
        if st.button("Logout"):
            st.session_state.admin_auth=False
            st.rerun()
    st.stop()

st.title("🎁 Daily Giveaway")
st.caption(f"{now().strftime('%d %b %Y')} • Prize {PRIZE} • Free Entry")
winner=get_winner(d)
if winner and winner["id"]:
    st.markdown(f"""<div class="winner"><p>🏆 TODAY'S WINNER</p><h1>@{winner['username']}</h1><h2>{winner['elapsed']:.3f} sec</h2><p>Prize: {PRIZE}</p></div>""",unsafe_allow_html=True)
else:
    st.info("Today's winner will be shown here after Admin finalizes the entries.")

st.subheader("📲 Follow to participate")
st.link_button(f"Open Instagram @{INSTAGRAM_USERNAME}",f"https://www.instagram.com/{INSTAGRAM_USERNAME}/",use_container_width=True)
followed=st.checkbox(f"I have followed @{INSTAGRAM_USERNAME}")
st.caption("Follow status is self-confirmed in this prototype. It is not automatically verified by Instagram.")
st.subheader("⏱️ Timer Challenge")
st.caption("Today's target is secret. Closest submitted time wins. Timer precision can be affected by browser/network delays.")
username=st.text_input("Instagram username (without @)",max_chars=30,placeholder="your_username").strip().lower().lstrip("@")
remaining=cooldown_remaining(username)
if remaining>0:
    hours=remaining//3600; mins=(remaining%3600)//60; secs=remaining%60
    st.warning(f"@{username} has already played. Try again in {hours:02d}:{mins:02d}:{secs:02d} (24-hour cooldown).")
elif winner and winner["id"]:
    st.warning("Today's winner is finalized. Game is closed.")
elif not followed:
    st.info("Follow the Instagram page and check the box to enable the timer.")
else:
    if "started_at" not in st.session_state: st.session_state.started_at=None
    if "stopped_elapsed" not in st.session_state: st.session_state.stopped_elapsed=None
    if st.session_state.stopped_elapsed is None:
        col1,col2=st.columns(2)
        with col1:
            if st.button("▶️ START TIMER",use_container_width=True,disabled=not username):
                st.session_state.started_at=time.perf_counter()
                st.session_state.stopped_elapsed=None
                st.rerun()
        with col2:
            if st.button("🛑 STOP TIMER",use_container_width=True,disabled=st.session_state.started_at is None):
                elapsed=time.perf_counter()-st.session_state.started_at
                st.session_state.stopped_elapsed=elapsed
                st.session_state.started_at=None
                # Lock username for 24h immediately on timer stop, before submit.
                set_lock(username)
                st.rerun()
        if st.session_state.started_at is not None:
            st.warning("Timer is running. Press STOP once.")
            st.metric("Elapsed",f"{time.perf_counter()-st.session_state.started_at:.3f} sec")
            if st.button("Refresh display"): st.rerun()
    else:
        elapsed=float(st.session_state.stopped_elapsed)
        st.metric("Your stopped time",f"{elapsed:.3f} sec")
        st.write("Enter your name above, then submit your attempt.")
        if st.button("Submit my time",use_container_width=True):
            if not username:
                st.error("Enter Instagram username.")
            else:
                diff=abs(elapsed-float(daily["target"]))
                with connect() as c:
                    c.execute("INSERT INTO entries(day,username,elapsed,diff,created_at) VALUES(?,?,?,?,?)",
                              (d,username,elapsed,diff,now().isoformat()))
                st.session_state.stopped_elapsed=None
                st.success("Time submitted. You cannot play again for 24 hours.")
                st.rerun()

st.divider()
st.subheader("🏁 Today's Leaderboard")
rows=get_entries(d)
if rows:
    for i,row in enumerate(rows[:30],1):
        st.write(f"{'🥇' if i==1 else f'{i}.'} **@{row['username']}** — {row['elapsed']:.3f} sec")
else:
    st.caption("No entries yet.")
st.caption("Winner is finalized by Admin based on closest time to the hidden target.")
