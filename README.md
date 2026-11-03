# Daily Instagram Giveaway — ₹100

A mobile-first Flask giveaway app with a daily random target, server-measured stop time, one winner per day, winner list, winner-only UPI submission, and an admin panel.

## Important timing limitation
The backend measures from the server-side `/api/start` timestamp to the server's receipt of `/api/stop`. This is not a perfect measure of the user's physical button press: mobile network latency affects the result. The default acceptable window is ±180 ms (`TOLERANCE_MS`). A precision contest needs a clearly published rule and should not claim nanosecond accuracy. The database lock and winner check ensure no more than one winner is stored for each day, assuming a transactional persistent database.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY='use-a-long-random-secret'
export ADMIN_PASSWORD='choose-a-strong-password'
python app.py
```

Open `http://127.0.0.1:5000`. Admin: `/admin/login`. Default local values are for development only; set both environment variables before sharing the site.

## Deploy with a free public link

A static GitHub Pages site cannot run this backend. Deploy this Flask app to a Python web host such as Render and attach a persistent PostgreSQL database (for example a free-tier PostgreSQL provider if available to your account). Free-tier terms can change, and some free web services sleep when idle.

1. Upload this folder to a GitHub repository.
2. Create a web service from the repository on your hosting provider.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Set environment variables:
   - `SECRET_KEY`: long random secret
   - `ADMIN_PASSWORD`: strong unique password
   - `DATABASE_URL`: PostgreSQL connection URL from your database provider
   - `TOLERANCE_MS`: optional, default `180`
6. Use the generated HTTPS URL as your giveaway link.
7. Check `/health`, then test start, stop, winner lock, and UPI submission before publishing.

**Do not use SQLite on an ephemeral free host for a real giveaway.** Data may be lost on restart or redeploy. Use persistent PostgreSQL and test database transaction/locking behaviour on your selected host.

## Instagram comment-to-DM automation

The giveaway website does not silently connect to Instagram. To automate comment replies/DMs, you need an Instagram professional account, a Meta developer app, the supported Instagram Messaging API/comment webhook permissions, an access token, and a webhook endpoint configured in Meta. The permissions and eligibility are controlled by Meta and can change. Use a reputable approved automation provider or implement the official Meta API flow separately. Do not collect Instagram passwords or send unsolicited bulk DMs. Manually paste this website URL into an approved automation's reply message after setup.

Suggested public comment reply: “Thanks for joining! Tap the giveaway link in our DM. Free entry; one winner per day. Rules: [your rules URL]”.

## Before launching

- Publish rules: eligibility, contest dates/time zone, target/tolerance method, how ties are handled, winner verification, payout deadline, and contact details.
- Add a privacy notice and data-retention policy before collecting names/UPI IDs.
- Do not ask for UPI PIN, OTP, bank password, or payment to claim a prize.
- This starter uses first valid stop request within tolerance as winner. It does not guarantee a winner every day; if no one lands within the target window, there may be no winner that day.
- Admin target edits are blocked after a winner is selected, but admins can pause the game.
- For production use, add CSRF protection/rate limiting, anti-bot checks, audit logs, stronger admin authentication, and a privacy/terms page.
