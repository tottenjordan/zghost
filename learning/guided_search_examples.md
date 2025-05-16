# Guided Search with Google and YouTube

This document shows different ways to use the underlying Google Search libraries and YouTube APIs. To simplifiy initial onboarding, we've made some of these parameters configurable only to the user :angel:  / developer :neckbeard: , as opposed to giving the LLM-based agents... *total control* :smiling_imp:

For example, consider the below function we could use as a tool for getting trending videos from YouTube:

```python
def get_youtube_trends(region_code: str, max_results: int = 5,) -> dict:
    """
    Makes request to YouTube Data API for most popular videos in a given region.
    Returns a dictionary of videos that match the API request parameters e.g., trending videos

    Args:
        region_code (str): selects a video chart available in the specified region. Values are ISO 3166-1 alpha-2 country codes.
            For example, the region_code for the United Kingdom would be 'GB', whereas 'US' would represent The United States.
        max_results (int): The number of video results to return.

    Returns:
        dict: The response from the YouTube Data API.
    """

    request = youtube_client.videos().list(
        part="snippet,contentDetails,statistics",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results,
    )
    trend_response = request.execute()
    return trend_response
```

**We're giving the LLM-based agent the ability to change the `region_code` and `max_results`. Why?**
* This allows the agent to easily make seperate API calls, each for a different region. 
* It could also change the number of results based off some user interaction e.g., :information_desk_person: "actually can I see the top 50 trending videos?"
   
   > Having a clear and informative doc strings goes a long way here! 

**We've hard-coded the `chart` and `part` parameters. Why?**
* We don't need the agent to do all the things the API can do. It just needs to focus on the *trending videos* --> `"mostPopular"`
* We want it to always return the `"snippet,contentDetails,statistics"`

  > We're mitigating some risk of it deviating too far from our expectations... mainly because we're more interested in how it deviates from other expectations :wink: 



## Google Search

`googlesearch-python` is a Python library for searching Google

**References**

