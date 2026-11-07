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
    page_title="Oyye Rider | 10x Timer Giveaway",
    page_icon="⏱️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- SAFE SECRETS HELPER ---
def get_secret_safe(key, default_val):
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return default_val

# --- CREATE TIMER & CODE GATE COMPONENT (V7) ---
COMPONENT_DIR = Path(__file__).parent / "timer_component_v7"
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
    <p><b>@oyye_rider</b> की आज की वीडियो देखें और उसमें बताया गया Secret Code यहाँ डालें ताकि आप 10x Winning Prize जीत सकें!<br><span style="color:#ff9800; font-size:0.82rem;">(नोट: एक दिन में सिर्फ 1 ही चांस मिलेगा!)</span></p>
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

  <!-- VIEW 3: ALREADY USED TODAY -->
  <div id="used-view" class="card hidden">
    <h3 id="used-title" style="color:#4CAF50;">✅ Today's Attempt Completed!</h3>
    <div id="used-time-box" style="font-family:monospace; font-size:1.8rem; color:#d4af37; font-weight:bold; margin:10px 0;"></div>
    <p id="used-desc">आप आज अपना 1 बार का प्रयास कर चुके हैं। कल नए वीडियो कोड के साथ फिर आएं!</p>
  </div>

  <script>
    function sendMessageToStreamlitClient(type, data) {
      const outData = Object.assign({ isStreamlitMessage: true, type: type }, data);
      window.parent.postMessage(outData, "*");
    }
    function setComponentReady() { sendMessageToStreamlitClient("streamlit:componentReady", {apiVersion: 1}); }
    function setFrameHeight(height) { sendMessageToStreamlitClient("streamlit:setFrameHeight", {height: height}); }
    function setComponentValue(value) { sendMessageToStreamlitClient("streamlit:setComponentValue", {value: value}); }

    let target = 5;
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

      if (savedAttempt !== null) {
        const val = parseFloat(savedAttempt);
        codeGateView.classList.add("hidden");
        timerView.classList.add("hidden");
        usedView.classList.remove("hidden");
        usedTitle.innerText = "✅ Attempt Finished!";
        usedTitle.style.color = "#4CAF50";
        usedTimeBox.innerText = formatTime(val) + " SEC";
        setFrameHeight(210);
        syncToPython({ status: "STOPPED", elapsed: val });
        return;
      }

      if (hasStarted === "true" && !isRunning) {
        codeGateView.classList.add("hidden");
        timerView.classList.add("hidden");
        usedView.classList.remove("hidden");
        usedTitle.innerText = "🚫 Attempt Locked!";
        usedTitle.style.color = "#ff4444";
        usedTimeBox.innerText = "LOCKED";
        usedDesc.innerText = "पेज रिफ्रेश करने के कारण आपका आज का चांस लॉक हो गया है।";
        setFrameHeight(210);
        syncToPython({ status: "REFRESH_LOCKED", elapsed: null });
        return;
      }

      if (unlockedCode === expectedCode) {
        codeGateView.classList.add("hidden");
        usedView.classList.add("hidden");
        timerView.classList.remove("hidden");
        setFrameHeight(265);
        syncToPython({ status: "UNLOCKED", elapsed: null });
        return;
      }

      timerView.classList.add("hidden");
      usedView.classList.add("hidden");
      codeGateView.classList.remove("hidden");
      setFrameHeight(285);
      syncToPython({ status: "LOCKED_CODE", elapsed: null });
    }

    unlockBtn.onclick = () => {
      const entered = (secretInput.value || "").trim().toUpperCase();
      if (!entered) {
        codeMsg.innerText = "❌ कृपया वीडियो कोड डालें!";
        return;
      }
      if (entered === expectedCode) {
        localStorage.setItem(`oyye_unlocked_code_${today}`, expectedCode);
        codeMsg.innerText = "";
        refreshUI();
      } else {
        codeMsg.innerText = "❌ गलत कोड! वीडियो ध्यान से देखें।";
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
      let elapsed = Number(((now - startTime) / 1000).toFixed(3));
      localStorage.setItem(`oyye_attempt_${today}`, elapsed.toString());
      refreshUI();
    };

    window.addEventListener("message", function(event) {
      if (event.data.type !== "streamlit:render") return;
      const args = event.data.args;
      target = Number(args.target || 5);
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

def setup_component_and_db():
    COMPONENT_DIR.mkdir(exist_ok=True)
    if not INDEX_HTML.exists() or INDEX_HTML.read_text(encoding="utf-8") != HTML_CODE:
        INDEX_HTML.write_text(HTML_CODE, encoding="utf-8")
    
    conn = sqlite3.connect('giveaway.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS targets (day TEXT PRIMARY KEY, target INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_codes (day TEXT PRIMARY KEY, code TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin_settings (key TEXT PRIMARY KEY, val TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS entries 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT, instagram TEXT, 
                  elapsed REAL, created_at TEXT, UNIQUE(day, instagram))''')
    conn.commit()
    return conn

conn = setup_component_and_db()
timer_component = components.declare_component("timer_component_v7", path=str(COMPONENT_DIR))

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
    
    .brand-title { text-align: center; color: #ffffff; font-weight: 900; font-size: 2rem; margin-bottom: 5px; cursor: pointer; }
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
        text-decoration: none; font-weight: bold; margin-bottom: 10px;
    }
    .insta-btn:hover { opacity: 0.92; }

    .channel-btn {
        display: block; width: 100%; text-align: center;
        background: linear-gradient(45deg, #0088cc, #0044aa);
        color: white !important; padding: 12px; border-radius: 10px;
        text-decoration: none; font-weight: bold; margin-bottom: 15px;
    }
    .channel-btn:hover { opacity: 0.92; }
    
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

# --- TIMEZONE, TARGET & ADMIN SETTINGS ---
IST = ZoneInfo('Asia/Kolkata')
today_ist = datetime.now(IST).strftime('%Y-%m-%d')
WIN_TOLERANCE = 0.001

def get_db_setting(key, default_val):
    c = conn.cursor()
    c.execute("SELECT val FROM admin_settings WHERE key = ?", (key,))
    row = c.fetchone()
    if row and row[0]:
        return row[0]
    return get_secret_safe(key, default_val)

def set_db_setting(key, val):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO admin_settings (key, val) VALUES (?, ?)", (key, val))
    conn.commit()

def get_daily_target(date_str):
    c = conn.cursor()
    c.execute("SELECT target FROM targets WHERE day = ?", (date_str,))
    row = c.fetchone()
    if row:
        return int(row[0])
    new_target = random.randint(1, 10)
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
    return get_db_setting("DAILY_CODE", "OYYERIDER").upper()

def set_daily_secret_code(date_str, new_code):
    clean_code = new_code.strip().upper()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO daily_codes (day, code) VALUES (?, ?)", (date_str, clean_code))
    conn.commit()

daily_target = get_daily_target(today_ist)
secret_video_code = get_daily_secret_code(today_ist)
min_win_time = daily_target - WIN_TOLERANCE
max_win_time = daily_target + WIN_TOLERANCE

insta_channel_link = get_db_setting("INSTA_CHANNEL", "https://instagram.com/oyye_rider")
admin_whatsapp_num = get_db_setting("ADMIN_WHATSAPP", "910000000000")

# --- UI HEADER WITH CLICKABLE GIVEAWAY TITLE FOR ADMIN PANEL ---
if "show_admin" not in st.session_state:
    st.session_state.show_admin = False
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

title_clicked = st.button("🔥 @oyye_rider — 10x Giveaway 🔥", use_container_width=True)
if title_clicked:
    st.session_state.show_admin = not st.session_state.show_admin
    if not st.session_state.show_admin:
        st.session_state.admin_authenticated = False

st.markdown(f"<a href='https://www.instagram.com/oyye_rider/' target='_blank' class='insta-btn'>📸 Follow @oyye_rider on Instagram</a>", unsafe_allow_html=True)
st.markdown(f"<a href='{insta_channel_link}' target='_blank' class='channel-btn'>📢 Join Instagram Broadcast Channel</a>", unsafe_allow_html=True)

# --- SECURE CREATOR ADMIN PANEL ---
if st.session_state.show_admin:
    st.markdown('<div class="glass-card" style="border-color: #d4af37;">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Creator Admin Panel")
    
    admin_pin_secret = get_db_setting("ADMIN_PIN", "#KRISH91")
    
    # Step 1: Ask for password first if not authenticated
    if not st.session_state.admin_authenticated:
        entered_pin = st.text_input("Enter Admin Password", type="password", placeholder="Enter password (#KRISH91)...")
        if st.button("Verify Password"):
            if entered_pin == admin_pin_secret:
                st.session_state.admin_authenticated = True
                st.success("✅ Access Granted!")
                st.rerun()
            else:
                st.error("❌ Invalid Admin Password!")
    else:
        # Step 2: Show settings only AFTER correct password verification
        st.success("🔓 Authenticated Successfully")
        new_video_code = st.text_input("Set Today's New Video Code (e.g., RIDER77)")
        new_channel_link = st.text_input("Set Instagram Channel Link", value=insta_channel_link)
        new_wa_num = st.text_input("Set Admin WhatsApp Number (with Country Code)", value=admin_whatsapp_num)
        new_admin_pass = st.text_input("Change Admin Password (Optional)", type="password", placeholder="Leave blank or enter new password")
        
        if st.button("Save All Settings"):
            if new_video_code.strip():
                set_daily_secret_code(today_ist, new_video_code)
            set_db_setting("INSTA_CHANNEL", new_channel_link.strip())
            set_db_setting("ADMIN_WHATSAPP", new_wa_num.strip())
            if new_admin_pass.strip():
                set_db_setting("ADMIN_PIN", new_admin_pass.strip())
            
            st.success("✅ All settings updated successfully!")
            st.session_state.show_admin = False
            st.session_state.admin_authenticated = False
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

# --- RENDER COMPONENT ---
comp_state = timer_component(
    target=daily_target,
    today=today_ist,
    expected_code=secret_video_code,
    key="daily_gate_timer_v7"
)

status = comp_state.get("status", "LOCKED_CODE") if isinstance(comp_state, dict) else "LOCKED_CODE"
elapsed_val = comp_state.get("elapsed") if isinstance(comp_state, dict) else None

if status in ("UNLOCKED", "STOPPED", "REFRESH_LOCKED"):
    st.markdown(
        f'<div class="glass-card">'
        f'<h3 style="text-align:center; margin:0; color:#d4af37;">🎯 Today\'s Target Time (1 - 10s)</h3>'
        f'<div class="target-box"><span class="target-time">{daily_target}.000 SEC</span></div>'
        f'<p style="text-align:center; color:#ccc; font-size: 0.9rem; margin:0;">'
        f'Winning Rule: Exact <b>{daily_target}.000s</b> par rokein aur <b>10x Winning Prize</b> jeetein!'
        f'</p></div>',
        unsafe_allow_html=True
    )

# --- ENTRY, RIGGING (0.9s PENALTY FOR OTHERS) & RESULT LOGIC ---
if "entry_submitted_day" not in st.session_state or st.session_state.entry_submitted_day != today_ist:
    st.session_state.entry_submitted = False
    st.session_state.entry_submitted_day = today_ist

if status == "STOPPED" and elapsed_val is not None:
    raw_stopped_time = float(elapsed_val)
    
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM entries WHERE day = ? AND ABS(elapsed - ?) <= ?", (today_ist, daily_target, WIN_TOLERANCE))
    winner_count = c.fetchone()[0]
    
    if winner_count > 0 or abs(raw_stopped_time - daily_target) <= 0.05:
        stopped_time = round(raw_stopped_time + 0.9, 3)
    else:
        stopped_time = round(raw_stopped_time, 3)

    difference = round(abs(stopped_time - daily_target), 3)
    is_winner = difference <= WIN_TOLERANCE and winner_count == 0
    
    if is_winner:
        st.markdown(
            f'<div class="glass-card" style="border-color: #25D366; background: #06210e; text-align:center;">'
            f'<h3 style="color:#4CAF50; margin-top:0;">🎉 BINGO! YOU WON 10x PRIZE!</h3>'
            f'<p style="font-size:1.1rem; color:#fff;">आपने बिल्कुल सटीक समय पर timer रोका!</p>'
            f'<p style="font-family:monospace; font-size:1rem; color:#ffd700;">'
            f'Stopped: {stopped_time:.3f}s | Target: {daily_target}.000s'
            f'</p></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="glass-card" style="border-color: #ff4444; text-align:center;">'
            f'<h3 style="color:#ff4444; margin-top:0;">❌ OOPS! YOU LOST!</h3>'
            f'<p style="font-size:1.05rem; color:#fff;">आप हार गए! आपने सही समय पर टाइमर नहीं रोका या आज का विजेता पहले ही चुना जा चुका है।</p>'
            f'<p style="font-family:monospace; font-size:0.95rem; color:#ccc;">'
            f'Your Time: {stopped_time:.3f}s | Target: {daily_target}.000s | Diff: {difference:.3f}s'
            f'</p></div>',
            unsafe_allow_html=True
        )
    
    if not st.session_state.entry_submitted:
        with st.form("submission_form"):
            st.write("अपना परिणाम रिकॉर्ड करने के लिए Instagram Username दर्ज करें:")
            insta_user = st.text_input("Instagram Username (with or without @)")
            submitted = st.form_submit_button("Submit Result")
            
            if submitted:
                clean_user = insta_user.strip().lower().lstrip('@')
                if not clean_user or not re.match(r'^[a-z0-9._]{1,30}$', clean_user):
                    st.error("Please enter a valid Instagram username.")
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
                        st.success("Result saved successfully!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.warning("आप आज पहले ही प्रयास कर चुके हैं!")
                        st.session_state.entry_submitted = True
                        st.session_state.current_user = clean_user

# --- WHATSAPP REDIRECT FOR WINNER ---
if status == "STOPPED" and elapsed_val is not None:
    c = conn.cursor()
    c.execute("SELECT instagram FROM entries WHERE day = ? ORDER BY ABS(elapsed - ?) ASC LIMIT 1", (today_ist, daily_target))
    top_entry = c.fetchone()
    
    if top_entry and st.session_state.get("current_user") == top_entry[0]:
        c.execute("SELECT ABS(elapsed - ?) FROM entries WHERE day = ? AND instagram = ?", (daily_target, today_ist, top_entry[0]))
        top_diff = c.fetchone()[0]
        
        if top_diff <= WIN_TOLERANCE and st.session_state.get("entry_submitted"):
            st.balloons()
            winner_user = top_entry[0]
            wa_msg = (
                f"Hi @oyye_rider Admin! 🎉 I won the 10x Timer Giveaway!\n\n"
                f"Instagram: @{winner_user}\n"
                f"Target: {daily_target}.000s\n"
                f"Date: {today_ist}\n\nPlease send my 10x winning payment via UPI/Bank!"
            )
            wa_url = f"https://wa.me/{admin_whatsapp_num}?text={urllib.parse.quote(wa_msg)}"
            
            st.markdown(
                f'<div class="glass-card" style="border: 2px solid #25D366; background: #06210e; text-align:center;">'
                f'<h3 style="color:#4CAF50; margin-top:0;">🚀 Claim Your 10x Payment Now!</h3>'
                f'<p>WhatsApp पर Admin से बात करें और अपना भुगतान प्राप्त करें:</p>'
                f'<a href="{wa_url}" target="_blank" style="display:inline-block; background:#25D366; color:white; padding:14px 28px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:1.1rem; margin-top:8px;">'
                f'💬 Connect with Admin on WhatsApp'
                f'</a></div>',
                unsafe_allow_html=True
            )

# --- LEADERBOARD ---
if status in ("UNLOCKED", "STOPPED", "REFRESH_LOCKED"):
    st.markdown("### 🏆 Today's Leaderboard")
    c = conn.cursor()
    c.execute("""
        SELECT instagram, elapsed, ROUND(ABS(elapsed - ?), 3) AS diff, created_at 
        FROM entries 
        WHERE day = ? 
        ORDER BY diff ASC, created_at ASC 
        LIMIT 50
    """, (daily_target, today_ist))
    leaderboard = c.fetchall()

    if leaderboard:
        rows_list = ['<div class="glass-card" style="padding:5px 0;">']
        for idx, (insta, elapsed_item, diff_val, created_at) in enumerate(leaderboard):
            rank = idx + 1
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
            diff_color = "#4CAF50" if diff_val <= WIN_TOLERANCE and rank == 1 else "#ff4444"
            status_text = "WINNER (10x)" if diff_val <= WIN_TOLERANCE and rank == 1 else f"Lost (Δ {diff_val:.3f}s)"
            row_str = (
                f'<div class="leaderboard-row">'
                f'<div style="width:15%; font-weight:bold;">{medal}</div>'
                f'<div style="width:35%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">@{insta}</div>'
                f'<div style="width:25%; text-align:right; color:#aaa;">{elapsed_item:.3f}s</div>'
                f'<div style="width:25%; text-align:right; color:{diff_color}; font-size:0.85rem;">{status_text}</div>'
                f'</div>'
            )
            rows_list.append(row_str)
        rows_list.append('</div>')
        st.markdown("".join(rows_list), unsafe_allow_html=True)
