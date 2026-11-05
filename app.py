import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from zoneinfo import ZoneInfo
from datetime import datetime
import random
import urllib.parse
import re
from pathlib import Path

# --- PAGE CONFIG ---
st.set_page_config(page_title="Oyye Rider | Daily Timer Challenge", page_icon="⏱️", layout="centered")

# --- AUTO-CREATE BULLETPROOF TIMER COMPONENT (ZERO EXTERNAL CDN) ---
COMPONENT_DIR = Path(__file__).parent / "timer_component_v2"
COMPONENT_DIR.mkdir(exist_ok=True)
INDEX_HTML = COMPONENT_DIR / "index.html"

HTML_CODE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * { box-sizing: border-box; user-select: none; -webkit-user-select: none; }
    body {
      background: transparent;
      color: white;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      text-align: center;
      margin: 0;
      padding: 10px 5px;
      overflow: hidden;
    }
    #timer-display {
      font-size: 4.2rem;
      font-weight: 900;
      color: #d4af37;
      font-family: 'Courier New', Courier, monospace;
      text-shadow: 0 0 18px rgba(212, 175, 55, 0.7);
      margin-bottom: 20px;
      letter-spacing: 2px;
      background: #0a0000;
      border: 2px solid #330000;
      border-radius: 14px;
      padding: 12px 10px;
    }
    .btn-container {
      display: flex;
      flex-direction: column;
      gap: 14px;
      align-items: center;
    }
    button {
      width: 100%;
      max-width: 320px;
      padding: 16px 20px;
      font-size: 1.25rem;
      border-radius: 12px;
      border: 1px solid #d4af37;
      cursor: pointer;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1px;
      transition: transform 0.1s, opacity 0.2s;
    }
    button:active:not(:disabled) {
      transform: scale(0.98);
    }
    #start-btn {
      background: linear-gradient(45deg, #1a1a1a, #333333);
      color: #d4af37;
      box-shadow: 0 4px 12px rgba(212, 175, 55, 0.2);
    }
    #stop-btn {
      background: linear-gradient(45deg, #cc0000, #880000);
      color: white;
      box-shadow: 0 0 15px rgba(204, 0, 0, 0.6);
    }
    button:disabled {
      opacity: 0.35;
      cursor: not-allowed;
      background: #1a1a1a;
      border-color: #444;
      box-shadow: none;
      color: #666;
    }
    #status-msg {
      margin-top: 12px;
      font-size: 0.9rem;
      color: #ff5555;
      font-weight: 600;
      min-height: 20px;
    }
  </style>
