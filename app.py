from flask import Flask, jsonify
from flask_cors import CORS
import os, requests, time
from pytrends.request import TrendReq

app = Flask(__name__)
CORS(app)

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

TRENDS = [
    {"id": 1, "name": "Sea Moss",           "keyword": "sea moss",          "category": "supplements"},
    {"id": 2, "name": "Rosemary Hair Oil",  "keyword": "rosemary hair oil", "category": "haircare"},
    {"id": 3, "name": "Psychobiotics",      "keyword": "psychobiotics",     "category": "gut"},
    {"id": 4, "name": "Berberine",          "keyword": "berberine",         "category": "supplements"},
    {"id": 5, "name": "Castor Oil Packs",   "keyword": "castor oil packs",  "category": "gut"},
    {"id": 6, "name": "Somatic Wellness",   "keyword": "somatic wellness",  "category": "mental"},
    {"id": 7, "name": "Fadogia Agrestis",   "keyword": "fadogia agrestis",  "category": "supplements"},
    {"id": 8, "name": "Tallow Skincare",    "keyword": "tallow skincare",   "category": "skincare"},
    {"id": 9, "name": "Ashwagandha KSM-66", "keyword": "ashwagandha ksm66", "category": "supplements"},
]

def fetch_google_trends(keyword):
    try:
        pt = TrendReq(hl='en-IN', tz=-330, timeout=(10, 25), retries=2, backoff_factor=0.5)
        pt.build_payload([keyword], cat=0, timeframe='today 6-m', geo='IN')
        df = pt.interest_over_time()
        if df.empty:
            return {"avg": 0, "current": 0, "peak": 0, "values": [], "growth_pct": 0}
        vals = df[keyword].tolist()
        if len(vals) >= 8:
            early  = sum(vals[:4]) / 4
            recent = sum(vals[-4:]) / 4
            growth = round(((recent - early) / early * 100), 1) if early > 0 else 0
        else:
            growth = 0
        return {
            "avg": round(sum(vals) / len(vals), 1),
            "current": vals[-1],
            "peak": max(vals),
            "values": vals[-12:],
            "growth_pct": growth
        }
    except Exception as e:
        return {"avg": 0, "current": 0, "peak": 0, "values": [], "growth_pct": 0, "error": str(e)}

def fetch_reddit(keyword):
    try:
        headers = {"User-Agent": "MosaicWellnessRadar/2.0 (research tool)"}
        url = f"https://www.reddit.com/search.json?q={requests.utils.quote(keyword)}&sort=top&limit=25&t=month"
        r = requests.get(url, headers=headers, timeout=12)
        data = r.json()
        posts = [p["data"] for p in data["data"]["children"]]
        if not posts:
            return {"post_count": 0, "avg_score": 0, "top_posts": [], "subreddits": []}
        scores = [p.get("score", 0) for p in posts]
        top3   = sorted(posts, key=lambda p: p.get("score", 0), reverse=True)[:3]
        subs   = list({p.get("subreddit", "") for p in posts})[:5]
        return {
            "post_count": len(posts),
            "avg_score":  round(sum(scores) / len(scores), 1),
            "top_score":  max(scores),
            "subreddits": subs,
            "top_posts": [
                {
                    "title":     p.get("title", ""),
                    "score":     p.get("score", 0),
                    "comments":  p.get("num_comments", 0),
                    "subreddit": p.get("subreddit", ""),
                    "url":       f"https://reddit.com{p.get('permalink', '')}"
                }
                for p in top3
            ]
        }
    except Exception as e:
        return {"post_count": 0, "avg_score": 0, "top_posts": [], "subreddits": [], "error": str(e)}

def fetch_youtube(keyword):
    if not YOUTUBE_API_KEY:
        return {"video_count": 0, "recent_videos": [], "error": "No API key"}
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet", "q": keyword + " wellness",
                "type": "video", "order": "date",
                "publishedAfter": "2024-10-01T00:00:00Z",
                "maxResults": 10, "key": YOUTUBE_API_KEY
            },
            timeout=12
        )
        data = r.json()
        if "error" in data:
            return {"video_count": 0, "recent_videos": [], "error": data["error"]["message"]}
        items = data.get("items", [])
        return {
            "video_count": data.get("pageInfo", {}).get("totalResults", len(items)),
            "recent_videos": [
                {
                    "title":     v["snippet"]["title"],
                    "channel":   v["snippet"]["channelTitle"],
                    "published": v["snippet"]["publishedAt"][:10],
                    "url":       f"https://youtube.com/watch?v={v['id']['videoId']}"
                }
                for v in items[:3]
            ]
        }
    except Exception as e:
        return {"video_count": 0, "recent_videos": [], "error": str(e)}

