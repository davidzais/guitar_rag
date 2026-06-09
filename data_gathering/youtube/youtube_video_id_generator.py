import requests

API_KEY = "YOUR_API_KEY"
HANDLE_ID = "@JackRuch"  # e.g. UC_x5XG1OV2P6uZZ5FSM9Ttw

def get_all_video_urls_and_titles(handle_id: str, api_key: str = None):
    video_data: list[tuple] = []
    next_page_token = None

    # Step 1: Get the "uploads" playlist ID for the channel
    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    channel_params = {
        "part": "contentDetails,snippet",
        "forHandle": handle_id,
        "key": "AIzaSyBN9P7q582lbsUIHV-jJop_GjYqV_ilXK4",
    }
    res = requests.get(channel_url, params=channel_params).json()

    
    uploads_playlist_id = res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    presenter = res["items"][0]["snippet"]["title"]
    

    # Step 2: Page through the playlist to collect all video IDs
    playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
    while True:
        playlist_params = {
            "part": "contentDetails,snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": 50,  # max allowed per page
            "key": "AIzaSyBN9P7q582lbsUIHV-jJop_GjYqV_ilXK4",
        }
        if next_page_token:
            playlist_params["pageToken"] = next_page_token

        res = requests.get(playlist_url, params=playlist_params).json()     
        
        
        for item in res["items"]:                         
            video_data.append((item["contentDetails"]["videoId"],item["snippet"]["title"],presenter))
           

        next_page_token = res.get("nextPageToken")
        if not next_page_token:
            break  # no more pagesclear

    return video_data


video_data = get_all_video_urls_and_titles(HANDLE_ID, API_KEY)
if __name__ == "__main__" :
    print(f"Found {len(video_data)} videos")
    for vid, title, owner in video_data:
        print(f"https://www.youtube.com/watch?v={vid}   {title} {owner}")
