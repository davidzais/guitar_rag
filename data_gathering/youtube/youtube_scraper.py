import re
import http.cookiejar
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube.youtube_video_id_generator import get_all_video_urls_and_titles, get_all_video_urls_and_titles_from_search
from youtube.data_models import Transcript, Segment
from pathlib import Path
from db import video_id_exists
import time



def clean_video_id(url_or_id):
    """Extract video ID from YouTube URL"""
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url_or_id)
        # print(match.group(1) if match else url_or_id)
        return match.group(1) if match else url_or_id

    return url_or_id

def create_session_cookie():
    session = requests.Session()
    # Load cookies from exported cookies.txt     
    session.cookies = http.cookiejar.MozillaCookieJar("cookies.txt")
    session.cookies.load()

    return session

def download_transcript(video_id, title, presenter, languages=["en"]):
    """Download transcript using the correct API"""
    video_id = clean_video_id(video_id)

    try:
        # Create API instance
        #
        # api = YouTubeTranscriptApi(http_client=create_session_cookie())
        api = YouTubeTranscriptApi()

        # Fetch transcript
        tscript = api.fetch(video_id, languages=languages)

        # Get snippets
        snippets = tscript.snippets

        """ 
        transcript.to_raw_data() returns a list of dictionaries, so no need to loop the snippets
        
        [
            {
                'text': 'Hey there',
                'start': 0.0,
                'duration': 1.54
            },
            {
                'text': 'how are you',
                'start': 1.54
                'duration': 4.16
            },
            # ...
        ]
        """
        segments_data = tscript.to_raw_data()
        flat_segments = [s for sublist in segments_data for s in sublist]
        full_text = " ".join(s.text for s in snippets)
        transcript = Transcript(
            video_id = video_id, 
            title = title,
            text = full_text,   # cleaned chunk text
            instructor = presenter,    # e.g. "jack_ruch"        
            url = f"https://www.youtube.com/watch?v={video_id}",
            language = tscript.language_code,
            is_generated = tscript.is_generated,
            char_count = len(full_text),
            segments = [Segment(**s) for s in segments_data]
        )

        
        return transcript
        # return {
        #     "video_id": video_id,
        #     "title": title,
        #     "url": f"https://www.youtube.com/watch?v={video_id}",
        #     "language": tscript.language_code,
        #     "is_generated": tscript.is_generated,
        #     "text": full_text,
        #     "char_count": len(full_text),
        #     "instructor": presenter,
        #     "segments": segments           
        # }

    except Exception as e:
        print(f"  Error: {e}")
        return None


# ========== ADD YOUR VIDEO IDs HERE ==========
# VIDEO_IDS = [
#     "https://www.youtube.com/watch?v=HGOBQPFzWKo",  # Example: ThePrimeagen Vim tutorial
#     # Add more video IDs here...
# ]

VIDEO_IDS = get_all_video_urls_and_titles("@JackRuch")
#VIDEO_IDS = get_all_video_urls_and_titles_from_search("robben ford guitar lesson",  "robben ford",   50)
# ========== DOWNLOAD ==========
print(f"Downloading {len(VIDEO_IDS)} transcripts...\n")
results = []

for i, (vid, title, presenter) in enumerate(VIDEO_IDS, 1):    
    print( vid, title, presenter)
    vid_clean = clean_video_id(vid)
    
    if video_id_exists( vid_clean):
        print(f"video id {vid_clean} is already in the database, not downloading")
        continue


    print(f"[{i}/{len(VIDEO_IDS)}] {vid_clean}")
    
    file_dir = presenter.lower().replace(" ", "_").strip()
    file_path = Path(f"../transcripts/{file_dir}/{vid_clean}.json")
    print( file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.is_file():       
        result = download_transcript(vid, title, presenter, languages=["en"])
        
        if result:                        
            with open(file_path, "w", encoding="utf-8") as f:            
                f.write(result.model_dump_json(indent=2, ensure_ascii=False))                                     

        else:
            file_path.unlink(missing_ok=True) 

        time.sleep(60)
    else:
        print(f"file {file_path} already exists")
   

print(f"\nComplete: {len(results)}/{len(VIDEO_IDS)} transcripts downloaded")
