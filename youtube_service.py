from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_youtube_service():
    if not YOUTUBE_API_KEY:
        print("WARNING: YOUTUBE_API_KEY not found in environment.")
        return None
    return build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def fetch_channel_info(channel_id: str):
    youtube = get_youtube_service()
    if not youtube: return None
    
    request = youtube.channels().list(
        part="snippet,statistics",
        id=channel_id
    )
    response = request.execute()
    
    if "items" not in response or not response["items"]:
        return None
        
    item = response["items"][0]
    return {
        "id": item["id"],
        "title": item["snippet"]["title"],
        "description": item["snippet"]["description"],
        "subscriber_count": int(item["statistics"].get("subscriberCount", 0)),
        "video_count": int(item["statistics"].get("videoCount", 0)),
        "view_count": int(item["statistics"].get("viewCount", 0))
    }

def fetch_latest_videos(channel_id: str, max_results: int = 10):
    youtube = get_youtube_service()
    if not youtube: return []
    
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        order="date",
        type="video",
        maxResults=max_results
    )
    response = request.execute()
    
    videos = []
    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        # Fetch stats for each video
        stats_request = youtube.videos().list(part="statistics", id=video_id)
        stats_response = stats_request.execute()
        stats = stats_response["items"][0]["statistics"] if stats_response.get("items") else {}
        
        videos.append({
            "id": video_id,
            "title": item["snippet"]["title"],
            "published_at": item["snippet"]["publishedAt"],
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0))
        })
    return videos

def fetch_video_comments(video_id: str, max_results: int = 100):
    youtube = get_youtube_service()
    if not youtube: return []
    
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            order="relevance"
        )
        response = request.execute()
        
        comments = []
        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "id": item["id"],
                "text": snippet["textDisplay"],
                "author": snippet["authorDisplayName"],
                "published_at": snippet["publishedAt"],
                "like_count": int(snippet.get("likeCount", 0))
            })
        return comments
    except Exception as e:
        print(f"Error fetching comments for video {video_id}: {e}")
        return []
