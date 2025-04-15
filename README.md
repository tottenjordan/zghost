# Overview

This Marketing Idea Generator Agent:
- Generates marketing ideas based on a product description.
- Uses a large language model to generate creative and relevant ideas.
- Can be used to brainstorm new marketing campaigns, content ideas, and more.

# Running locally

```bash
adk web .
```


# Deploying

```bash
adk deploy cloud_run --help

# last of the zghost

## using this repository

Change variables in `.env` file

```
source .env
```

<details>
<summary> <strong>Accessing YouTube API</strong></summary>

1. REST API: `GET https://www.googleapis.com/youtube/v3/videos?part=id&chart=mostPopular&regionCode=FR&key={YOUR_API_KEY}`

2. HTTP requests with `Python`

*config discovery client..*

```python
    youtube = googleapiclient.discovery.build(
        serviceName=API_SERVICE_NAME, 
        version=API_VERSION, 
        developerKey=YOUTUBE_DATA_API_KEY
    )
```


**Videos: list** - `Returns a list of videos that match the API request parameters`

```python
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        chart="mostPopular",
        regionCode="US"
    )
    response = request.execute()
```

**Search: list** -`Returns a collection of search results that match the query parameters specified in the API request`

```python
    yt_data_api_request = youtube.search().list(
        part="id,snippet",
        type="video",
        q=TARGET_QUERY,
        videoDuration=VIDEO_DURATION,
        maxResults=NUM_RESULTS,
        publishedAfter=PUBLISHED_AFTER_TIMESTAMP,
        channelId=CHANNEL_ID,
        order=ORDER_CRITERIA,
    )
    yt_data_api_response = yt_data_api_request.execute()
```
 
</details>