from flask import Flask
from flask import request, redirect, abort, url_for, render_template

import requests
import json
from dateutil import parser
from datetime import datetime, timedelta
import operator

import ConfigParser



app = Flask(__name__)
app.debug = True



MOVES_CLIENT_ID="YOUR_CLIENT_ID"
MOVES_CLIENT_SECRET="YOUR_CLIENT_SECRET"
MOVES_REDIRECT_URI="YOUR_CALLBACK_URI"


class OAuth(requests.auth.AuthBase):
  def __init__(self, creds):
    self.creds = creds

  def __call__(self, r):
    r.headers['Authorization'] = "Bearer %s" % self.creds['access_token']
    return r

def get_oauth_authorize_url():
  return ("https://api.moves-app.com/oauth/v1/authorize?"
          "response_type=code&"
          "client_id=%s&"
          "scope=activity location" % MOVES_CLIENT_ID)
          
def get_exchange_url(code):
  return ("https://api.moves-app.com/oauth/v1/access_token"
          "?grant_type=authorization_code"
          "&code=%s"
          "&client_id=%s"
          "&client_secret=%s"
          "&redirect_uri=%s" % (code, MOVES_CLIENT_ID, MOVES_CLIENT_SECRET, MOVES_REDIRECT_URI))
          
def read_creds():
  with open("creds.json", "r") as text_file:
    x = json.load(text_file)
    values = None
    
    if "access_token" in x:
      values = {
        "access_token": x['access_token'],
        "refresh_token": x['refresh_token'],
        "user_id": x['user_id']
      }
    
    return values
    
def get_summary(creds):
  days = 30
  r = requests.get("https://api.moves-app.com/api/1.1/user/places/daily?pastDays=%s" % days, auth=OAuth(creds))
  return r.json()
  
def delta_to_hours(delta):
  return delta.days * 24 + delta.seconds / (60 * 60)

def summarize_time_at(days):
  time_by_place = {}
  
  for day in days:
    for visit in day['segments']:
      if "name" in visit["place"]:
        name = visit["place"]["name"]
        if name not in time_by_place:
          time_by_place[name] = timedelta(0)
        end_time = parser.parse(visit['endTime'])
        start_time = parser.parse(visit['startTime'])
        duration = end_time - start_time
        time_by_place[name] += duration
        
  return { name: delta_to_hours(delta) for name, delta in time_by_place.iteritems() }


@app.route("/")
def hello():
  creds = read_creds()
  if not creds:
      return '<a href="%s">Authorize!</a>' % get_oauth_authorize_url()

  days = get_summary(creds)
  values = summarize_time_at(days)

  sorted_values = sorted(values.iteritems(), key=operator.itemgetter(1), reverse = True)

  return render_template("index.html", places = sorted_values)
  
@app.route("/oauthcallback")
def callback():
  code = request.args.get('code', '')
  response = requests.post(get_exchange_url(code))

  with open("creds.json", "w") as text_file:
    text_file.write(response.text)
  
  read_creds()
  
  return redirect(url_for("hello"))

if __name__ == "__main__":
    config = ConfigParser.RawConfigParser()
    config.read('moves.ini')
    MOVES_CLIENT_ID = config.get("Moves API Creds", "client_id")
    MOVES_CLIENT_SECRET = config.get("Moves API Creds", "client_secret")
    MOVES_REDIRECT_URI = config.get("Moves API Creds", "redirect_uri")
    app.run()