def compute_scores(gt, reddit, youtube):
    growth = gt.get("growth_pct", 0)
    if   growth >= 300: v = 95
    elif growth >= 200: v = 85
    elif growth >= 100: v = 72
    elif growth >= 50:  v = 58
    elif growth >= 0:   v = 40
    else:               v = 25

    rc = reddit.get("post_count", 0)
    if   rc >= 25: r = 90
    elif rc >= 15: r = 75
    elif rc >= 8:  r = 58
    elif rc >= 3:  r = 40
    else:          r = 20

    yc = youtube.get("video_count", 0)
    if   yc >= 1000: y = 90
    elif yc >= 500:  y = 78
    elif yc >= 100:  y = 62
    elif yc >= 20:   y = 45
    else:            y = 25

    overall = round(v * 0.4 + r * 0.35 + y * 0.25)
    vel     = "hot" if overall >= 85 else ("rising" if overall >= 68 else "emerging")
    conf    = min(100, round((min(100, v + 5) + min(100, round((r + y) / 2)) + min(100, round(gt.get("current", 0) * 0.9 + 10))) / 3))

    return {
        "velocity": v, "social": r, "reach": y, "overall": overall,
        "vel_label": vel, "confidence": conf,
        "verdict": "TREND" if conf >= 70 else ("WATCH" if conf >= 50 else "FAD"),
        "fad": {
            "persistence":   min(100, v + 5),
            "crossPlatform": min(100, round((r + y) / 2)),
            "science":       60,
            "westernLag":    min(100, round(gt.get("current", 0) * 0.9 + 10))
        }
    }

def build_trend_result(t, gt, reddit, youtube, scores):
    g = gt.get("growth_pct", 0)
    return {
        "id":       t["id"],
        "name":     t["name"],
        "category": t["category"],
        "velocity": scores["vel_label"],
        "overall":  scores["overall"],
        "scores":   {"v": scores["velocity"], "g": 85, "c": 80, "t": scores["reach"]},
        "fad":      scores["fad"],
        "conf":     scores["confidence"],
        "verdict":  scores["verdict"],
        "metrics": {
            "search_growth":  f"+{g}%" if g >= 0 else f"{g}%",
            "google_current": gt.get("current", 0),
            "google_peak":    gt.get("peak", 0),
            "reddit_posts":   reddit.get("post_count", 0),
            "reddit_avg":     reddit.get("avg_score", 0),
            "youtube_videos": youtube.get("video_count", 0),
        },
        "reddit_top_posts":    reddit.get("top_posts", []),
        "reddit_subreddits":   reddit.get("subreddits", []),
        "youtube_recent":      youtube.get("recent_videos", []),
        "google_trend_values": gt.get("values", []),
        "fetched_at":          time.strftime("%Y-%m-%d %H:%M UTC")
    }

@app.route("/")
def index():
    return jsonify({"status": "Mosaic Wellness Radar API v2", "trends": len(TRENDS)})

@app.route("/api/trends")
def all_trends():
    results = []
    for t in TRENDS:
        gt      = fetch_google_trends(t["keyword"])
        time.sleep(1.2)
        reddit  = fetch_reddit(t["keyword"])
        youtube = fetch_youtube(t["keyword"])
        scores  = compute_scores(gt, reddit, youtube)
        results.append(build_trend_result(t, gt, reddit, youtube, scores))
    return jsonify({"status": "ok", "count": len(results), "data": results})

@app.route("/api/trend/<int:trend_id>")
def single_trend(trend_id):
    t = next((x for x in TRENDS if x["id"] == trend_id), None)
    if not t:
        return jsonify({"error": "Not found"}), 404
    gt      = fetch_google_trends(t["keyword"])
    reddit  = fetch_reddit(t["keyword"])
    youtube = fetch_youtube(t["keyword"])
    scores  = compute_scores(gt, reddit, youtube)
    return jsonify(build_trend_result(t, gt, reddit, youtube, scores))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
