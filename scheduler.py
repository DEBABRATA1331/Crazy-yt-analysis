from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime
import os
import joblib

from models import SessionLocal, Channel, Video, Comment, init_db
from youtube_service import fetch_channel_info, fetch_latest_videos, fetch_video_comments

# Load model and vectorizer
MODEL_PATH = "sentiment_model.pkl"
VECTORIZER_PATH = "vectorizer.pkl"
model = None
vectorizer = None

if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)

def analyze_sentiment(text: str):
    if not model or not vectorizer:
        return "Unknown", 0.0
    import re
    text = text.lower()
    text = re.sub(r"<br />", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    
    vec = vectorizer.transform([text])
    pred = model.predict(vec)[0]
    prob = model.predict_proba(vec)[0]
    
    label = "Positive" if pred == 1 else "Negative"
    confidence = float(prob[pred])
    return label, confidence

def update_channel_data(channel_id: str):
    print(f"[{datetime.utcnow()}] Starting update for channel: {channel_id}")
    db = SessionLocal()
    try:
        # Update Channel
        c_info = fetch_channel_info(channel_id)
        if not c_info:
            print(f"Failed to fetch channel info for {channel_id}")
            return
            
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            channel = Channel(id=channel_id)
            db.add(channel)
        
        channel.title = c_info["title"]
        channel.description = c_info["description"]
        channel.subscriber_count = c_info["subscriber_count"]
        channel.video_count = c_info["video_count"]
        channel.view_count = c_info["view_count"]
        channel.last_updated = datetime.utcnow()
        db.commit()
        
        # Fetch Videos
        v_info = fetch_latest_videos(channel_id, max_results=5) # 5 for demo to save API quota
        for v in v_info:
            video = db.query(Video).filter(Video.id == v["id"]).first()
            if not video:
                video = Video(id=v["id"], channel_id=channel_id)
                db.add(video)
            
            # published_at usually looks like 2024-05-10T12:00:00Z
            try:
                pub_date = datetime.strptime(v["published_at"], "%Y-%m-%dT%H:%M:%SZ")
            except:
                pub_date = datetime.utcnow()
                
            video.title = v["title"]
            video.published_at = pub_date
            video.view_count = v["view_count"]
            video.like_count = v["like_count"]
            video.comment_count = v["comment_count"]
            db.commit()
            
            # Fetch Comments for this video
            c_info_list = fetch_video_comments(v["id"], max_results=50) # 50 comments per video
            
            pos_count = 0
            neg_count = 0
            
            for comment_data in c_info_list:
                comment = db.query(Comment).filter(Comment.id == comment_data["id"]).first()
                if not comment:
                    comment = Comment(id=comment_data["id"], video_id=v["id"])
                    db.add(comment)
                
                comment.text = comment_data["text"]
                comment.author = comment_data["author"]
                
                try:
                    c_pub_date = datetime.strptime(comment_data["published_at"], "%Y-%m-%dT%H:%M:%SZ")
                except:
                    c_pub_date = datetime.utcnow()
                
                comment.published_at = c_pub_date
                comment.like_count = comment_data["like_count"]
                
                # Predict Sentiment
                label, conf = analyze_sentiment(comment.text)
                comment.sentiment_label = label
                comment.confidence = conf
                
                if label == "Positive":
                    pos_count += 1
                else:
                    neg_count += 1
                    
            db.commit()
            
            # Update video aggregates
            video.positive_comments = pos_count
            video.negative_comments = neg_count
            total = pos_count + neg_count
            if total > 0:
                video.sentiment_score = pos_count / total * 100.0
            video.last_updated = datetime.utcnow()
            db.commit()
            
        print(f"[{datetime.utcnow()}] Successfully updated channel: {channel_id}")
    except Exception as e:
        print(f"Error updating channel {channel_id}: {e}")
        db.rollback()
    finally:
        db.close()

def start_scheduler(channel_ids: list):
    init_db()
    scheduler = BackgroundScheduler()
    
    # Run immediately for the first time
    for cid in channel_ids:
        scheduler.add_job(
            update_channel_data, 
            args=[cid], 
            trigger='date' # Runs once immediately
        )
        
    # Then schedule every 4 hours
    for cid in channel_ids:
        scheduler.add_job(
            update_channel_data,
            args=[cid],
            trigger=IntervalTrigger(hours=4)
        )
        
    scheduler.start()
    return scheduler
