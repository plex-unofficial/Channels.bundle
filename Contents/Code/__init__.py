from PMS import Plugin, Log, XML, HTTP, JSON, Prefs, RSS, Utils
from PMS.MediaXML import MediaContainer, DirectoryItem, VideoItem, SearchDirectoryItem
from PMS.FileTypes import PLS
import re
import urllib

CHANNELS_PLUGIN_PREFIX   = "/video/channels"
CHANNELS_URL             = "http://www.channels.com/"
CHANNELS_SEARCH_URL      = CHANNELS_URL + "search/rss?search_box="
CACHE_INTERVAL = 3600
USE_CACHE = True

# this is a patch for feedparser.py to handle the yahoo/media namespace.
def _start_media_thumbnail(self, attrsD):
    context = self._getContext()
    context.setdefault('media_thumbnail', [])
    context['media_thumbnail'].append(attrsD)
RSS.feedparser._FeedParserMixin._start_media_thumbnail = _start_media_thumbnail

####################################################################################################
def Start():
  Plugin.AddRequestHandler(CHANNELS_PLUGIN_PREFIX, HandleRequest, "CHANNELS", "icon-default.jpg", "art-default.jpg")
  Plugin.AddViewGroup("InfoList", viewMode="InfoList", contentType="items")
  Plugin.AddViewGroup("List", viewMode="List", contentType="items")
  Prefs.Expose("device_code", "Device Code (from Channels User Profile)")
  Prefs.Expose("user_id", "User ID (from Channels User Profile)")

####################################################################################################

def populateFromFeed(url, secondTitle=None, firstTitle=None):
  if not firstTitle:
    firstTitle = "Channels"

  dir = MediaContainer('channels-art-default.jpg', None, firstTitle, secondTitle)
  dir.SetViewGroup("InfoList")
  if USE_CACHE == True:
    feed = RSS.Parse(HTTP.GetCached(url, CACHE_INTERVAL))
  else:
    feed = RSS.Parse(url)

  added = 0
  for e in feed["items"]:
    try:
      id = e.enclosures[0]["href"]
      media_type = e.enclosures[0]["type"]
      if media_type == "application/x-shockwave-flash" or media_type.find("vmv") > -1 or media_type == "":
        continue

      try:
        description = XML.ElementFromString(e.description, True).text_content()
      except:
        description = ""

      try:
        thumbnail = e["media_thumbnail"][0]["url"]
      except:
        thumbnail = ""

      try:
        content_url = e["media_content"][0]["url"]
      except:
        content_url = ""

      duration = ""

      title = e.title
      if secondTitle and title.find(secondTitle) == 0:
        title = title[len(secondTitle)+1:]

      videoItem = VideoItem(id, title, description, duration+content_url, thumbnail)
  #   TODO: Set the metadata!
  #      videoItem.SetTelevisonMetadata(1,2,3)

      dir.AppendItem(videoItem)
      added = added + 1
      Log.Add("Read data for: "+title)
    except:
      Log.Add("Skipping item due to an error.")

  Log.Add("Total Videos: "+str(added))
  return dir.ToXML()

def askForLogin():
  
  return

def HandleRequest(pathNouns, count):
  user_id = Prefs.Get("user_id")
  device_code = Prefs.Get("device_code")

  Log.Add("Handling request for paths "+(",".join(pathNouns)) )

  if count == 0:
    dir = MediaContainer('channels-art-default.jpg', None, "Channels")
    dir.AppendItem(DirectoryItem("most_watched_week", "Most Watched This Week", ""))
    dir.AppendItem(DirectoryItem("most_watched_all", "Most Watched All Time", ""))
    dir.AppendItem(DirectoryItem("most_watched_month", "Most Watched This Month", ""))
    dir.AppendItem(DirectoryItem("newest_videos_week", "Newest Videos This Week", ""))
    dir.AppendItem(DirectoryItem("newest_videos_today", "Newest Videos Today", ""))
    dir.AppendItem(SearchDirectoryItem("search", "Search", "Search Channels.com", Plugin.ExposedResourcePath("search.png")))
    dir.AppendItem(DirectoryItem("my_feed", "My Feed", ""))

    if user_id != None:
      dir.AppendItem(SearchDirectoryItem("pref^user_id", "Change Channels User Id [" + user_id + "]", "Change your Channels User ID.", ""))
    else:
      dir.AppendItem(SearchDirectoryItem("pref^user_id", "Set your User ID", "Go to Edit Profile - Tools and see your user ID.", ""))

    if device_code != None:
      dir.AppendItem(SearchDirectoryItem("pref^device_code", "Change Channels Device Code [" + device_code + "]", "Change your Channels Device Code.", ""))
    else:
      dir.AppendItem(SearchDirectoryItem("pref^device_code", "Set your Device Code", "Go to Edit Profile - Tools and see your Device Code.", ""))

    return dir.ToXML()

  elif pathNouns[0] == "most_watched_week":
    url = CHANNELS_URL + "popular/videos/week?format=rss"
    Log.Add("Loading "+url )
    return populateFromFeed(url, "Most Watched This Week")
  elif pathNouns[0] == "most_watched_month":
    url = CHANNELS_URL + "popular/videos/month?format=rss"
    Log.Add("Loading "+url )
    return populateFromFeed(url, "Most Watched This Month")
  elif pathNouns[0] == "most_watched_all":
    url = CHANNELS_URL + "popular/videos/all?format=rss"
    Log.Add("Loading "+url )
    return populateFromFeed(url, "Most Watched All Time")
  elif pathNouns[0] == "newest_videos_today":
    url = CHANNELS_URL + "newest/videos/today?format=rss"
    Log.Add("Loading "+url )
    return populateFromFeed(url, "Newest Videos Today")
  elif pathNouns[0] == "newest_videos_week":
    url = CHANNELS_URL + "newest/videos/week?format=rss"
    Log.Add("Loading "+url )
    return populateFromFeed(url, "Newest Videos This Week")
  elif pathNouns[0] == "my_feed":
    Log.Add("Handling my feed only if user_id and device_code are there.")
    if user_id != None and device_code != None:
      url = CHANNELS_URL + "device_feed?format=rss&user_id="+user_id+"&device_code="+device_code
      Log.Add("Loading "+url )
      return populateFromFeed(url, "My Feed")
  elif pathNouns[0].startswith("pref"):
    if count == 2:
      field = pathNouns[0].split("^")[1]
      Prefs.Set(field,pathNouns[1])
      if field == "user_id":
        dir.SetMessage("Channels Preferences", "Channels User ID Set.")
      else:
        dir.SetMessage("Channels Preferences", "Channels Device Code Set")

  elif pathNouns[0] == "search":
    if count > 1:
      query = pathNouns[1]
      if count > 2:
        for i in range(2, len(pathNouns)): query += "/%s" % pathNouns[i]
      return populateFromFeed(CHANNELS_SEARCH_URL + urllib.quote_plus(query), "Query: "+query)