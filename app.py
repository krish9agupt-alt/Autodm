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
st.set_page_config(
    page_title="Oyye Rider | Daily Timer Challenge",
    page_icon="⏱️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CREATE TIMER & CODE GATE COMPONENT (V3) ---
COMPONENT_DIR = Path(__file__).parent / "timer_component_v3"
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
      padding: 6px 4px;
      overflow: hidden;
    }
    .card {
      background: linear-gradient(145deg, #1a0000, #0a0000);
      border: 1px solid #d4af37;
      border-radius: 14px;
      padding: 18px 14px;
      box-shadow: 0 4px 15px rgba(212, 175, 55, 0.15);
    }
    h3 {
      margin: 0 0 10px 0;
      color: #d4af37;
      font-size: 1.3rem;
    }
    p {
      color: #ccc;
      font-size: 0.92rem;
      margin: 0 0 14px 0;
      line-height: 1.4;
    }
    input[type="text"] {
      width: 100%;
      max-width: 300px;
      padding: 14px;
      font-size: 1.1rem;
      border-radius: 10px;
      border: 1px solid #d4af37;
      background: #050505;
      color: #fff;
      text-align: center;
      font-weight: bold;
      text-transform: uppercase;
      margin-bottom: 12px;
      outline: none;
      user-select: text;
      -webkit-user-select: text;
    }
    #timer-display {
      font-size: 4rem;
      font-weight: 900;
      color: #d4af37;
      font-family: 'Courier New', Courier, monospace;
      text-shadow: 0 0 18px rgba(212, 175, 55, 0.7);
      margin-bottom: 18px;
      letter-spacing: 2px;
      background: #0a0000;
      border: 2px solid #330000;
      border-radius: 14px;
      padding: 12px 10px;
    }
    .btn-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
      align-items: center;
    }
    button {
      width: 100%;
      max-width: 300px;
      padding: 15px 18px;
      font-size: 1.15rem;
      border-radius: 12px;
      border: 1px solid #d4af37;
      cursor: pointer;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1px;
      transition: transform 0.1s, opacity 0.2s;
    }
    button:active:not(:disabled) { transform: scale(0.98); }
    .gold-btn {
      background: linear-gradient(45deg, #cc0000, #880000);
      color: white;
      box-shadow: 0 0 12px rgba(204, 0, 0, 0.5);
    }
    #start-btn {
      background: linear-gradient(45deg, #1a1a1a, #333333);
      color: #d4af37;
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
    #status-msg, #code-msg {
      margin-top: 10px;
      font-size: 0.9rem;
      color: #ff5555;
      font-weight: 600;
      min-height: 20px;
    }
    .hidden { display: none !important; }
  </style>
</head>
<body>

  <!-- VIEW 1: DAILY VIDEO CODE GATE -->
  <div id="code-gate-view" class="card hidden">
    <h3>🔒 Enter Today's Video Code</h3>
    <p>आज के Giveaway में भाग लेने के लिए <b>@oyye_rider</b> की आज की वीडियो देखें और उसमें बताया गया कोड नीचे डालें。<br><span style="color:#ff9800; font-size:0.82rem;">(ध्यान रहे: आप एक दिन में सिर्फ 1 बार ही इस कोड और वेबसाइट का उपयोग कर सकते हैं!)</span></p>
    <input type="text" id="secret-input" placeholder="ENTER VIDEO CODE..." autocomplete="off" />
    <div class="btn-container">
      <button id="unlock-btn" class="gold-btn">🔓 UNLOCK CHALLENGE</button>
    </div>
    <div id="code-msg"></div>
  </div>

  <!-- VIEW 2: TIMER CHALLENGE -->
  <div id="timer-view" class="hidden">
    <div id="timer-display">00.000</div>
    <div class="btn-container">
      <button id="start-btn">START TIMER</button>
      <button id="stop-btn" disabled>STOP TIMER</button>
    </div>
    <div id="status-msg"></div>
  </div>

  <!-- VIEW 3: ALREADY USED TODAY (1 DAY 1 ATTEMPT LOCK) -->
  <div id="used-view" class="card hidden">
    <h3 id="used-title" style="color:#4CAF50;">✅ Today's Attempt Completed!</h3>
    <div id="used-time-box" style="font-family:monospace; font-size:1.8rem; color:#d4af37; font-weight:bold; margin:10px 0;"></div>
    <p id="used-desc">आप आज इस मोबाइल पर अपना 1 बार का चांस और कोड इस्तेमाल कर चुके हैं। अब आप कल के नए वीडियो कोड के साथ दोबारा खेल सकते हैं!</p>
  </div>

  <script>
    function sendMessageToStreamlitClient(type, data) {
      const outData = Object.assign({ isStreamlitMessage: true, type: type }, data);
      window.parent.postMessage(outData, "*");
    }
    function setComponentReady() { sendMessageToStreamlitClient("streamlit:componentReady", {apiVersion: 1}); }
    function setFrameHeight(height) { sendMessageToStreamlitClient("streamlit:setFrameHeight", {height: height}); }
    function setComponentValue(value) { sendMessageToStreamlitClient("streamlit:setComponentValue", {value: value}); }

    let target = 10;
    let today = "";
    let expectedCode = "";
    let startTime = 0;
    let isRunning = false;
    let beepPlayed = false;
    let audioCtx = null;
    let lastStateSent = "";

    const codeGateView = document.getElementById("code-gate-view");
    const timerView = document.getElementById("timer-view");
    const usedView = document.getElementById("used-view");

    const secretInput = document.getElementById("secret-input");
    const unlockBtn = document.getElementById("unlock-btn");
    const codeMsg = document.getElementById("code-msg");

    const display = document.getElementById("timer-display");
    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const statusMsg = document.getElementById("status-msg");

    const usedTitle = document.getElementById("used-title");
    const usedTimeBox = document.getElementById("used-time-box");
    const usedDesc = document.getElementById("used-desc");

    function syncToPython(payload) {
      const serialized = JSON.stringify(payload);
      if (serialized !== lastStateSent) {
        lastStateSent = serialized;
        setComponentValue(payload);
      }
    }

    function playBeep() {
      try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === 'suspended') audioCtx.resume();
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
      } catch (e) {}
    }

    function formatTime(sec) {
      const s = Math.max(0, sec);
      const whole = Math.floor(s).toString().padStart(2, '0');
      const ms = Math.round((s - Math.floor(s)) * 1000);
      if (ms === 1000) return `${(Math.floor(s) + 1).toString().padStart(2, '0')}.000`;
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

    function refreshUI() {
      const savedAttempt = localStorage.getItem(`oyye_attempt_${today}`);
      const hasStarted = localStorage.getItem(`oyye_started_${today}`);
      const unlockedCode = localStorage.getItem(`oyye_unlocked_code_${today}`);

      // Case 1: User already completed their 1 attempt today
      if (savedAttempt !== null) {
        const val = parseFloat(savedAttempt);
        codeGateView.classList.add("hidden");
        timerView.classList.add("hidden");
        usedView.classList.remove("hidden");
        usedTitle.innerText = "✅ Today's Attempt Completed!";
        usedTitle.style.color = "#4CAF50";
        usedTimeBox.innerText = formatTime(val) + " SEC";
        setFrameHeight(210);
        syncToPython({ status: "STOPPED", elapsed: val });
        return;
      }

      // Case 2: User started timer and refreshed page to cheat
      if (hasStarted === "true" && !isRunning) {
        codeGateView.classList.add("hidden");
        timerView.classList.add("hidden");
        usedView.classList.remove("hidden");
        usedTitle.innerText = "🚫 Attempt Locked for Today!";
        usedTitle.style.color = "#ff4444";
        usedTimeBox.innerText = "LOCKED";
        usedDesc.innerText = "आपने टाइमर चालू करने के बाद पेज रिफ्रेश कर दिया। एक दिन में सिर्फ 1 ही चांस मिलता है, अब आप कल खेल सकते हैं!";
        setFrameHeight(210);
        syncToPython({ status: "REFRESH_LOCKED", elapsed: null });
        return;
      }

      // Case 3: User unlocked today's valid code and is ready to play
      if (unlockedCode === expectedCode) {
        codeGateView.classList.add("hidden");
        usedView.classList.add("hidden");
        timerView.classList.remove("hidden");
        setFrameHeight(265);
        syncToPython({ status: "UNLOCKED", elapsed: null });
        return;
      }

      // Case 4: Show Video Code Login Gate
      timerView.classList.add("hidden");
      usedView.classList.add("hidden");
      codeGateView.classList.remove("hidden");
      setFrameHeight(285);
      syncToPython({ status: "LOCKED_CODE", elapsed: null });
    }

    unlockBtn.onclick = () => {
      const entered = (secretInput.value || "").trim().toUpperCase();
      if (!entered) {
        codeMsg.innerText = "❌ कृपया वीडियो में बताया गया कोड डालें!";
        return;
      }
      if (entered === expectedCode) {
        localStorage.setItem(`oyye_unlocked_code_${today}`, expectedCode);
        codeMsg.innerText = "";
        refreshUI();
      } else {
        codeMsg.innerText = "❌ गलत कोड! @oyye_rider की आज की वीडियो ध्यान से देखें।";
      }
    };

    startBtn.onclick = () => {
      if (isRunning) return;
      try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === 'suspended') audioCtx.resume();
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
      localStorage.setItem(`oyye_attempt_${today}`, elapsed.toString());
      refreshUI();
    };

    window.addEventListener("message", function(event) {
      if (event.data.type !== "streamlit:render") return;
      const args = event.data.args;
      target = Number(args.target || 10);
      today = String(args.today || "");
      expectedCode = String(args.expected_code || "OYYERIDER").trim().toUpperCase();
      if (!isRunning) {
        refreshUI();
      }
    });

    setComponentReady();
    setFrameHeight(285);
  </script>