* [pypi project](https://pypi.org/project/googlesearch-python/)
* see [GitHub repo](https://github.com/Nv7-GitHub/googlesearch) for more examples
* see [supported country codes](https://developers.google.com/custom-search/docs/json_api_reference#countryCodes) for input arg: `region`

**Example usage**

1. **Simple Search:** search Google for URLs *related to given `query` string*

```python
from googlesearch import search

target_topic = "widespread panic"
query = target_topic

results_generator = search(
    term=query,
    lang="en",
    region="us",
    num_results=10,
    sleep_interval=2.0,
    unique=True,
    advanced=False,
)

# convert result object to list
search_results_urls = list(results_generator)
search_results_urls
```

*returns list of related URLs:*

```python
['https://widespreadpanic.com/',
 'https://en.wikipedia.org/wiki/Widespread_Panic',
 'http://www.widespreadpanic.com/',
 'https://www.youtube.com/channel/UCKmXntvZFs9VBYknXMMzIbw',
 'https://open.spotify.com/artist/54SHZF2YS3W87xuJKSvOVf',]
 ```


2. **Search Operators:** Combine `query` string with [search operators](https://developers.google.com/search/docs/monitor-debug/search-operators/all-search-site) (e.g., `site:`) to *request results from a particular domain, URL, or URL prefix:*

```python
from googlesearch import search

# Search Reddit for content related to "widespread panic"
target_topic = "widespread panic"
query = "site:reddit.com" + " " + target_topic

results_generator = search(
    term=query,
    lang="en",
    region="us",
    num_results=10,
    sleep_interval=2.0,
    unique=True,
    advanced=False,
)
search_results_urls = list(results_generator)
search_results_urls
```

*returns list of related URLs from `reddit.com` only:*

```python
['https://www.reddit.com/r/WidespreadPanic/',
 'https://www.reddit.com/r/jambands/comments/12oyub2/why_the_hate_on_widespread_panic/',
 'https://www.reddit.com/r/jambands/comments/1c55dhz/widespread_panic_complete_concert_videos/',
 'https://www.reddit.com/r/WidespreadPanic/comments/165nt0l/dark_and_menacing_widespread_panic/',
 'https://www.reddit.com/r/gratefuldead/comments/1htfa31/widespread_panic/',]
```


3. **Advanced Search:** set `advanced=True` to *return list of `SearchResult` objects (title, url, description):*

```python
results_generator = search(
    term=query,
    lang="en",
    region="us",
    num_results=10,
    sleep_interval=2.0,
    unique=True,
    advanced=True,
)
search_results = list(results_generator)
search_results[0]
```
*returns `SearchResult` object:*

```python
SearchResult(
  url="https://www.reddit.com/r/jambands/comments/1e6hjl9/widespread_panic_appreciation_thread/", 
  title="Widespread Panic Appreciation Thread : r/jambands - Reddit",
  description="Jul 18,2024·In a jam band world of the goofy, wookie, entitled and sometimes creepy-ass fans, panic's fans remain undefeated..."
)
```


## Google News

`GoogleNews` is a Python library for searching [Google News](https://news.google.com/)

**References**
* [pypi project](https://pypi.org/project/GoogleNews/)

**Example usage**

1. *Can only search `query` terms; **cannot combine** with search operators (e.g., `site: `)*

```python
from GoogleNews import GoogleNews

# initialize 
googlenews = GoogleNews(
    lang='en',
    region='US',
    # period='7d',
    # start='02/01/2020',
    # end='02/28/2020',
    # encode='utf-8',
)

# check version
print(googlenews.getVersion())

# enable throw exception
googlenews.enableException(True)

# topic/query
query = "widespread panic"

# sets topic/query to search `news.google.com`
news_wsp = googlenews.get_news(query)
```

**get news article results dict**

```python
news_wsp_results = googlenews.results()
news_wsp_results = [
    {
        'title': 'Widespread Panic Delivers a One, Two, Three Knock-Out Punch to Smashville',
        'desc': None,
        'date': '3 days ago',
        'datetime': datetime.datetime(2025, 5, 11, 11, 51, 18, 655146),
        'media': None,
        'site': None,
        'reporter': None,
        'link': 'https://news.google.com/read/CBMirwFBVV95cUxQbmo2NlpoMzVQZEtvUkUyQVk2Vi13X2FIMGlmc3l4bHJRN1VXQjQ3NzZnUWUxZ2xJMnBRMVlBeFBOWUx5dTBkWFBRZmV1ZkRLNmQ0RThCYmQyNURaWXc1ZWYxRTBnT2FBejZ3bFdxbDBHeTAwZ3YzcUF1QnA3Y0tubnBMaVhRVnhUZGt5d3F1ME4ydkJaOHByM2ZJUXRTTklSRktiNkJkWC1kT0N6bXZB?hl=en-US&gl=US&ceid=US%3Aen',
        'img': 'https://news.google.com/api/attachments/CC8iK0NnNXJZVk5RV0U1VlNuQnpOWE5RVFJERUF4aW1CU2dLTWdZQkFJYUVqZ2s=-w200-h112-p-df',
    },
    ...
]
```

**get news article URLs only**

```python
news_wsp_links = googlenews.get_links()
news_wsp_links[0] = 'https://news.google.com/read/CBMirwFBVV95cUxQbmo2NlpoMzVQZEtvUkUyQVk2Vi13X2FIMGlmc3l4bHJRN1VXQjQ3NzZnUWUxZ2xJMnBRMVlBeFBOWUx5dTBkWFBRZmV1ZkRLNmQ0RThCYmQyNURaWXc1ZWYxRTBnT2FBejZ3bFdxbDBHeTAwZ3YzcUF1QnA3Y0tubnBMaVhRVnhUZGt5d3F1ME4ydkJaOHByM2ZJUXRTTklSRktiNkJkWC1kT0N6bXZB?hl=en-US&gl=US&ceid=US%3Aen'
```

**get news article titles only**

```python
news_wsp_titles = googlenews.get_texts()
news_wsp_titles = [
    'Widespread Panic Delivers a One, Two, Three Knock-Out Punch to Smashville',
    'Widespread Panic Announce September Shows at New Richmond, Va. Venue',
    'Widespread Panic books two Richmond shows at Allianz',
    'Widespread Panic brings 40 years of jams',
]
```

**clear result list before doing another search with same `googlenews` object**

```python
googlenews.clear()
```

2. *Get news by topics:*

```python
SPORTS_TOPIC_ID = "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pWVXlnQVAB"
googlenews.set_topic(SPORTS_TOPIC_ID)
googlenews.get_news()
googlenews.results()
```

**topic IDs**

* **HEALTH** = "CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ"
* **SPORTS** = "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pWVXlnQVAB"
* **SCIENCE** = "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pWVXlnQVAB"
* **US NEWS** = "CAAqIggKIhxDQkFTRHdvSkwyMHZNRGxqTjNjd0VnSmxiaWdBUAE"
* **BUSINESS** = "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB"
* **WORLD NEWS** = "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB"
* **TECHNOLOGY** = "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB"
* **ENTERTAINMENT** = "CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtVnVHZ0pWVXlnQVAB"

> topic URLs: `https://news.google.com/topics/{TOPIC_ID}?hl=en-US&gl=US&ceid=US%3Aen`


## YouTube Data API v3

<details>
  <summary>Create and store API key</summary>

1. See [these instructions](https://developers.google.com/youtube/v3/getting-started) for getting a `YOUTUBE_DATA_API_KEY`

2. Store this API key in [Secret Manager](https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets) as `yt-data-api`. See [create a secret and access a secret version](https://cloud.google.com/secret-manager/docs/create-secret-quickstart#create_a_secret_and_access_a_secret_version) or step-by-step guidance

</details>

---

**Example usage**

1. *REST API:* 
   * `GET https://www.googleapis.com/youtube/v3/videos?part=id&chart=mostPopular&regionCode=FR&key={YOUTUBE_DATA_API_KEY}`

2. *Python client:*

```python
import googleapiclient.discovery

# config discovery client
youtube_client = googleapiclient.discovery.build(
    serviceName="youtube", 
    version="v3", 
    developerKey=YOUTUBE_DATA_API_KEY
)
```

**Videos: list** - Returns a list of videos that match the API request parameters

```python
# return most popular (i.e., trending) in US
request = youtube_client.videos().list(
    part="snippet,contentDetails,statistics",
    chart="mostPopular",
    regionCode="US"
)
response = request.execute()
```

The response has 3 `parts`: "snippet", "contentDetails", & "statistics"

1. the `snippet` object contains basic details about the video, such as its title, description, and category:

```python
response['items'][0]['snippet']

{
    'publishedAt': '2025-05-13T21:15:00Z',
    'channelId': 'UCdtXPiqI2cLorKaPrfpKc4g',
    'title': "Diddy Trial: Cassie's Testimony Breakdown With CBS News' Jericka Duncan",
    'description': "CBS News' Jericka Duncan breaks down Cassie Ventura's testimony against her ex, Sean 'Diddy' Combs, in his sex trafficking and racketeering trial on Tuesday, May 13. Diddy maintains his innocence against all charges, currently being explored in a New York City court. Jericka recounts Cassie's explanation of 'freak offs,' the supposed sex-fueled parties thrown by Diddy, and abuse she allegedly experienced while dating Diddy. Jericka also speculates on other famous faces who may take the stand in the coming days.",
    'thumbnails': {
        'default': {
            'url': 'https://i.ytimg.com/vi/ArIqryxHquo/default.jpg',
            'width': 120,
            'height': 90
        },
        'medium': {
            'url': 'https://i.ytimg.com/vi/ArIqryxHquo/mqdefault.jpg',
            'width': 320,
            'height': 180
        },
        'high': {
            'url': 'https://i.ytimg.com/vi/ArIqryxHquo/hqdefault.jpg',
            'width': 480,
            'height': 360
        },
        'standard': {
            'url': 'https://i.ytimg.com/vi/ArIqryxHquo/sddefault.jpg',
            'width': 640,
            'height': 480
        },
        'maxres': {
            'url': 'https://i.ytimg.com/vi/ArIqryxHquo/maxresdefault.jpg',
            'width': 1280,
            'height': 720
        }
    },
    'channelTitle': 'Entertainment Tonight',
    'tags': ['Cassie Ventura', 'Diddy', 'Sean Combs'],
    'categoryId': '24',
    'liveBroadcastContent': 'none',
    'defaultLanguage': 'en',
    'localized': {
        'title': "Diddy Trial: Cassie's Testimony Breakdown With CBS News' Jericka Duncan",
        'description': "CBS News' Jericka Duncan breaks down Cassie Ventura's testimony against her ex,Sean 'Diddy' Combs, in his sex trafficking and racketeering trial on Tuesday, May 13. Diddy maintains his innocence against all charges, currently being explored in a New York City court. Jericka recounts Cassie's explanation of 'freak offs,' the supposed sex-fueled parties thrown by Diddy, and abuse she allegedly experienced while dating Diddy. Jericka also speculates on other famous faces who may take the stand in the coming days."
    },
    'defaultAudioLanguage': 'en'
}
```

2. The `contentDetails` object contains information about the video content, including the length of the video and an indication of whether captions are available for the video:

```python
response['items'][0]['contentDetails']

{'duration': 'PT8M50S',
 'dimension': '2d',
 'definition': 'hd',
 'caption': 'false',
 'licensedContent': True,
 'contentRating': {},
 'projection': 'rectangular'}
```

3. The `statistics` object contains statistics about the video:

```python
response['items'][0]['statistics']

{'viewCount': '533962',
 'likeCount': '7469',
 'favoriteCount': '0',
 'commentCount': '1811'}
```

**Search: list** - Returns a collection of search results that match the query parameters specified in the API request

```python
import pandas as pd

TARGET_QUERY = "time travel"
MAX_DAYS_AGO = 60

# get correct format
PUBLISHED_AFTER_TIMESTAMP = (
    (pd.Timestamp.now() - pd.DateOffset(days=MAX_DAYS_AGO))
    .tz_localize("UTC")
    .isoformat()
)

# search YouTube for reated videos
yt_data_api_request = youtube_client.search().list(
    part="id,snippet",
    type="video",
    regionCode="US",
    q=TARGET_QUERY,
    videoDuration="medium", # "any" | "short" | "medium" | "long"
    maxResults=3,
    publishedAfter=PUBLISHED_AFTER_TIMESTAMP,
    channelId="any",
    order="relevance",
)
yt_data_api_response = yt_data_api_request.execute()
yt_data_api_response = {
    'kind': 'youtube#searchListResponse',
    'etag': 'dZfJzsSeeHDXXQRL2boFP0h06BA',
    'nextPageToken': 'CAEQAA',
    'regionCode': 'US',
    'pageInfo': {'totalResults': 3, 'resultsPerPage': 1},
    'items': [
        {
            'kind': 'youtube#searchResult',
            'etag': 'JE7wL5DcJeZHj10m3RMyLB956n4',
            'id': {'kind': 'youtube#video', 'videoId': 'uHTrBuekQzg'},
            'snippet': {
                'publishedAt': '2025-05-13T20:00:38Z',
                'channelId': 'UC9MAhZQQd9egwWCxrwSIsJQ',
                'title': 'History&#39;s Greatest Mysteries: Did the U.S. Government Steal the Tesla Files? (Season 6)',
                'description': "Dive into one of the most intriguing mysteries of modern history with this captivating clip from History's Greatest Mysteries!",
                'thumbnails': {
                    'default': {
                        'url': 'https://i.ytimg.com/vi/uHTrBuekQzg/default.jpg',
                        'width': 120,
                        'height': 90
                    },
                    'medium': {
                        'url': 'https://i.ytimg.com/vi/uHTrBuekQzg/mqdefault.jpg',
                        'width': 320,
                        'height': 180
                    },
                    'high': {
                        'url': 'https://i.ytimg.com/vi/uHTrBuekQzg/hqdefault.jpg',
                        'width': 480,
                        'height': 360
                    }
                },
                'channelTitle': 'HISTORY',
                'liveBroadcastContent': 'none',
                'publishTime': '2025-05-13T20:00:38Z'
            }
        }
    ]
}
```