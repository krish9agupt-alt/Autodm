import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pytz
from datetime import datetime
import random
import urllib.parse
import re
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Oyye Rider | Daily Timer Challenge", page_icon="⏱️", layout="centered")

# --- CUSTOM CSS (Dark Gaming Theme) ---
st.markdown("""
<style>
    /* Dark Base & Hiding Elements */
    [data-testid="stAppViewContainer"] { background-color: #050505; color: #ffffff; }
    [data-testid="stHeader"] { background-color: transparent; }
    #MainMenu, footer, header { visibility: hidden; }
    
    /* Branding */
    .brand-title { text-align: center; color: #ffffff; font-weight: 900; font-size: 2rem; margin-bottom: 0px; }
    .gold-highlight { color: #d4af37; text-shadow: 0 0 10px rgba(212,175,55,0.4); }
    
    /* UI Cards */
    .glass-card {
        background: linear-gradient(145deg, #1a0000, #0a0000);
        border: 1px solid #d4af37;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.1);
    }
    
    .target-box {
        text-align: center;
        background: #000;
        border: 2px dashed #cc0000;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
    }
    .target-time { font-size: 2.5rem; font-family: monospace; color: #ff3333; font-weight: bold; }
    
    /* Buttons */
    .insta-btn {
        display: block; width: 100%; text-align: center; background: linear-gradient(45deg, #833ab4, #fd1d1d, #fcb045);
        color: white; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-bottom: 10px;
    }
    .insta-btn:hover { color: white; opacity: 0.9; }
    
    .stButton>button { width: 100%; background: linear-gradient(45deg, #cc0000, #880000); border: 1px solid #d4af37; color: white; font-weight: bold; border-radius: 8px; padding: 10px; }
    .stButton>button:hover { background: linear-gradient(45deg, #ff0000, #aa0000); border-color: #ffdf00; color: white;}

    /* Leaderboard */
    .leaderboard-row { display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #330000; font-family: monospace; font-size: 1.1rem; }
    .leaderboard-row:nth-child(odd) { background-color: rgba(255,0,0,0.05); }
    .rank-1 { color: #ffd700; font-weight: bold; font-size: 1.3rem; }
    .rank-2 { color: #c0c0c0; font-weight: bold; }
    .rank-3 { color: #cd7f32; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- INIT DATABASE & TIMEZONE ---
IST = pytz.timezone('Asia/Kolkata')
today_ist = datetime.now(IST).strftime('%Y-%m-%d')

def init_db():
    conn = sqlite3.connect('giveaway.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS targets (day TEXT PRIMARY KEY, target INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS entries 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT, instagram TEXT, 
                  elapsed REAL, diff REAL, created_at TEXT, UNIQUE(day, instagram))''')
    conn.commit()
    return conn

conn = init_db()

def get_daily_target(date_str):
    c = conn.cursor()
    c.execute("SELECT target FROM targets WHERE day = ?", (date_str,))
    row = c.fetchone()
    if row:
        return row[0]
    else:
        new_target = random.randint(10, 20) # Ensures 10-20 sec as per prompt spec
        c.execute("INSERT INTO targets (day, target) VALUES (?, ?)", (date_str, new_target))
        conn.commit()
        return new_target

daily_target = get_daily_target(today_ist)

# --- DECLARE COMPONENT ---
timer_component = components.declare_component("timer_component", path="timer_component")

# --- UI HEADER ---
st.markdown("<p class='brand-title'>@oyye_rider <span class='gold-highlight'>Giveaway</span></p>", unsafe_allow_html=True)
st.markdown("<a href='https://www.instagram.com/oyye_rider/' target='_blank' class='insta-btn'>📸 Follow on Instagram</a>", unsafe_allow_html=True)

st.markdown(f"""
<div class="glass-card">
    <h3 style='text-align:center; margin:0;'>Today's Target Time</h3>
    <div class="target-box">
        <span class="target-time">{daily_target:.3f} SEC</span>
    </div>
    <p style='text-align:center; color:#ccc; font-size: 0.9rem;'>Stop the timer exactly at the target. Smallest difference wins!</p>
</div>
""", unsafe_allow_html=True)

# --- RENDER TIMER ---
# Passed parameters dictate target and today's date for LocalStorage locking
timer_value = timer_component(target=daily_target, today=today_ist, key="daily_timer")

# --- ENTRY SUBMISSION LOGIC ---
if "entry_submitted" not in st.session_state:
    st.session_state.entry_submitted = False

if timer_value is not None:
    difference = abs(timer_value - daily_target)
    
    if not st.session_state.entry_submitted:
        st.markdown(f"""
        <div class="glass-card" style="border-color: #4CAF50;">
            <h3 style="text-align:center; color:#4CAF50;">Timer Stopped!</h3>
            <p style="text-align:center; font-family:monospace; font-size:1.2rem;">
            Your Time: <b>{timer_value:.3f}s</b><br>
            Difference: <b>{difference:.3f}s</b>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("submission_form"):
            st.write("Submit your Instagram username to claim your spot on the leaderboard.")
            insta_user = st.text_input("Instagram Username (with or without @)")
            submitted = st.form_submit_button("Submit Entry")
            
            if submitted:
                if not insta_user:
                    st.error("Please enter a valid Instagram username.")
                else:
                    # Normalize username
                    clean_user = insta_user.strip().lower()
                    if clean_user.startswith('@'):
                        clean_user = clean_user[1:]
                        
                    if not re.match(r'^[a-z0-9_\.]+$', clean_user):
                        st.error("Invalid Instagram username format.")
                    else:
                        timestamp = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                        c = conn.cursor()
                        try:
                            c.execute("INSERT INTO entries (day, instagram, elapsed, diff, created_at) VALUES (?, ?, ?, ?, ?)",
                                      (today_ist, clean_user, timer_value, difference, timestamp))
                            conn.commit()
                            st.session_state.entry_submitted = True
                            st.session_state.current_user = clean_user
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("This Instagram username has already been registered for today!")

# --- LEADERBOARD & WINNER LOGIC ---
st.markdown("### 🏆 Live Leaderboard")

c = conn.cursor()
c.execute("""
    SELECT instagram, elapsed, diff 
    FROM entries 
    WHERE day = ? 
    ORDER BY diff ASC, created_at ASC 
    LIMIT 50
""", (today_ist,))
leaderboard = c.fetchall()

if not leaderboard:
    st.info("No entries yet today. Be the first!")
else:
    # Check if the current session user is the provisional winner
    rank_1_user = leaderboard[0][0]
    is_provisional_winner = (
        st.session_state.get("entry_submitted") and 
        st.session_state.get("current_user") == rank_1_user
    )

    if is_provisional_winner:
        st.balloons()
        st.success("🎉 CONGRATULATIONS! You are currently ranked 1st!")
        
        admin_wa = st.secrets.get("ADMIN_WHATSAPP", "910000000000")
        wa_msg = f"Hi Admin! I am the provisional winner for the {today_ist} timer challenge.\n\nInsta: @{rank_1_user}\nTarget: {daily_target:.3f}s\nMy Time: {leaderboard[0][1]:.3f}s\nDifference: {leaderboard[0][2]:.3f}s"
        wa_url = f"https://wa.me/{admin_wa}?text={urllib.parse.quote(wa_msg)}"
        
        st.markdown(f"""
        <div class="glass-card" style="border-color: #ffd700; text-align:center;">
            <h3 style="color:#ffd700;">🥇 Provisional Winner!</h3>
            <p>If you maintain this rank until midnight, click below to claim your prize.</p>
            <a href="{wa_url}" target="_blank" style="display:inline-block; background:#25D366; color:white; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:bold;">📱 Claim via WhatsApp</a>
        </div>
        """, unsafe_allow_html=True)

    # Render Leaderboard entries
    st.markdown('<div class="glass-card" style="padding:0;">', unsafe_allow_html=True)
    for idx, row in enumerate(leaderboard):
        rank = idx + 1
        insta = row[0]
        time_diff = row[2]
        
        medal = ""
        rank_class = ""
        if rank == 1: 
            medal, rank_class = "🥇", "rank-1"
        elif rank == 2: 
            medal, rank_class = "🥈", "rank-2"
        elif rank == 3: 
            medal, rank_class = "🥉", "rank-3"
            
        st.markdown(f"""
        <div class="leaderboard-row">
            <div class="{rank_class}" style="width:15%;">{medal} #{rank}</div>
            <div style="width:45%;">@{insta}</div>
            <div style="width:40%; text-align:right; color:#ccc;">Δ {time_diff:.3f}s</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- DISCLAIMERS ---
with st.expander("Terms & Technical Notes"):
    st.caption("""
    - **One Attempt Limit:** Enforced securely via browser local storage. Clearing your cache or changing devices bypasses this client-side limit.
    - **Verification:** @oyye_rider reserves the right to disqualify entries suspected of manipulation. Instagram follow status is not automatically verified by API but is checked manually for winners.
    - **Server Note:** Hosted on Streamlit Community Cloud. If the container restarts, SQLite database memory might reset unless connected to a persistent PostgreSQL instance. For full production durability, migration to Postgres is recommended.
    - **Final Winners:** The final winner is determined at 11:59 PM IST. Provisional status during the day is subject to change.
    """)