</body>
</html>
"""

@st.cache_resource
def setup_component_and_db():
    COMPONENT_DIR.mkdir(exist_ok=True)
    if not INDEX_HTML.exists() or INDEX_HTML.read_text(encoding="utf-8") != HTML_CODE:
        INDEX_HTML.write_text(HTML_CODE, encoding="utf-8")
    
    conn = sqlite3.connect('giveaway.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS targets (day TEXT PRIMARY KEY, target INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_codes (day TEXT PRIMARY KEY, code TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS entries 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT, instagram TEXT, 
                  elapsed REAL, created_at TEXT, UNIQUE(day, instagram))''')
    conn.commit()
    return conn

conn = setup_component_and_db()
timer_component = components.declare_component("timer_component_v3", path=str(COMPONENT_DIR))

# --- CUSTOM CSS ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #050505; color: #ffffff; }
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
        display: none !important;
        visibility: hidden !important;
    }
    #MainMenu, footer, header {
        display: none !important;
        visibility: hidden !important;
    }
    .viewerBadge_container__r5tak,
    .viewerBadge_link__qRIco,
    .styles_viewerBadge__CvC9N,
    ._container_gzau3_1,
    ._profileContainer_gzau3_53,
    ._profilePreview_gzau3_63,
    [data-testid="manage-app-button"],
    a[href*="streamlit.io/cloud"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    
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
        padding: 12px 14px; border-bottom: 1px solid #330000;
        font-family: monospace; font-size: 1rem;
    }
    .leaderboard-row:last-child { border-bottom: none; }
    .leaderboard-row:nth-child(odd) { background-color: rgba(255,0,0,0.05); }
    .rank-1 { color: #ffd700; font-weight: bold; font-size: 1.15rem; }
    .rank-2 { color: #c0c0c0; font-weight: bold; font-size: 1.08rem; }
    .rank-3 { color: #cd7f32; font-weight: bold; font-size: 1.05rem; }
</style>
""", unsafe_allow_html=True)