</head>
<body>
  <div id="timer-display">00.000</div>
  <div class="btn-container">
    <button id="start-btn">START TIMER</button>
    <button id="stop-btn" disabled>STOP TIMER</button>
  </div>
  <div id="status-msg"></div>

  <script>
    function sendMessageToStreamlitClient(type, data) {
      const outData = Object.assign({
        isStreamlitMessage: true,
        type: type,
      }, data);
      window.parent.postMessage(outData, "*");
    }

    function setComponentReady() {
      sendMessageToStreamlitClient("streamlit:componentReady", {apiVersion: 1});
    }

    function setFrameHeight(height) {
      sendMessageToStreamlitClient("streamlit:setFrameHeight", {height: height});
    }

    function setComponentValue(value) {
      sendMessageToStreamlitClient("streamlit:setComponentValue", {value: value});
    }

    let target = 10;
    let today = "";
    let startTime = 0;
    let isRunning = false;
    let beepPlayed = false;
    let audioCtx = null;
    let initialized = false;

    const display = document.getElementById("timer-display");
    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const statusMsg = document.getElementById("status-msg");

    function playBeep() {
      try {
        if (!audioCtx) {
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
          audioCtx.resume();
        }
        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        osc.type = 'sine';
        osc.frequency.value = 880;
        gainNode.gain.setValueAtTime(0.5, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.25);
        osc.start(audioCtx.currentTime);
        osc.stop(audioCtx.currentTime + 0.25);
      } catch (e) {
        console.warn("Audio error:", e);
      }
    }

    function formatTime(sec) {
      const s = Math.max(0, sec);
      const whole = Math.floor(s).toString().padStart(2, '0');
      const ms = Math.round((s - Math.floor(s)) * 1000);
      if (ms === 1000) {
        return `${(Math.floor(s) + 1).toString().padStart(2, '0')}.000`;
      }
      return `${whole}.${ms.toString().padStart(3, '0')}`;
    }

    function updateTimer() {
      if (!isRunning) return;
      const now = performance.now();
      const elapsed = (now - startTime) / 1000;
      display.innerText = formatTime(elapsed);

      if (elapsed >= target && !beepPlayed) {
        playBeep();
        beepPlayed = true;
      }
      requestAnimationFrame(updateTimer);
    }

    startBtn.onclick = () => {
      if (isRunning) return;
      try {
        if (!audioCtx) {
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
          audioCtx.resume();
        }
      } catch (e) {}

      localStorage.setItem(`oyye_started_${today}`, "true");
      startTime = performance.now();
      isRunning = true;
      startBtn.disabled = true;
      stopBtn.disabled = false;
      beepPlayed = false;
      statusMsg.innerText = "Timer running... Stop at exact " + target.toFixed(3) + "s!";
      statusMsg.style.color = "#d4af37";
      requestAnimationFrame(updateTimer);
    };

    stopBtn.onclick = () => {
      if (!isRunning) return;
      isRunning = false;
      stopBtn.disabled = true;
      const now = performance.now();
      const elapsed = Number(((now - startTime) / 1000).toFixed(3));
      display.innerText = formatTime(elapsed);
      
      localStorage.setItem(`oyye_attempt_${today}`, elapsed.toString());
      statusMsg.innerText = "Timer stopped! Scroll down to submit your Instagram username.";
      statusMsg.style.color = "#4CAF50";
      
      setComponentValue(elapsed);
    };

    window.addEventListener("message", function(event) {
      if (event.data.type !== "streamlit:render") return;
      const args = event.data.args;
      target = Number(args.target || 10);
      today = String(args.today || "");

      if (!initialized) {
        initialized = true;
        const savedAttempt = localStorage.getItem(`oyye_attempt_${today}`);
        const hasStarted = localStorage.getItem(`oyye_started_${today}`);

        if (savedAttempt !== null) {
          const val = parseFloat(savedAttempt);
          display.innerText = formatTime(val);
          startBtn.disabled = true;
          stopBtn.disabled = true;
          statusMsg.innerText = "You have completed today's attempt on this device.";
          statusMsg.style.color = "#4CAF50";
          setComponentValue(val);
        } else if (hasStarted === "true" && !isRunning) {
          display.innerText = "LOCKED";
          display.style.color = "#ff4444";
          startBtn.disabled = true;
          stopBtn.disabled = true;
          statusMsg.innerText = "Attempt locked! Refreshing after starting is not allowed.";
        }
      }
      setFrameHeight(270);
    });

    setComponentReady();
    setFrameHeight(270);
  </script>
</body>
</html>
"""

INDEX_HTML.write_text(HTML_CODE, encoding="utf-8")
timer_component = components.declare_component("timer_component", path=str(COMPONENT_DIR))

# --- CUSTOM CSS (Dark Gaming Theme) ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #050505; color: #ffffff; }
    [data-testid="stHeader"] { background-color: transparent; }
    #MainMenu, footer, header { visibility: hidden; }
    
    .brand-title { text-align: center; color: #ffffff; font-weight: 900; font-size: 2rem; margin-bottom: 5px; }
    .gold-highlight { color: #d4af37; text-shadow: 0 0 10px rgba(212,175,55,0.4); }
    
    .glass-card {
        background: linear-gradient(145deg, #1a0000, #0a0000);
        border: 1px solid #d4af37;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 18px;
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.12);
    }
    
    .target-box {
        text-align: center;
        background: #000;
        border: 2px dashed #cc0000;
        border-radius: 10px;
        padding: 12px;
        margin: 10px 0;
    }
    .target-time { font-size: 2.3rem; font-family: monospace; color: #ff3333; font-weight: bold; }
    
    .insta-btn {
        display: block; width: 100%; text-align: center;
        background: linear-gradient(45deg, #833ab4, #fd1d1d, #fcb045);
        color: white !important; padding: 12px; border-radius: 10px;
        text-decoration: none; font-weight: bold; margin-bottom: 15px;
    }
    .insta-btn:hover { opacity: 0.92; }
    
    .stButton>button {
        width: 100%; background: linear-gradient(45deg, #cc0000, #880000);
        border: 1px solid #d4af37; color: white; font-weight: bold;
        border-radius: 8px; padding: 10px;
    }

    .leaderboard-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 12px; border-bottom: 1px solid #330000;
        font-family: monospace; font-size: 1rem;
    }
    .leaderboard-row:nth-child(odd) { background-color: rgba(255,0,0,0.05); }
    .rank-1 { color: #ffd700; font-weight: bold; font-size: 1.15rem; }
    .rank-2 { color: #c0c0c0; font-weight: bold; }
    .rank-3 { color: #cd7f32; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- INIT DATABASE & TIMEZONE ---
IST = ZoneInfo('Asia/Kolkata')
today_ist = datetime.now(IST).strftime('%Y-%m-%d')
WIN_TOLERANCE = 0.001  # Exact target (0.000) or +/- 0.001s

def init_db():
    conn = sqlite3.connect('giveaway.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS targets (day TEXT PRIMARY KEY, target INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS entries 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT, instagram TEXT, 
                  elapsed REAL, created_at TEXT, UNIQUE(day, instagram))''')
    conn.commit()
    return conn

conn = init_db()

def get_daily_target(date_str):
    c = conn.cursor()
    c.execute("SELECT target FROM targets WHERE day = ?", (date_str,))
    row = c.fetchone()
    if row:
        return int(row[0])
    new_target = random.randint(10, 20)
    c.execute("INSERT INTO targets (day, target) VALUES (?, ?)", (date_str, new_target))
    conn.commit()
    return new_target

daily_target = get_daily_target(today_ist)
min_win_time = daily_target - WIN_TOLERANCE
max_win_time = daily_target + WIN_TOLERANCE

# --- UI HEADER ---
st.markdown("<p class='brand-title'>@oyye_rider <span class='gold-highlight'>Giveaway</span></p>", unsafe_allow_html=True)
st.markdown("<a href='https://www.instagram.com/oyye_rider/' target='_blank' class='insta-btn'>📸 Follow @oyye_rider on Instagram</a>", unsafe_allow_html=True)

st.markdown(f"""
<div class="glass-card">
    <h3 style='text-align:center; margin:0; color:#d4af37;'>🎯 Today's Target Time</h3>
    <div class="target-box">
        <span class="target-time">{daily_target:.3f} SEC</span>
    </div>
    <p style='text-align:center; color:#ccc; font-size: 0.9rem; margin:0;'>
        Win Rule: Stop at exact <b>{daily_target:.3f}s</b> or within <b>±0.001s</b> (<b>{min_win_time:.3f}s – {max_win_time:.3f}s</b>)!
    </p>
