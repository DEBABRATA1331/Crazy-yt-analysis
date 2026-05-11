from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

from models import SessionLocal, Channel, Video, Comment, init_db
from scheduler import start_scheduler, analyze_sentiment

load_dotenv()

app = FastAPI(title="YouTube Sentiment Analyzer API")

# Setup CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Start scheduler on startup
@app.on_event("startup")
def startup_event():
    init_db()
    
    # We can monitor some popular tech channels by default or let the user add them
    channels_to_monitor = [
        "UC8butISFwT-Wl7EV0hUK0BQ", # freeCodeCamp
        # You can add more channel IDs here
    ]
    app.state.scheduler = start_scheduler(channels_to_monitor)

@app.on_event("shutdown")
def shutdown_event():
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()

class CommentRequest(BaseModel):
    text: str

class SentimentResponse(BaseModel):
    text: str
    sentiment: str
    confidence: float

@app.get("/")
def read_root():
    return {"message": "Welcome to the YouTube Sentiment Analyzer API"}

@app.post("/predict", response_model=SentimentResponse)
def predict_sentiment(req: CommentRequest):
    label, confidence = analyze_sentiment(req.text)
    if label == "Unknown":
        raise HTTPException(status_code=500, detail="Model is not loaded.")
    
    return SentimentResponse(
        text=req.text,
        sentiment=label,
        confidence=confidence
    )

@app.get("/channels")
def get_channels(db: Session = Depends(get_db)):
    return db.query(Channel).all()

@app.get("/channels/{channel_id}/videos")
def get_videos(channel_id: str, db: Session = Depends(get_db)):
    videos = db.query(Video).filter(Video.channel_id == channel_id).order_by(Video.published_at.desc()).all()
    return videos

@app.get("/videos/{video_id}/comments")
def get_comments(video_id: str, db: Session = Depends(get_db)):
    return db.query(Comment).filter(Comment.video_id == video_id).all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