# --- TIMEZONE, DAILY TARGET & DAILY VIDEO CODE ---
IST = ZoneInfo('Asia/Kolkata')
today_ist = datetime.now(IST).strftime('%Y-%m-%d')
WIN_TOLERANCE = 0.001

def get_daily_target(date_str):
    c = conn.cursor()
    c.execute("SELECT target FROM targets WHERE day = ?", (date_str,))
    row = c.fetchone()
    if row:
        return int(row[0])
    new_target = random.randint(10, 20)
    c.execute("INSERT OR IGNORE INTO targets (day, target) VALUES (?, ?)", (date_str, new_target))
    conn.commit()
    c.execute("SELECT target FROM targets WHERE day = ?", (date_str,))
    return int(c.fetchone()[0])

def get_daily_secret_code(date_str):
    c = conn.cursor()
    c.execute("SELECT code FROM daily_codes WHERE day = ?", (date_str,))
    row = c.fetchone()
    if row and row[0]:
        return str(row[0]).strip().upper()
    return str(st.secrets.get("DAILY_CODE", "OYYERIDER")).strip().upper()

def set_daily_secret_code(date_str, new_code):
    clean_code = new_code.strip().upper()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO daily_codes (day, code) VALUES (?, ?)", (date_str, clean_code))
    conn.commit()

