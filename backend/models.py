from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(String, primary_key=True)
    title = Column(String)
    description = Column(String)
    subscriber_count = Column(Integer)
    video_count = Column(Integer)
    view_count = Column(Integer)
    last_updated = Column(DateTime, default=datetime.utcnow)

    videos = relationship("Video", back_populates="channel")

class Video(Base):
    __tablename__ = 'videos'
    id = Column(String, primary_key=True)
    channel_id = Column(String, ForeignKey('channels.id'))
    title = Column(String)
    published_at = Column(DateTime)
    view_count = Column(Integer)
    like_count = Column(Integer)
    comment_count = Column(Integer)
    
    # Sentiment aggregations
    positive_comments = Column(Integer, default=0)
    negative_comments = Column(Integer, default=0)
    sentiment_score = Column(Float, default=0.0) # percentage of positive
    last_updated = Column(DateTime, default=datetime.utcnow)

    channel = relationship("Channel", back_populates="videos")
    comments = relationship("Comment", back_populates="video")

class Comment(Base):
    __tablename__ = 'comments'
    id = Column(String, primary_key=True)
    video_id = Column(String, ForeignKey('videos.id'))
    text = Column(String)
    author = Column(String)
    published_at = Column(DateTime)
    like_count = Column(Integer)
    
    # ML predictions
    sentiment_label = Column(String)
    confidence = Column(Float)

    video = relationship("Video", back_populates="comments")

# Setup Database Connection
DATABASE_URL = "sqlite:///./youtube_data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
