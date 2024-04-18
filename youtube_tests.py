import os
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

API_KEY = os.getenv('API_KEY')

youtube = build('youtube', 'v3', developerKey=API_KEY)


# request = youtube.channels().list(
#     part="statistics",
#     id="UCX6OQ3DkcsbYNE6H8uQQuVA"
# )

# response = request.execute()

# pl_request = youtube.search().list(
#     part="snippet",
#     q="mrbeast",
#     maxResults=10000
# )
#
# pl_response = pl_request.execute()

dl_request = youtube.videos().list(
    part="snippet,contentDetails,statistics",
    id="erLbbextvlY"
)

dl_response = dl_request.execute()
# print(json.dumps(dl_response, sort_keys=True, indent=4))
#
# for item in pl_response['items']:
#     if item["id"]["kind"] == "youtube#video":
#         print(json.dumps(item, sort_keys=True, indent=4))