daily_target = get_daily_target(today_ist)
secret_video_code = get_daily_secret_code(today_ist)
min_win_time = daily_target - WIN_TOLERANCE
max_win_time = daily_target + WIN_TOLERANCE

# --- UI HEADER ---
st.markdown("<p class='brand-title'>@oyye_rider <span class='gold-highlight'>Giveaway</span></p>", unsafe_allow_html=True)
st.markdown("<a href='https://www.instagram.com/oyye_rider/' target='_blank' class='insta-btn'>📸 Watch Today's Reel on @oyye_rider</a>", unsafe_allow_html=True)

# --- RENDER UNIFIED CODE GATE + TIMER COMPONENT ---
comp_state = timer_component(
    target=daily_target,
    today=today_ist,
    expected_code=secret_video_code,
    key="daily_gate_timer"
)

status = comp_state.get("status", "LOCKED_CODE") if isinstance(comp_state, dict) else "LOCKED_CODE"
elapsed_val = comp_state.get("elapsed") if isinstance(comp_state, dict) else None

# Show Target Card only once code is unlocked or attempt completed
if status in ("UNLOCKED", "STOPPED", "REFRESH_LOCKED"):
    st.markdown(
        f'<div class="glass-card">'
        f'<h3 style="text-align:center; margin:0; color:#d4af37;">🎯 Today\'s Target Time</h3>'
        f'<div class="target-box"><span class="target-time">{daily_target:.3f} SEC</span></div>'
        f'<p style="text-align:center; color:#ccc; font-size: 0.9rem; margin:0;">'
        f'Win Rule: Stop at exact <b>{daily_target:.3f}s</b> or within <b>±0.001s</b> (<b>{min_win_time:.3f}s – {max_win_time:.3f}s</b>)!'
        f'</p></div>',
        unsafe_allow_html=True
    )

# --- ENTRY SUBMISSION LOGIC ---
if "entry_submitted_day" not in st.session_state or st.session_state.entry_submitted_day != today_ist:
    st.session_state.entry_submitted = False
    st.session_state.entry_submitted_day = today_ist

if status == "STOPPED" and elapsed_val is not None:
    stopped_time = round(float(elapsed_val), 3)
    difference = round(abs(stopped_time - daily_target), 3)
    is_qualifying_hit = difference <= WIN_TOLERANCE
    
    border_col = "#4CAF50" if is_qualifying_hit else "#ff9800"
    status_title = "🎯 WINNING ZONE HIT!" if is_qualifying_hit else "⏱️ Timer Stopped!"
    
    st.markdown(
        f'<div class="glass-card" style="border-color: {border_col};">'
        f'<h3 style="text-align:center; color:{border_col}; margin-top:0;">{status_title}</h3>'
        f'<p style="text-align:center; font-family:monospace; font-size:1.15rem; margin-bottom:0;">'
        f'Stopped Time: <b>{stopped_time:.3f}s</b><br>'
        f'Target Time: <b>{daily_target:.3f}s</b><br>'
        f'Difference: <b style="color:#ffd700;">{difference:.3f}s</b>'
        f'</p></div>',
        unsafe_allow_html=True
    )
    
    if not st.session_state.entry_submitted:
        with st.form("submission_form"):
            st.write("लीडरबोर्ड में अपना नाम दर्ज करने के लिए Instagram Username डालें (सिर्फ 1 बार):")
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
                        st.warning(f"@{clean_user} आज पहले ही सबमिट किया जा चुका है!")
                        st.session_state.entry_submitted = True
                        st.session_state.current_user = clean_user

