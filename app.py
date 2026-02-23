from flask import Flask, jsonify
from flask_cors import CORS
import os, requests, time
from pytrends.request import TrendReq

app = Flask(__name__)
CORS(app)  # Allow dashboard to call this from any domain

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Wellness keywords to track
KEYWORDS = [
    "sea moss", "rosemary hair oil", "psychobiotics", "berberine",
    "castor oil packs", "somatic wellness", "fadogia agrestis",
    "tallow skincare", "ashwagandha KSM-66"
]

# ─── GOOGLE TRENDS ────────────────────────────────────────────
def fetch_google_trends(keyword):
    try:
        pt = TrendReq(hl='en-IN', tz=-330, timeout=(10, 25))
        pt.build_payload([keyword], cat=0, timeframe='today 6-m', geo='IN')
        df = pt.interest_over_time()
        if df.empty:
            return {"keyword": keyword, "values": [], "avg": 0, "peak": 0}
        vals = df[keyword].tolist()
        return {
            "keyword": keyword,
            "values": vals[-12:],          # last 12 weeks
            "avg": round(sum(vals) / len(vals), 1),
            "peak": max(vals),
            "current": vals[-1]
        }
    except Exception as e:
        return {"keyword": keyword, "error": str(e), "values": [], "avg": 0, "peak": 0}

# ─── REDDIT ───────────────────────────────────────────────────
def fetch_reddit(keyword):
    try:
        headers = {"User-Agent": "MosaicWellnessRadar/1.0"}
        # Search across all of reddit
        url = f"https://www.reddit.com/search.json?q={requests.utils.quote(keyword)}&sort=new&limit=25&t=month"
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        posts = data["data"]["children"]
        scores = [p["data"]["score"] for p in posts]
        total = len(posts)
        avg_score = round(sum(scores) / total, 1) if total else 0
        top_posts = sorted(posts, key=lambda p: p["data"]["score"], reverse=True)[:3]
        return {
            "keyword": keyword,
            "post_count": total,
            "avg_score": avg_score,
            "top_posts": [
                {
                    "title": p["data"]["title"],
                    "score": p["data"]["score"],
                    "subreddit": p["data"]["subreddit"],
                    "url": f"https://reddit.com{p['data']['permalink']}"
                }
                for p in top_posts
            ]
        }
    except Exception as e:
        return {"keyword": keyword, "error": str(e), "post_count": 0}

# ─── YOUTUBE ──────────────────────────────────────────────────
def fetch_youtube(keyword):
    if not YOUTUBE_API_KEY:
        return {"keyword": keyword, "error": "No API key set", "video_count": 0}
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": keyword + " India wellness",
            "type": "video",
            "order": "date",
            "publishedAfter": "2024-10-01T00:00:00Z",
            "maxResults": 10,
            "key": YOUTUBE_API_KEY
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        items = data.get("items", [])
        return {
            "keyword": keyword,
            "video_count": data.get("pageInfo", {}).get("totalResults", len(items)),
            "recent_videos": [
                {
                    "title": v["snippet"]["title"],
                    "channel": v["snippet"]["channelTitle"],
                    "published": v["snippet"]["publishedAt"][:10],
                    "url": f"https://youtube.com/watch?v={v['id']['videoId']}"
                }
                for v in items[:3]
            ]
        }
    except Exception as e:
        return {"keyword": keyword, "error": str(e), "video_count": 0}

# ─── ROUTES ───────────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({"status": "Mosaic Wellness Radar API", "version": "1.0"})

@app.route("/api/trends")
def all_trends():
    """Fetch all signals for all keywords in one call."""
    results = []
    for kw in KEYWORDS:
        gtrend = fetch_google_trends(kw)
        time.sleep(1)  # be polite to Google Trends
        reddit  = fetch_reddit(kw)
        youtube = fetch_youtube(kw)
        results.append({
            "keyword": kw,
            "google_trends": gtrend,
            "reddit": reddit,
            "youtube": youtube,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M UTC")
        })
    return jsonify({"status": "ok", "data": results, "count": len(results)})

@app.route("/api/trends/<keyword>")
def single_trend(keyword):
    """Fetch signals for a single keyword."""
    gtrend  = fetch_google_trends(keyword)
    reddit  = fetch_reddit(keyword)
    youtube = fetch_youtube(keyword)
    return jsonify({
        "keyword": keyword,
        "google_trends": gtrend,
        "reddit": reddit,
        "youtube": youtube,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M UTC")
    })

@app.route("/api/reddit/<keyword>")
def reddit_only(keyword):
    return jsonify(fetch_reddit(keyword))

@app.route("/api/youtube/<keyword>")
def youtube_only(keyword):
    return jsonify(fetch_youtube(keyword))

@app.route("/api/google/<keyword>")
def google_only(keyword):
    return jsonify(fetch_google_trends(keyword))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
