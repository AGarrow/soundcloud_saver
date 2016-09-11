## import required libraries 

import requests
import urllib2
import urllib
import json
import os, sys
from optparse import OptionParser
import eyed3
from secrets import CLIENT_ID

reload(sys)
sys.setdefaultencoding('utf8')

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
HOME_DIR = os.path.expanduser('~')
SOUNDCLOUD_DIR = os.path.join(os.path.join(HOME_DIR, "Music"), "SoundCloud")
USER_NAME = ""

# if the soundcloud directory doesn't exist, create it
if not os.path.exists(SOUNDCLOUD_DIR):
  os.mkdir(SOUNDCLOUD_DIR)

def download_track(track, track_dir):
  """
  This is the method that actually saves the track to the specified directory,
  the track parameter is a dictionary object, returned by the soundcloud api
  track_dir is the directory the track will be saved to.
  """
  track_title = track['title'].encode('utf-8').replace("/", "-")
  track_filepath = os.path.join(track_dir, "{}.mp3".format(track_title))

  ## if we already have the song, don't do anything
  if os.path.exists(track_filepath):
    return

  print "Downloading " + track_title

  ## put our client_id into url-friendly form
  params = urllib.urlencode({'client_id':CLIENT_ID})

  #create our song file
  f = open(track_filepath, 'w')

  ## if the track is downloadable, we just have to write the response
  ## to the file, urllib does all the work
  if track['downloadable']:
      response = urllib2.urlopen(track['download_url']+"?"+params)
      f.write(response.read())
      f.close()


  ## otherwise we need to actually write the stream as it comes in,
  else:
      try:
        response = urllib2.urlopen(track['stream_url']+"?"+params)
        buffer_data = "."
        while len(buffer_data) != 0:
          buffer_data = response.read(1024)
          f.write(buffer_data)
        f.close()
        tag = eyed3.load(track_filepath)
        tag.initTag()
        tag = tag.tag
        tag.artist = track['user']['username']
        tag.title = track['title']
        tag.save()
      except Exception, e:
        print track
     
  print 'done downloading'
  os.system("osascript {script_loc} \"{plist_name}\" \"{track_fp}\" \"{track_title}\"".format(
    script_loc="/Users/alexio/Desktop/side_projects/soundcloud/playlist_manager.scpt",
    plist_name=track_dir.split("/")[-1],
    track_fp=track_filepath,
    track_title=track['title']))


  ## always remember to close the file when you're done writing to it to prevent
  ## data corruption


## this tells python to look out for options we pass it from the command line.
## in this case by passing the -t argument, we can specify a specific track we want to 
## download instead of downloading an entire users library
parser = OptionParser()
parser.add_option("-t", "--track", dest="track_url", help="soundcloud track url")
(options, args) = parser.parse_args()

## if we specify a single track from the command line,
## then only download that track and save to SOUNDCLOUD_DIR. this is run as follows:
## python ./soundcloud_saver.py -t https://soundcloud.com/prettylights/pretty-lights-i-can-see-it-in
if options.track_url:
  r = requests.get(
    "https://api.soundcloud.com/resolve.json",
    params = {
    "client_id" : CLIENT_ID,
    "url" : options.track_url
    }
    )
  track_dict = json.loads(r.text)
  download_track(track_dict, SOUNDCLOUD_DIR)

## if we don't specify one track, the default is to get a users libary
else:

  ## this detects wether or not we have passed a url to a users account
  ## if not, the default is to download MY library (which you probably want because I have fantastic taste ;) 
  if len(sys.argv) > 1:
    user_url = sys.argv[1]
  else:
    user_url = "http://soundcloud.com/alexi-garrow"

  ### Get List of Tracks
  r = requests.get(
    "https://api.soundcloud.com/resolve.json",
    params={
      "url" : user_url,
      "client_id" : CLIENT_ID
    })

  ## load the response into a dict object
  response_json = json.loads(r.text)

  USER_NAME = response_json['username'].replace("/", "-")

  ## soundcloud will return the api version of the 
  ## users url, to which we can append /playlists
  ## to get a list of their playlists
  r = requests.get(
    response_json['uri'] + "/playlists",
    params={
      "client_id" : CLIENT_ID
    })

  ## load the response into a dict
  playlists_json = json.loads(r.text)

  ## get the users favorited tracks
  r = requests.get(
    response_json['uri'] + "/favorites",
    params = {
      "client_id" : CLIENT_ID
    })

  ## load the response into a dict
  favorites_json = json.loads(r.text)

  ## add likes as a playlist to our list of playlists
  playlists_json.append({
    "title" : "Likes",
    "tracks": favorites_json
  })

  ## make sure user directory exists within soundcloud, if not, create it
  soundcloud_user_dir = os.path.join(SOUNDCLOUD_DIR, USER_NAME)
  if not os.path.isdir(soundcloud_user_dir):
    os.mkdir(soundcloud_user_dir)

  for playlist in playlists_json:
    
    playlist_name = playlist['title'].encode('utf-8')
    playlist_directory = os.path.join(soundcloud_user_dir, playlist_name)
    if not os.path.isdir(playlist_directory):
      os.mkdir(playlist_directory)
      print "Downloading Playlist " + playlist_name
    else:
      print "Updating Playlist " + playlist_name
    print "========================="
    

    if playlist['title'] is not 'Likes':
      ## the likes list includes all of the songs, 
      ## but for playlists we need to get the list of songs
      ## from the playlist url
      p = requests.get(
        playlist['uri'],
        params = {
        "client_id" : CLIENT_ID
        })

      playlist_json = json.loads(p.text)
    else:
      playlist_json = playlist

    for track in playlist_json['tracks']:
      download_track(track, playlist_directory)