# --- LEADERBOARD & WINNER LOGIC (SHOWN ONLY AFTER UNLOCK OR ATTEMPT) ---
if status in ("UNLOCKED", "STOPPED", "REFRESH_LOCKED"):
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
            st.markdown(
                f'<div class="glass-card" style="border-color: #ffd700; text-align:center;">'
                f'<div style="color:#ffd700; font-weight:bold; font-size:1.1rem;">👑 CURRENT WINNER (±0.001s QUALIFIED)</div>'
                f'<div style="font-size:1.5rem; font-weight:900; margin:6px 0;">@{top_user}</div>'
                f'<div style="font-family:monospace; color:#ccc;">'
                f'Stopped: <b>{top_elapsed:.3f}s</b> | Diff: <b style="color:#4CAF50;">{top_diff:.3f}s</b>'
                f'</div></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="glass-card" style="border-color: #ff4444; text-align:center;">'
                f'<div style="color:#ff4444; font-weight:bold; font-size:1.1rem;">⏳ NO WINNER YET TODAY</div>'
                f'<div style="font-size:0.95rem; color:#ccc; margin:6px 0;">'
                f'To win, stop at exact <b>{daily_target:.3f}s</b> or within <b>±0.001s</b> (<b>{min_win_time:.3f}s – {max_win_time:.3f}s</b>).'
                f'</div>'
                f'<div style="font-family:monospace; font-size:0.85rem; color:#999;">'
                f'Closest so far: @{top_user} ({top_elapsed:.3f}s | Diff: {top_diff:.3f}s)'
                f'</div></div>',
                unsafe_allow_html=True
            )

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
            
            st.markdown(
                f'<div class="glass-card" style="border: 2px solid #25D366; background: #06210e; text-align:center;">'
                f'<h3 style="color:#4CAF50; margin-top:0;">🎉 CONGRATULATIONS @{top_user}!</h3>'
                f'<p style="font-size:0.95rem;">You hit the winning zone (<b>±0.001s</b>) and are <b>Rank #1</b>!</p>'
                f'<p style="font-family:monospace; font-size:0.9rem;">'
                f'Stopped: {top_elapsed:.3f}s | Target: {daily_target:.3f}s | Diff: {top_diff:.3f}s'
                f'</p>'
                f'<a href="{wa_url}" target="_blank" style="display:inline-block; background:#25D366; color:white; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:bold; margin-top:8px;">'
                f'💬 Claim Prize on WhatsApp'
                f'</a></div>',
                unsafe_allow_html=True
            )

        # Render Top 50 Table
        rows_list = ['<div class="glass-card" style="padding:5px 0;">']
        for idx, (insta, elapsed_item, diff_val, created_at) in enumerate(leaderboard):
            rank = idx + 1
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
            rank_class = f"rank-{rank}" if rank <= 3 else ""
            diff_color = "#4CAF50" if diff_val <= WIN_TOLERANCE else "#d4af37"
            row_str = (
                f'<div class="leaderboard-row">'
                f'<div class="{rank_class}" style="width:16%;">{medal}</div>'
                f'<div style="width:42%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">@{insta}</div>'
                f'<div style="width:21%; text-align:right; color:#aaa;">{elapsed_item:.3f}s</div>'
                f'<div style="width:21%; text-align:right; color:{diff_color};">Δ {diff_val:.3f}s</div>'
                f'</div>'
            )
            rows_list.append(row_str)
        rows_list.append('</div>')
        st.markdown("".join(rows_list), unsafe_allow_html=True)

# --- CREATOR ADMIN PANEL ---
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("⚙️ Creator Admin Panel"):
    admin_pin_secret = str(st.secrets.get("ADMIN_PIN", "9999"))
    entered_pin = st.text_input("Admin PIN", type="password")
    new_video_code = st.text_input("Set Today's New Video Code (e.g., RIDER77)")
    if st.button("Update Today's Code"):
        if entered_pin == admin_pin_secret:
            if new_video_code.strip():
                set_daily_secret_code(today_ist, new_video_code)
                st.success(f"✅ Today's Video Code updated to: {new_video_code.strip().upper()}")
                st.rerun()
            else:
                st.warning("Please enter a valid code.")
        else:
            st.error("❌ Invalid Admin PIN!")