</div>
""", unsafe_allow_html=True)

# --- RENDER TIMER COMPONENT ---
timer_value = timer_component(target=daily_target, today=today_ist, key="daily_timer")

# --- ENTRY SUBMISSION LOGIC ---
if "entry_submitted_day" not in st.session_state or st.session_state.entry_submitted_day != today_ist:
    st.session_state.entry_submitted = False
    st.session_state.entry_submitted_day = today_ist

if timer_value is not None:
    stopped_time = round(float(timer_value), 3)
    difference = round(abs(stopped_time - daily_target), 3)
    is_qualifying_hit = difference <= WIN_TOLERANCE
    
    border_col = "#4CAF50" if is_qualifying_hit else "#ff9800"
    status_title = "🎯 WINNING ZONE HIT!" if is_qualifying_hit else "⏱️ Timer Stopped!"
    
    st.markdown(f"""
    <div class="glass-card" style="border-color: {border_col};">
        <h3 style="text-align:center; color:{border_col}; margin-top:0;">{status_title}</h3>
        <p style="text-align:center; font-family:monospace; font-size:1.15rem; margin-bottom:0;">
            Stopped Time: <b>{stopped_time:.3f}s</b><br>
            Target Time: <b>{daily_target:.3f}s</b><br>
            Difference: <b style="color:#ffd700;">{difference:.3f}s</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.entry_submitted:
        with st.form("submission_form"):
            st.write("Enter your Instagram username to join today's leaderboard:")
            insta_user = st.text_input("Instagram Username (with or without @)")
            submitted = st.form_submit_button("Submit Entry")
            
            if submitted:
                clean_user = insta_user.strip().lower().lstrip('@')
                if not clean_user or not re.match(r'^[a-z0-9._]{1,30}$', clean_user):
                    st.error("Please enter a valid Instagram username (letters, numbers, periods, underscores).")
                else:
                    timestamp = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                    c = conn.cursor()
                    try:
                        with conn:
                            c.execute(
                                "INSERT INTO entries (day, instagram, elapsed, created_at) VALUES (?, ?, ?, ?)",
                                (today_ist, clean_user, stopped_time, timestamp)
                            )
                        st.session_state.entry_submitted = True
                        st.session_state.current_user = clean_user
                        st.success(f"Entry confirmed for @{clean_user}!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.warning(f"@{clean_user} has already submitted an entry today!")
                        st.session_state.entry_submitted = True
                        st.session_state.current_user = clean_user

# --- LEADERBOARD & WINNER LOGIC ---
st.markdown("### 🏆 Today's Top 50 Leaderboard")

c = conn.cursor()
c.execute("""
    SELECT instagram, elapsed, ROUND(ABS(elapsed - ?), 3) AS diff, created_at 
    FROM entries 
    WHERE day = ? 
    ORDER BY diff ASC, created_at ASC 
    LIMIT 50
""", (daily_target, today_ist))
leaderboard = c.fetchall()

if not leaderboard:
    st.info("No entries yet for today. Stop the timer at the exact target (±0.001s) to win!")
else:
    top_user, top_elapsed, top_diff, top_time = leaderboard[0]
    has_qualifying_winner = top_diff <= WIN_TOLERANCE
    
    if has_qualifying_winner:
        st.markdown(f"""
        <div class="glass-card" style="border-color: #ffd700; text-align:center;">
            <div style="color:#ffd700; font-weight:bold; font-size:1.1rem;">👑 CURRENT WINNER (±0.001s QUALIFIED)</div>
            <div style="font-size:1.5rem; font-weight:900; margin:6px 0;">@{top_user}</div>
            <div style="font-family:monospace; color:#ccc;">
                Stopped: <b>{top_elapsed:.3f}s</b> | Diff: <b style="color:#4CAF50;">{top_diff:.3f}s</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="glass-card" style="border-color: #ff4444; text-align:center;">
            <div style="color:#ff4444; font-weight:bold; font-size:1.1rem;">⏳ NO WINNER YET TODAY</div>
            <div style="font-size:0.95rem; color:#ccc; margin:6px 0;">
                To win, stop at exact <b>{daily_target:.3f}s</b> or within <b>±0.001s</b> (<b>{min_win_time:.3f}s – {max_win_time:.3f}s</b>).
            </div>
            <div style="font-family:monospace; font-size:0.85rem; color:#999;">
                Closest so far: @{top_user} ({top_elapsed:.3f}s | Diff: {top_diff:.3f}s)
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Show Winner Popup & WhatsApp Claim Button ONLY if #1 AND within 0.001s of target
    is_qualifying_winner = (
        has_qualifying_winner and
        st.session_state.get("entry_submitted") and 
        st.session_state.get("current_user") == top_user
    )

    if is_qualifying_winner:
        st.balloons()
        admin_wa = st.secrets.get("ADMIN_WHATSAPP", "910000000000")
        wa_msg = (
            f"Hi @oyye_rider Admin! I hit the winning target in the Daily Timer Giveaway!\n\n"
            f"Instagram: @{top_user}\n"
            f"Stopped Time: {top_elapsed:.3f}s\n"
            f"Daily Target: {daily_target:.3f}s\n"
            f"Difference: {top_diff:.3f}s\n"
            f"Date: {today_ist}"
        )
        wa_url = f"https://wa.me/{admin_wa}?text={urllib.parse.quote(wa_msg)}"
        
        st.markdown(f"""
        <div class="glass-card" style="border: 2px solid #25D366; background: #06210e; text-align:center;">
            <h3 style="color:#4CAF50; margin-top:0;">🎉 CONGRATULATIONS @{top_user}!</h3>
            <p style="font-size:0.95rem;">You hit the winning zone (<b>±0.001s</b>) and are <b>Rank #1</b>!</p>
            <p style="font-family:monospace; font-size:0.9rem;">
                Stopped: {top_elapsed:.3f}s | Target: {daily_target:.3f}s | Diff: {top_diff:.3f}s
            </p>
            <a href="{wa_url}" target="_blank" style="display:inline-block; background:#25D366; color:white; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:bold; margin-top:8px;">
                💬 Claim Prize on WhatsApp
            </a>
        </div>
        """, unsafe_allow_html=True)

    # Render Top 50 Table
    rows_html = '<div class="glass-card" style="padding:5px 0;">'
    for idx, (insta, elapsed_val, diff_val, created_at) in enumerate(leaderboard):
        rank = idx + 1
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
        rank_class = f"rank-{rank}" if rank <= 3 else ""
        diff_color = "#4CAF50" if diff_val <= WIN_TOLERANCE else "#d4af37"
        rows_html += f"""
        <div class="leaderboard-row">
            <div class="{rank_class}" style="width:18%;">{medal}</div>
            <div style="width:38%; overflow:hidden; text-overflow:ellipsis;">@{insta}</div>
            <div style="width:22%; text-align:right; color:#aaa;">{elapsed_val:.3f}s</div>
            <div style="width:22%; text-align:right; color:{diff_color};">Δ {diff_val:.3f}s</div>
        </div>
        """
    rows_html += '</div>'
    st.markdown(rows_html, unsafe_allow_html=True)
