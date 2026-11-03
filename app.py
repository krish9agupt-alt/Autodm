import streamlit as st
import sqlite3, random, datetime, json, html
import streamlit.components.v1 as components

st.set_page_config(page_title="Daily Timer Giveaway", page_icon="🎁", layout="centered")

DB_PATH = "giveaway.db"
TODAY = datetime.date.today().isoformat()

def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS targets (
            day TEXT PRIMARY KEY, target INTEGER NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL, instagram TEXT NOT NULL,
            elapsed REAL NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(day, instagram))""")
        row = con.execute("SELECT target FROM targets WHERE day=?", (TODAY,)).fetchone()
        if row is None:
            target = random.randint(10, 20)
            con.execute("INSERT INTO targets(day,target) VALUES (?,?)", (TODAY,target))
            con.commit()
            return target
        return row[0]

target = init_db()

st.markdown("""
<style>
.stApp {background: radial-gradient(circle at top, #202020, #080808 70%); color:#fff;}
.block-container {max-width: 760px; padding-top: 1.5rem;}
h1,h2,h3,p,label {color:#fff!important;}
div[data-testid="stMetric"] {background:#171717; border:1px solid #333; padding:14px; border-radius:14px;}
</style>
""", unsafe_allow_html=True)

st.title("🎁 Daily Timer Giveaway")
st.caption("Follow Instagram → Start Timer → Stop near the target → Submit Instagram ID")
st.markdown(f"""
<div style="background:linear-gradient(135deg,#9b1515,#330909);padding:22px;border-radius:18px;text-align:center;border:1px solid #ff5555">
<div style="font-size:15px;letter-spacing:2px;color:#ffdada">TODAY'S TARGET</div>
<div style="font-size:clamp(48px,10vw,76px);font-weight:900;line-height:1.15;color:white">{target}.000 <span style="font-size:24px">SEC</span></div>
<div style="font-size:15px;color:#ffe4e4">Stop as close as possible to {target}.000 seconds!</div>
</div>
""", unsafe_allow_html=True)

st.markdown("### 1️⃣ Follow Instagram")
st.link_button("📸 Follow @oyye_rider on Instagram", "https://www.instagram.com/oyye_rider/")
st.info("Instagram follow status is not verified automatically. Follow the account, then continue.")

if "follow_confirmed" not in st.session_state:
    st.session_state.follow_confirmed = False
st.checkbox("I have followed @oyye_rider", key="follow_confirmed")

st.markdown("### 2️⃣ Enter your Instagram username")
username = st.text_input("Instagram ID (without @)", placeholder="your_instagram_id").strip().lstrip("@")
username_clean = username.lower()

st.markdown("### 3️⃣ Timer Challenge")
st.caption("Press START. The timer runs smoothly in your browser. At the target, a beep sounds. Press STOP as close to the target as possible.")

if st.session_state.follow_confirmed:
    if not username or len(username) < 2:
        st.warning("Enter your Instagram username first.")
    else:
        already = False
        with db() as con:
            already = con.execute("SELECT 1 FROM entries WHERE day=? AND instagram=?", (TODAY, username_clean)).fetchone() is not None
        if already:
            st.warning("This Instagram ID has already submitted today.")
        else:
            timer_html = r"""
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#111;color:white;font-family:Arial,sans-serif">
<div style="border:1px solid #333;border-radius:16px;background:#151515;padding:18px;text-align:center">
  <div id="status" style="color:#ffb3b3;font-size:14px;margin-bottom:8px">READY</div>
  <div id="display" style="font-size:clamp(52px,13vw,86px);font-weight:900;font-variant-numeric:tabular-nums;letter-spacing:1px">00.000</div>
  <div style="font-size:13px;color:#aaa;margin:4px 0 14px">SECONDS</div>
  <button id="start" style="background:#16803c;color:white;border:0;border-radius:12px;padding:15px 28px;font-size:20px;font-weight:bold;width:48%">START</button>
  <button id="stop" disabled style="background:#b32020;color:white;border:0;border-radius:12px;padding:15px 28px;font-size:20px;font-weight:bold;width:48%;opacity:.5">STOP</button>
  <div id="result" style="margin-top:14px;font-size:16px;color:#ffe0a3"></div>
</div>
<script>
const target = __TARGET__;
let startAt=null, raf=null, stopped=false, beeped=false;
const display=document.getElementById('display'), status=document.getElementById('status');
const startBtn=document.getElementById('start'), stopBtn=document.getElementById('stop'), result=document.getElementById('result');
function beep(){
 try {
   const ctx=new (window.AudioContext||window.webkitAudioContext)();
   const osc=ctx.createOscillator(), gain=ctx.createGain();
   osc.type='sine'; osc.frequency.value=880; gain.gain.value=.18;
   osc.connect(gain); gain.connect(ctx.destination); osc.start();
   setTimeout(()=>{osc.stop();ctx.close();},220);
 } catch(e){}
}
function tick(){
 if(startAt===null || stopped) return;
 const ms=performance.now()-startAt, sec=ms/1000;
 display.textContent=sec.toFixed(3);
 if(!beeped && sec>=target){beeped=true;beep();status.textContent='🎯 TARGET! STOP NOW';status.style.color='#ffe066';}
 raf=requestAnimationFrame(tick);
}
startBtn.onclick=()=>{
 if(startAt!==null) return;
 startAt=performance.now(); status.textContent='RUNNING'; startBtn.disabled=true;startBtn.style.opacity='.5';
 stopBtn.disabled=false;stopBtn.style.opacity='1';raf=requestAnimationFrame(tick);
};
stopBtn.onclick=()=>{
 if(startAt===null||stopped)return;
 stopped=true;cancelAnimationFrame(raf);
 const elapsed=(performance.now()-startAt)/1000;
 display.textContent=elapsed.toFixed(3);status.textContent='STOPPED';stopBtn.disabled=true;
 result.textContent='Stopped time: '+elapsed.toFixed(3)+' sec';
 const payload={elapsed:elapsed, user:__USERNAME__};
 window.parent.postMessage({type:'streamlit:setComponentValue',value:payload},'*');
 window.parent.postMessage({type:'streamlit:setFrameHeight',height:240},'*');
};
</script></body></html>
"""
            timer_html = timer_html.replace("__TARGET__", str(target)).replace("__USERNAME__", json.dumps(username_clean))
            stopped_data = components.html(timer_html, height=260, scrolling=False)
            if isinstance(stopped_data, dict) and "elapsed" in stopped_data:
                elapsed = float(stopped_data["elapsed"])
                # store once; username is already collected outside the iframe
                with db() as con:
                    try:
                        con.execute("INSERT INTO entries(day,instagram,elapsed,created_at) VALUES(?,?,?,?)",
                                    (TODAY, username_clean, elapsed, datetime.datetime.now().isoformat(timespec="seconds")))
                        con.commit()
                        st.success(f"Time submitted: {elapsed:.3f} sec")
                    except sqlite3.IntegrityError:
                        st.warning("This Instagram ID has already submitted today.")
                st.rerun()
else:
    st.warning("Follow Instagram and tick the confirmation box to unlock the timer.")

st.divider()
st.markdown("## 🏆 Today's Leaderboard")
with db() as con:
    rows=con.execute("SELECT instagram,elapsed,created_at FROM entries WHERE day=?", (TODAY,)).fetchall()
rows=sorted(rows,key=lambda r:(abs(r[1]-target), r[2]))
if not rows:
    st.write("No entries yet. Be the first!")
else:
    for i,(ig,elapsed,created) in enumerate(rows[:50], start=1):
        diff=abs(elapsed-target)
        medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"#{i}"
        st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;background:#171717;border:1px solid #333;border-radius:12px;padding:12px 14px;margin:7px 0">
<div><b>{medal} @{html.escape(ig)}</b><div style="color:#aaa;font-size:12px">Difference: {diff:.3f} sec</div></div>
<div style="font-size:20px;font-weight:bold;color:#ffdf8a">{elapsed:.3f} sec</div>
</div>
""", unsafe_allow_html=True)
    winner=rows[0]
    st.success(f"Current closest: @{winner[0]} — {winner[1]:.3f} sec. Admin will contact the winner.")

st.markdown("---")
st.caption("Winner is the entry closest to today's target. Admin contacts the winner directly. Avoid submitting sensitive payment details publicly.")
