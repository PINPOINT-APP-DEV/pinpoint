# Pinpoint — $PINPOINT (v2)

Included:
- Like voter reward (+1) and author reward (+2)
- Dislike button + voter reward (+1)
- Hot/New tabs
- Hot ranking: time decay (half-life) + vote weights (MVP)
- Daily check-in (UTC): random 1~50 points, streak up to 30 days
- Brand centered under UTC row, bigger logo/text
- Token button nudged down

Run (PowerShell):
```powershell
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
$env:PORT=5050
python app.py
```
Open:
http://127.0.0.1:5050/?lang=en&tab=hot
