import streamlit as st
import sqlite3, random, datetime, html, os, urllib.parse
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(page_title="Daily Timer Giveaway", page_icon="🎁", layout="centered")
# Set this in Streamlit Secrets: ADMIN_WHATSAPP = "91XXXXXXXXXX" (digits only)
ADMIN_WHATSAPP = st.secrets.get("ADMIN_WHATSAPP", "91XXXXXXXXXX")
DB_PATH = "giveaway.db"
TODAY = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()

def db(): return sqlite3.connect(DB_PATH, check_same_thread=False)
def init_db():
    with db() as con:
        con.execute("CREATE TABLE IF NOT EXISTS targets(day TEXT PRIMARY KEY, target INTEGER NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS entries(id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, instagram TEXT NOT NULL, elapsed REAL NOT NULL, created_at TEXT NOT NULL, UNIQUE(day,instagram))")
        row=con.execute("SELECT target FROM targets WHERE day=?",(TODAY,)).fetchone()
        if row is None:
            val=random.randint(10,20); con.execute("INSERT INTO targets VALUES(?,?)",(TODAY,val)); con.commit(); return val
        return int(row[0])
target=init_db()
st.markdown("<style>.stApp{background:radial-gradient(circle at top,#202020,#080808 70%);color:white}.block-container{max-width:760px;padding-top:1.3rem}h1,h2,h3,p,label{color:white!important}</style>",unsafe_allow_html=True)
st.title("🎁 Daily Timer Giveaway")
st.caption("Follow Instagram → Timer challenge → Submit Instagram ID after stopping")
st.markdown(f"""<div style='background:linear-gradient(135deg,#9b1515,#330909);padding:22px;border-radius:18px;text-align:center;border:1px solid #ff5555'><div style='font-size:15px;letter-spacing:2px;color:#ffdada'>TODAY'S TARGET</div><div style='font-size:clamp(48px,10vw,76px);font-weight:900;color:white'>{target}.000 <span style='font-size:24px'>SEC</span></div><div style='color:#ffe4e4'>Stop as close as possible to {target}.000 seconds!</div></div>""",unsafe_allow_html=True)
st.link_button("📸 Follow @oyye_rider on Instagram","https://www.instagram.com/oyye_rider/")
followed=st.checkbox("I have followed @oyye_rider")
if not followed: st.warning("Follow Instagram and confirm to unlock the timer.")
else:
    st.caption("Start the timer. A beep sounds at the target. Stop as close as possible. Instagram ID is requested after STOP.")
    component_path=str(Path(__file__).parent / "timer_component")
    result=components.declare_component("giveaway_timer",path=component_path)(target=target,day=TODAY,key=f"timer_{TODAY}")
    if isinstance(result,dict) and result.get("submitted"):
        ig=str(result.get("instagram","")).strip().lstrip("@").lower(); elapsed=float(result.get("elapsed",0))
        if len(ig)<2 or elapsed<=0 or elapsed>120: st.error("Invalid entry. Refresh and try again.")
        else:
            with db() as con:
                try:
                    con.execute("INSERT INTO entries(day,instagram,elapsed,created_at) VALUES(?,?,?,?)",(TODAY,ig,elapsed,datetime.datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")));con.commit()
                    st.session_state["submitted_user"]=ig; st.session_state["submitted_elapsed"]=elapsed
                    st.success(f"Submitted: @{ig} — {elapsed:.3f} sec")
                except sqlite3.IntegrityError: st.error("This Instagram ID has already entered today.")
            st.rerun()
st.divider(); st.markdown("## 🏆 Leaderboard")
with db() as con: entries=con.execute("SELECT instagram,elapsed,created_at FROM entries WHERE day=?",(TODAY,)).fetchall()
entries=sorted(entries,key=lambda r:(abs(r[1]-target),r[2]))
if not entries: st.write("No entries yet. Be the first!")
else:
    for rank,(ig,elapsed,created) in enumerate(entries[:50],1):
        medal="🥇" if rank==1 else "🥈" if rank==2 else "🥉" if rank==3 else f"#{rank}"
        st.markdown(f"""<div style='display:flex;justify-content:space-between;align-items:center;background:#171717;border:1px solid #333;border-radius:12px;padding:12px;margin:7px 0'><div><b>{medal} @{html.escape(ig)}</b><div style='color:#aaa;font-size:12px'>Difference: {abs(elapsed-target):.3f} sec</div></div><div style='font-size:20px;font-weight:bold;color:#ffdf8a'>{elapsed:.3f} sec</div></div>""",unsafe_allow_html=True)
    current=st.session_state.get("submitted_user"); winner=entries[0]
    if current and winner[0]==current and not st.session_state.get("winner_popup_shown"):
        @st.dialog("🎉 Congratulations! You are the current winner!")
        def winner_dialog():
            st.success(f"Your time: {winner[1]:.3f} sec | Target: {target}.000 sec")
            st.write("Tap below to contact the organizer on WhatsApp.")
            if ADMIN_WHATSAPP=="91XXXXXXXXXX": st.warning("Organizer WhatsApp is not configured. Add ADMIN_WHATSAPP in Streamlit Secrets.")
            else:
                msg=urllib.parse.quote(f"Hello, I am @{current}. My timer was {winner[1]:.3f} sec for target {target}.000 sec.")
                st.link_button("📲 Contact Admin on WhatsApp",f"https://wa.me/{ADMIN_WHATSAPP}?text={msg}")
        st.session_state["winner_popup_shown"]=True; winner_dialog()
st.caption("Winner is the entry closest to today's target. Follow status is not verified through Instagram API.")
