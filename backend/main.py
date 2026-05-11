from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import re
from dotenv import load_dotenv

from models import SessionLocal, Channel, Video, Comment, init_db
from scheduler import start_scheduler, analyze_sentiment
from youtube_service import (
    get_youtube_service,
    fetch_video_comments,
    fetch_channel_info,
)

load_dotenv()

app = FastAPI(title="YouTube Sentiment Analyzer API")

# CORS — origins from env so you can update without code change
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://crazy-yt-analysis.vercel.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_origin_regex=r"https://crazy-yt-analysis.*\.vercel\.app",  # allow preview deploys
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    init_db()
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        channels_to_monitor = ["UC8butISFwT-Wl7EV0hUK0BQ"]
        app.state.scheduler = start_scheduler(channels_to_monitor)
        print("Scheduler started.")
    else:
        print("Scheduler disabled.")

@app.on_event("shutdown")
def shutdown_event():
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()

# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------

class CommentRequest(BaseModel):
    text: str

class SentimentResponse(BaseModel):
    text: str
    sentiment: str
    confidence: float

class VideoAnalysisRequest(BaseModel):
    url: str

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    # bare 11-char ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url.strip()):
        return url.strip()
    return None

def fetch_video_details(video_id: str):
    """Get full video metadata: title, channel, thumbnail, stats."""
    youtube = get_youtube_service()
    if not youtube:
        return None
    try:
        request = youtube.videos().list(
            part="snippet,statistics",
            id=video_id,
        )
        response = request.execute()
        items = response.get("items", [])
        if not items:
            return None
        item = items[0]
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        thumbnails = snippet.get("thumbnails", {})
        thumb = (
            thumbnails.get("maxres")
            or thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
            or {}
        )
        return {
            "id": video_id,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:500],
            "channel_title": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": thumb.get("url", ""),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
            "tags": snippet.get("tags", [])[:10],
        }
    except Exception as e:
        print(f"Error fetching video details: {e}")
        return None

# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": "Welcome to the YouTube Sentiment Analyzer API", "status": "online"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/predict", response_model=SentimentResponse)
def predict_sentiment(req: CommentRequest):
    label, confidence = analyze_sentiment(req.text)
    if label == "Unknown":
        raise HTTPException(status_code=500, detail="Model is not loaded.")
    return SentimentResponse(text=req.text, sentiment=label, confidence=confidence)

@app.post("/analyze")
def analyze_video(req: VideoAnalysisRequest):
    """Full video analysis: metadata + stats + sentiment of top comments."""
    video_id = extract_video_id(req.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL. Please provide a valid YouTube video link.")

    # 1) Video details
    details = fetch_video_details(video_id)
    if not details:
        raise HTTPException(
            status_code=404,
            detail="Video not found. Check the URL or YouTube API key.",
        )

    # 2) Comments
    comments_raw = fetch_video_comments(video_id, max_results=100)

    analyzed_comments = []
    pos_count = 0
    neg_count = 0
    confidence_buckets = {"0-50": 0, "50-70": 0, "70-85": 0, "85-95": 0, "95-100": 0}

    for c in comments_raw:
        label, conf = analyze_sentiment(c["text"])
        analyzed_comments.append({
            "id": c["id"],
            "author": c["author"],
            "text": c["text"],
            "sentiment": label,
            "confidence": conf,
            "like_count": c["like_count"],
            "published_at": c["published_at"],
        })
        if label == "Positive":
            pos_count += 1
        else:
            neg_count += 1

        pct = conf * 100
        if pct < 50:
            confidence_buckets["0-50"] += 1
        elif pct < 70:
            confidence_buckets["50-70"] += 1
        elif pct < 85:
            confidence_buckets["70-85"] += 1
        elif pct < 95:
            confidence_buckets["85-95"] += 1
        else:
            confidence_buckets["95-100"] += 1

    total = pos_count + neg_count
    sentiment_score = (pos_count / total * 100) if total > 0 else 0
    engagement_rate = (
        details["like_count"] / details["view_count"] * 100
        if details["view_count"] > 0 else 0
    )

    return {
        "video": details,
        "analytics": {
            "total_analyzed": total,
            "positive_count": pos_count,
            "negative_count": neg_count,
            "sentiment_score": round(sentiment_score, 1),
            "engagement_rate": round(engagement_rate, 2),
            "confidence_distribution": confidence_buckets,
        },
        "comments": analyzed_comments,
    }

@app.get("/channels")
def get_channels(db: Session = Depends(get_db)):
    return db.query(Channel).all()

@app.get("/channels/{channel_id}/videos")
def get_videos(channel_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Video)
        .filter(Video.channel_id == channel_id)
        .order_by(Video.published_at.desc())
        .all()
    )

@app.get("/videos/{video_id}/comments")
def get_comments(video_id: str, db: Session = Depends(get_db)):
    return db.query(Comment).filter(Comment.video_id == video_id).all()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)