import json
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_video_id_generator import get_all_video_urls_and_titles
from data_models import Transcript, Segment
import http.cookiejar
import requests


def clean_video_id(url_or_id):
    """Extract video ID from YouTube URL"""
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url_or_id)
        # print(match.group(1) if match else url_or_id)
        return match.group(1) if match else url_or_id

    return url_or_id


def download_transcript(video_id, title, presenter, languages=["en"]):
    """Download transcript using the correct API"""
    video_id = clean_video_id(video_id)

    try:
        # Create API instance
        session = requests.Session()

# Load cookies from exported cookies.txt
       
        # session.cookies = http.cookiejar.MozillaCookieJar("cookies.txt")
        # session.cookies.load()
        # api = YouTubeTranscriptApi(http_client=session)
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
        
     
        print (transcript)
        # Combine all text
        

       
       
        
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
# ========== DOWNLOAD ==========
print(f"Downloading {len(VIDEO_IDS)} transcripts...\n")
results = []

for i, (vid, title, presenter) in enumerate(VIDEO_IDS, 1):
    if i > 5:
        break
    print( vid, title, presenter)
    vid_clean = clean_video_id(vid)
    print(f"[{i}/{len(VIDEO_IDS)}] {vid_clean}")

    result = download_transcript(vid, title, presenter, languages=["en"])

    if result:
        # Save JSON
        file_dir = result.instructor.lower().replace(" ", "_").strip()
        
        with open(f"../transcripts/{file_dir}/{result.video_id}.json", "w", encoding="utf-8") as f:            
            f.write(result.model_dump_json(indent=2, ensure_ascii=False))
            #json.dump(result, f, indent=2, ensure_ascii=False)

        # Save TXT
        # with open(f"{result['video_id']}.txt", "w", encoding="utf-8") as f:
        #     f.write(f"Video: {result['url']}\n")
        #     f.write(f"Language: {result['language']}\n\n")
        #     f.write(result["text"])

        # print(f"  Success: {result['char_count']:,} characters")
        # print(f"  Saved: {result['video_id']}.json, {result['video_id']}.txt")
        # print(f"  Preview: {result['text'][:100]}...")
        # results.append(result)

    print()

print(f"\nComplete: {len(results)}/{len(VIDEO_IDS)} transcripts downloaded")
