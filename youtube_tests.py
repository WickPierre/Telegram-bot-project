import os
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from pytube import YouTube


load_dotenv()

API_KEY = os.getenv('API_KEY')

youtube = build('youtube', 'v3', developerKey=API_KEY)

# request = youtube.channels().list(
#     part="statistics",
#     id="UCX6OQ3DkcsbYNE6H8uQQuVA"
# )

# response = request.execute()

# pl_request = youtube.search().list(
#     part="id",
#     q="mrbeast",
#     maxResults=10
# )
#
# pl_response = pl_request.execute()
# print(json.dumps(pl_response, sort_keys=True, indent=4))
# dl_request = youtube.videos().list(
#     part="snippet,contentDetails,statistics",
#     id="erLbbextvlY"
# )
#
# dl_response = dl_request.execute()

pl_request = youtube.search().list(
    part="id",
    q="Синий трактор",
    maxResults=5
)
pl_response = pl_request.execute()
video_id = None
for item in pl_response["items"]:
    if item["id"]["kind"] == "youtube#video":
        video_id = item["id"]["videoId"]
        break
if video_id:
    request = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=video_id
    )
    response = request.execute()
    print(json.dumps(response, sort_keys=True, indent=4))

    title = response["items"][0]["snippet"]["title"]
    description = response["items"][0]["snippet"]["description"]
    duration = response["items"][0]["contentDetails"]["duration"]
    commentCount = response["items"][0]["statistics"].get("commentCount")
    if not commentCount:
        commentCount = 0
    likeCount = response["items"][0]["statistics"]["likeCount"]
    viewCount = response["items"][0]["statistics"]["viewCount"]
    publication_date = response["items"][0]["snippet"]["publishedAt"]
    print(commentCount)
    #
    # print(duration)
    # duration = duration[::-1]
    # s = {}
    # e = None
    # for i in range(len(duration)):
    #     if duration[i] in "1234567890":
    #         s[e] += duration[i]
    #     elif e:
    #         s[e] = s[e][::-1]
    #         s[duration[i]] = ""
    #         e = duration[i]
    #     else:
    #         s[duration[i]] = ""
    #         e = duration[i]
    # print(s)