# Mosaic Wellness Radar — Backend API

A lightweight Flask API that fetches live data from Google Trends, Reddit, and YouTube for the Mosaic Wellness Radar dashboard.

---

## Deploy to Render (free, ~10 minutes)

### Step 1 — Get a YouTube API Key (2 mins)
1. Go to https://console.cloud.google.com
2. Create a new project (call it "Mosaic Radar")
3. Go to **APIs & Services → Enable APIs** → search "YouTube Data API v3" → Enable
4. Go to **APIs & Services → Credentials → Create Credentials → API Key**
5. Copy the key — you'll need it in Step 3

### Step 2 — Push this folder to GitHub
1. Go to github.com → New repository → name it `mosaic-wellness-backend` → Create
2. Upload all files in this folder (app.py, requirements.txt, Procfile, README.md)

### Step 3 — Deploy on Render
1. Go to https://render.com → Sign up free with GitHub
2. Click **New → Web Service**
3. Connect your `mosaic-wellness-backend` GitHub repo
4. Set these values:
   - **Name:** mosaic-wellness-backend
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Click **Advanced → Add Environment Variable:**
   - Key: `YOUTUBE_API_KEY`
   - Value: (paste your key from Step 1)
6. Click **Create Web Service**

Render will build and deploy. In ~3 minutes you'll get a URL like:
`https://mosaic-wellness-backend.onrender.com`

### Step 4 — Test it
Open in browser:
`https://mosaic-wellness-backend.onrender.com/api/reddit/sea moss`

You should see live Reddit data as JSON.

### Step 5 — Update your dashboard
Replace `BACKEND_URL` in wellness-radar.html with your Render URL.

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/trends` | All keywords, all sources (slow ~30s) |
| `GET /api/trends/:keyword` | Single keyword, all sources |
| `GET /api/reddit/:keyword` | Reddit only |
| `GET /api/youtube/:keyword` | YouTube only |
| `GET /api/google/:keyword` | Google Trends only |

---

## Notes
- Google Trends has rate limits — the full `/api/trends` call takes ~30s due to 1s delays between requests
- Reddit requires no API key
- YouTube free tier allows 10,000 units/day (enough for hundreds of searches)
- Render free tier spins down after 15 mins of inactivity — first request after sleep takes ~30s to wake up
