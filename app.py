import os, secrets, hashlib, hmac, json
from datetime import datetime, date, timezone
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-change-me')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///giveaway.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'change-this-admin-password')
PRIZE_INR = 100
# Challenge timing is measured on the server when the stop request arrives. Network latency
# affects results, so this is a demo-friendly game and not a precision scientific timer.
TOLERANCE_MS = int(os.environ.get('TOLERANCE_MS', '180'))

class Day(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_key = db.Column(db.String(10), unique=True, nullable=False)
    target_ms = db.Column(db.Integer, nullable=False)
    prize = db.Column(db.Integer, nullable=False, default=PRIZE_INR)
    winner_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_name = db.Column(db.String(50), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    day_key = db.Column(db.String(10), nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    stopped_at = db.Column(db.DateTime, nullable=True)
    elapsed_ms = db.Column(db.Integer, nullable=True)
    difference_ms = db.Column(db.Integer, nullable=True)
    is_winner = db.Column(db.Boolean, default=False, nullable=False)
    upi_id = db.Column(db.String(100), nullable=True)
    upi_submitted_at = db.Column(db.DateTime, nullable=True)

with app.app_context():
    db.create_all()

def today_key():
    # Giveaway day follows India Standard Time (UTC+05:30).
    from datetime import timedelta
    return (datetime.utcnow() + timedelta(hours=5, minutes=30)).date().isoformat()

def get_day(create=True):
    key = today_key()
    day = Day.query.filter_by(day_key=key).first()
    if not day and create:
        # Random daily target from 3.000s to 10.000s, in 10ms increments.
        import random
        target = random.randrange(300, 1001) * 10
        day = Day(day_key=key, target_ms=target, prize=PRIZE_INR, active=True)
        db.session.add(day)
        db.session.commit()
    return day

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def admin_required():
    return session.get('is_admin') is True

@app.get('/')
def index():
    day = get_day()
    return render_template('index.html', day=day, prize=PRIZE_INR)

@app.get('/api/status')
def status():
    day = get_day()
    winner = Player.query.get(day.winner_id) if day.winner_id else None
    return jsonify({
        'day': day.day_key, 'prize': day.prize, 'target_ms': day.target_ms,
        'target_seconds': f'{day.target_ms/1000:.2f}', 'active': day.active,
        'has_winner': bool(winner),
        'winner_name': winner.public_name if winner else None,
        'winner_upi_submitted': bool(winner and winner.upi_id)
    })

@app.post('/api/start')
def start_game():
    day = get_day()
    if not day.active:
        return jsonify(error='आज का गेम बंद है।'), 403
    if day.winner_id:
        return jsonify(error='आज का विजेता चुना जा चुका है। कल फिर कोशिश करें।'), 409
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or 'Instagram Player').strip()[:50]
    if not name:
        name = 'Instagram Player'
    # A one-play-per-day cookie helps UX; the database token is the actual game session.
    token = secrets.token_urlsafe(32)
    player = Player(public_name=name, token_hash=token_hash(token), day_key=day.day_key, started_at=datetime.utcnow())
    db.session.add(player)
    db.session.commit()
    return jsonify(token=token, started_at=player.started_at.isoformat() + 'Z', target_seconds=f'{day.target_ms/1000:.2f}')

@app.post('/api/stop')
def stop_game():
    data = request.get_json(silent=True) or {}
    token = data.get('token', '')
    if not token:
        return jsonify(error='गेम सेशन नहीं मिला। दोबारा शुरू करें।'), 400
    player = Player.query.filter_by(token_hash=token_hash(token)).with_for_update().first()
    if not player or player.day_key != today_key():
        return jsonify(error='गेम सेशन अमान्य या समाप्त हो गया।'), 400
    if player.stopped_at:
        return jsonify(error='इस गेम में टाइमर पहले ही रोका जा चुका है।'), 409
    day = Day.query.filter_by(day_key=player.day_key).with_for_update().first()
    if not day or not day.active:
        return jsonify(error='गेम अभी उपलब्ध नहीं है।'), 403
    now = datetime.utcnow()
    elapsed = max(0, int((now - player.started_at).total_seconds() * 1000))
    diff = abs(elapsed - day.target_ms)
    player.stopped_at = now
    player.elapsed_ms = elapsed
    player.difference_ms = diff
    # First valid stop request within tolerance wins; atomic DB update prevents duplicate winner.
    if diff <= TOLERANCE_MS and not day.winner_id:
        day.winner_id = player.id
        player.is_winner = True
        db.session.commit()
        return jsonify(result='winner', elapsed_ms=elapsed, difference_ms=diff,
                       message='बधाई! आप आज के विजेता हैं। UPI ID जमा करें।')
    db.session.commit()
    if day.winner_id:
        return jsonify(result='closed', elapsed_ms=elapsed, difference_ms=diff,
                       message='आज का विजेता चुना जा चुका है। कल फिर कोशिश करें।')
    return jsonify(result='try_again', elapsed_ms=elapsed, difference_ms=diff,
                   message=f'इस बार लक्ष्य से {diff} ms का अंतर रहा। आज विजेता अभी तय नहीं हुआ है।')

@app.post('/api/upi')
def submit_upi():
    data = request.get_json(silent=True) or {}
    token = data.get('token', '')
    upi = (data.get('upi_id') or '').strip()
    # Basic UPI ID format validation; never request a UPI PIN or OTP.
    import re
    if not re.fullmatch(r'[A-Za-z0-9._-]{2,256}@[A-Za-z]{2,64}', upi):
        return jsonify(error='सही UPI ID डालें, जैसे name@bank.'), 400
    player = Player.query.filter_by(token_hash=token_hash(token)).first()
    day = get_day()
    if not player or not player.is_winner or day.winner_id != player.id:
        return jsonify(error='UPI फॉर्म केवल आज के सत्यापित विजेता के लिए है।'), 403
    player.upi_id = upi
    player.upi_submitted_at = datetime.utcnow()
    db.session.commit()
    return jsonify(message='UPI ID जमा हो गई। इनाम का भुगतान एडमिन सत्यापित करेगा।')

@app.get('/winners')
def winners():
    rows = Day.query.filter(Day.winner_id.isnot(None)).order_by(Day.day_key.desc()).limit(90).all()
    result = []
    for d in rows:
        p = Player.query.get(d.winner_id)
        if p:
            result.append({'day': d.day_key, 'name': p.public_name, 'prize': d.prize})
    return render_template('winners.html', winners=result)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if hmac.compare_digest(password, ADMIN_PASSWORD):
            session['is_admin'] = True
            return redirect(url_for('admin'))
        flash('गलत पासवर्ड।')
    return render_template('admin_login.html')

@app.get('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

@app.get('/admin')
def admin():
    if not admin_required():
        return redirect(url_for('admin_login'))
    day = get_day()
    winner = Player.query.get(day.winner_id) if day.winner_id else None
    players = Player.query.filter_by(day_key=day.day_key).order_by(Player.id.desc()).limit(100).all()
    return render_template('admin.html', day=day, winner=winner, players=players)

@app.post('/admin/target')
def admin_target():
    if not admin_required(): return redirect(url_for('admin_login'))
    day = get_day()
    try:
        seconds = float(request.form.get('target_seconds', ''))
        target_ms = int(round(seconds * 1000))
        if not 1 <= target_ms <= 30000: raise ValueError()
    except ValueError:
        flash('टारगेट 1 से 30 सेकंड के बीच होना चाहिए।')
        return redirect(url_for('admin'))
    if day.winner_id:
        flash('विजेता चुने जाने के बाद आज का टारगेट नहीं बदला जा सकता।')
    else:
        day.target_ms = target_ms
        db.session.commit()
        flash('आज का टारगेट अपडेट हो गया।')
    return redirect(url_for('admin'))

@app.post('/admin/toggle')
def admin_toggle():
    if not admin_required(): return redirect(url_for('admin_login'))
    day = get_day()
    day.active = not day.active
    db.session.commit()
    flash('गेम स्टेटस अपडेट हो गया।')
    return redirect(url_for('admin'))

@app.get('/health')
def health():
    return jsonify(ok=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
